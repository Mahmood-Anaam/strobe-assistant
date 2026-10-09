import { createServer, type IncomingMessage, type ServerResponse } from "node:http";
import { existsSync, readFileSync, statSync } from "node:fs";
import { extname, join, normalize } from "node:path";
import { WebSocketServer } from "ws";
import * as acp from "@agentclientprotocol/sdk";
import { createNodeHttpHandler, createNodeWebSocketUpgradeHandler } from "@agentclientprotocol/sdk/experimental/node";
import { AcpServer } from "@agentclientprotocol/sdk/experimental/server";
import { BedrockRuntimeClient, ConverseCommand, type ContentBlock } from "@aws-sdk/client-bedrock-runtime";
import { GetSecretValueCommand, SecretsManagerClient } from "@aws-sdk/client-secrets-manager";

const PORT = Number(process.env.PORT ?? 8080);
const HOST = process.env.HOST ?? "0.0.0.0";
const REGION = process.env.AWS_REGION ?? "ap-southeast-2";
const MODEL_ID = process.env.CHAT_MODEL_ID ?? "apac.amazon.nova-lite-v1:0";
const MCP_URL = (process.env.MCP_URL ?? "http://127.0.0.1:8081").replace(/\/$/, "");
const DEMO_USER_ID = process.env.DEMO_USER_ID ?? "";
const WEB_ROOT = normalize(process.env.WEB_ROOT ?? join(process.cwd(), "dist"));

interface SearchResult {
  vector_key: string;
  distance: number;
  post_id: string;
  object_key: string;
  description: string;
  labels: string[];
  image_url?: string;
}

interface SessionState { pending: AbortController | null; }

class McpGateway {
  private apiKey = process.env.MCP_API_KEY ?? "";

  async initialize(): Promise<void> {
    const arn = process.env.MCP_API_KEY_SECRET_ARN;
    if (!arn || this.apiKey) return;
    const client = new SecretsManagerClient({ region: REGION });
    const response = await client.send(new GetSecretValueCommand({ SecretId: arn }));
    const payload = JSON.parse(response.SecretString ?? "{}");
    this.apiKey = String(payload.apiKey ?? "");
  }

  async search(query: string, userId: string, signal: AbortSignal): Promise<SearchResult[]> {
    const response = await fetch(`${MCP_URL}/api/tools/search`, {
      method: "POST",
      headers: { "content-type": "application/json", "x-api-key": this.apiKey },
      body: JSON.stringify({ query, user_id: userId, top_k: 8 }),
      signal,
    });
    if (!response.ok) throw new Error(`MCP search failed (${response.status})`);
    const body = await response.json() as { results: SearchResult[] };
    return body.results;
  }
}

class StrobeAssistantAgent {
  private readonly sessions = new Map<string, SessionState>();
  private readonly bedrock = new BedrockRuntimeClient({ region: REGION, maxAttempts: 5 });

  constructor(private readonly mcp: McpGateway) {}

  initialize(): acp.InitializeResponse {
    return { protocolVersion: acp.PROTOCOL_VERSION, agentCapabilities: { loadSession: false } };
  }

  newSession(): acp.NewSessionResponse {
    const sessionId = crypto.randomUUID();
    this.sessions.set(sessionId, { pending: null });
    return { sessionId };
  }

  cancel(params: acp.CancelNotification): void {
    this.sessions.get(params.sessionId)?.pending?.abort();
  }

  async prompt(params: acp.PromptRequest, context: acp.AgentContext): Promise<acp.PromptResponse> {
    const session = this.sessions.get(params.sessionId);
    if (!session) throw new Error(`Unknown session: ${params.sessionId}`);
    session.pending?.abort();
    const controller = new AbortController();
    session.pending = controller;
    try {
      const text = params.prompt.flatMap((part) => part.type === "text" ? [part.text] : []).join("\n").trim();
      if (!DEMO_USER_ID) throw new Error("DEMO_USER_ID is not configured for this deployment.");
      await this.status(params.sessionId, "Searching your Strobe library", context);
      const results = await this.mcp.search(text || "attached photo", DEMO_USER_ID, controller.signal);
      await this.status(params.sessionId, `Retrieved ${results.length} grounded photo records`, context);
      const answer = await this.groundedAnswer(text, params.prompt, results);
      await this.sendText(params.sessionId, answer, context);
      for (const result of results.slice(0, 4)) {
        if (result.image_url) await this.sendText(params.sessionId, `\n\n![${result.description}](${result.image_url})`, context);
      }
      return { stopReason: "end_turn" };
    } catch (error) {
      if (controller.signal.aborted) return { stopReason: "cancelled" };
      await this.sendText(params.sessionId, `I could not complete this turn: ${this.errorMessage(error)}`, context);
      return { stopReason: "end_turn" };
    } finally {
      if (session.pending === controller) session.pending = null;
    }
  }

  private async groundedAnswer(text: string, prompt: readonly acp.ContentBlock[], results: SearchResult[]): Promise<string> {
    const context = JSON.stringify(results.map(({ image_url: _url, ...item }) => item));
    const content: ContentBlock[] = [{ text: `${text}\n\nRetrieved Strobe records:\n${context}` }];
    const image = prompt.find((part) => part.type === "image");
    if (image?.type === "image") {
      const format = image.mimeType.split("/")[1]?.replace("jpg", "jpeg") as "png" | "jpeg" | "gif" | "webp";
      content.unshift({ image: { format, source: { bytes: Uint8Array.from(Buffer.from(image.data, "base64")) } } });
    }
    try {
      const response = await this.bedrock.send(new ConverseCommand({
        modelId: MODEL_ID,
        system: [{ text: "You are Strobe Assistant. Answer only from retrieved records. State when evidence is insufficient. Be concise." }],
        messages: [{ role: "user", content }],
        inferenceConfig: { maxTokens: 512, temperature: 0.3 },
      }));
      return response.output?.message?.content?.map((block) => block.text ?? "").join("").trim() || "No answer was generated.";
    } catch (error) {
      const lines = results.map((item, index) => `${index + 1}. ${item.description} (${item.labels.join(", ")})`);
      const fallback = lines.length ? `I found these semantically matched photos:\n\n${lines.join("\n")}` : "I found no matching classified photos.";
      return `${fallback}\n\n_Model narration is temporarily unavailable: ${this.errorMessage(error)}_`;
    }
  }

  private async sendText(sessionId: string, text: string, context: acp.AgentContext): Promise<void> {
    for (let offset = 0; offset < text.length; offset += 120) {
      await context.notify(acp.methods.client.session.update, {
        sessionId,
        update: { sessionUpdate: "agent_message_chunk", content: { type: "text", text: text.slice(offset, offset + 120) } },
      });
    }
  }

  private async status(sessionId: string, title: string, context: acp.AgentContext): Promise<void> {
    await context.notify(acp.methods.client.session.update, {
      sessionId,
      update: { sessionUpdate: "agent_thought_chunk", content: { type: "text", text: title } },
    });
  }

  private errorMessage(error: unknown): string {
    const message = error instanceof Error ? error.message : String(error);
    if (message.includes("service control policy") || message.includes("AccessDenied")) {
      return "Bedrock generative access is blocked by the CAB432 organisation policy.";
    }
    return message;
  }
}

function pathname(request: IncomingMessage): string {
  return new URL(request.url ?? "/", `http://${request.headers.host ?? "localhost"}`).pathname;
}

function send(response: ServerResponse, status: number, body: Buffer, contentType: string): void {
  response.writeHead(status, { "content-type": contentType, "content-length": body.byteLength, "cache-control": "no-store" });
  response.end(body);
}

function serveWeb(path: string, response: ServerResponse): void {
  const requested = path === "/" ? "index.html" : path.replace(/^\//, "");
  let file = normalize(join(WEB_ROOT, requested));
  if (!file.startsWith(WEB_ROOT) || !existsSync(file) || statSync(file).isDirectory()) file = join(WEB_ROOT, "index.html");
  const types: Record<string, string> = { ".html": "text/html; charset=utf-8", ".js": "text/javascript", ".css": "text/css", ".svg": "image/svg+xml" };
  send(response, 200, readFileSync(file), types[extname(file)] ?? "application/octet-stream");
}

export async function startServer(): Promise<ReturnType<typeof createServer>> {
  const mcp = new McpGateway();
  await mcp.initialize();
  const implementation = new StrobeAssistantAgent(mcp);
  const agent = acp.agent({ name: "strobe-assistant" })
    .onRequest(acp.methods.agent.initialize, () => implementation.initialize())
    .onRequest(acp.methods.agent.session.new, () => implementation.newSession())
    .onRequest(acp.methods.agent.session.prompt, (context) => implementation.prompt(context.params, context.client))
    .onNotification(acp.methods.agent.session.cancel, (context) => implementation.cancel(context.params));
  const acpServer = new AcpServer({ agent });
  const httpHandler = createNodeHttpHandler(acpServer);
  const webSockets = new WebSocketServer({ noServer: true });
  const upgradeHandler = createNodeWebSocketUpgradeHandler(acpServer, webSockets);
  const server = createServer((request, response) => {
    const path = pathname(request);
    if (path === "/healthz") send(response, 200, Buffer.from("ok\n"), "text/plain");
    else if (path === "/acp") httpHandler(request, response);
    else serveWeb(path, response);
  });
  server.on("upgrade", (request, socket, head) => pathname(request) === "/acp" ? upgradeHandler(request, socket, head) : socket.destroy());
  server.listen(PORT, HOST);
  return server;
}

void startServer().then(() => console.log(`Strobe Assistant listening on http://${HOST}:${PORT}`));

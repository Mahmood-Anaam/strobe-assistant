# Testing and verification

## Automated quality gates

```powershell
.\.venv\Scripts\ruff.exe check .
.\.venv\Scripts\ruff.exe format --check .
.\.venv\Scripts\pytest.exe --cov=strobe_assistant --cov-report=term-missing
npm test
npm run build
npm run build:server
```

Python tests use fakes/mocks at AWS boundaries and cover the Titan embedding request, image classification orchestration and Rekognition fallback, persistence handoff, and S3 Vectors user filtering/result mapping. TypeScript tests cover ACP request handling, streaming, native image input/output, Markdown fallback, cancellation, and path safety. The production build also runs `tsc --noEmit`.

## Container smoke tests

```powershell
docker build -f Dockerfile.mcp -t strobe-assistant-mcp:test .
docker run --rm -d --name strobe-mcp-test -p 18081:8081 strobe-assistant-mcp:test
Invoke-RestMethod http://127.0.0.1:18081/healthz
docker stop strobe-mcp-test

npm run build
npm run build:server
docker build -f Dockerfile.agent -t strobe-assistant-agent:test .
docker run --rm -d --name strobe-agent-test -p 18080:8080 strobe-assistant-agent:test
Invoke-RestMethod http://127.0.0.1:18080/healthz
docker stop strobe-agent-test
```

Both health endpoints must return `status: ok`.

## Real AWS acceptance test

1. Upload a JPEG under `userId/postId/fileId`.
2. Confirm EventBridge delivered one message and the classification queue drained.
3. Confirm Lambda logs show classification and embedding without an unhandled error.
4. Read the classification row and verify labels, description, model ID, timestamp, user, post, and object key.
5. Search the same concept through ACP and verify the response includes that object's signed image URL.
6. Inspect the heartbeat rule and a persisted agent-run row whose timestamp predates the live demo.
7. Show the MCP ECS task and ACP agent ECS task as separate services/task definitions.

## Verification record

Local verification completed on 2 October 2026:

- Ruff lint and formatting: passed.
- Python unit tests: 8 passed.
- TypeScript/Vitest tests: 8 passed.
- Vite production build and TypeScript validation: passed.
- MCP Docker health check: passed.
- ACP agent Docker health check: passed.
- Bedrock Titan Text Embeddings V2 live invocation: passed (1,024 dimensions).
- Generative model invocation: blocked by organisation SCP; fallback behavior verified by design and unit tests.
- AWS async acceptance test: passed at 06:29 Asia/Riyadh; SQS was consumed and the classification/vector record was created.
- Scheduled heartbeat invocation: passed at 06:30 Asia/Riyadh; a durable `degraded` agent-run record was created.
- Deployed ACP → private MCP → S3 Vectors query: passed; the dog result and signed inline image rendered in the browser.
- Public health endpoint: `http://n11553758-strobe-agent-1217585299.ap-southeast-2.elb.amazonaws.com/healthz` returned `ok`.

The remaining degradation is an external account-policy restriction, not an unhandled application failure.

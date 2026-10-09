# Assessment requirements traceability

| Requirement | Implementation | Evidence |
|---|---|---|
| Track A over Assessment 1 | Reuses media bucket, users/posts tables, and `userId/postId/fileId` contract | `classification.py`, architecture document |
| Amazon Bedrock foundation model | Nova Lite through Bedrock Converse; explicit degraded response on SCP denial | `bedrock.py`, `strobe-agent.ts`, CloudWatch |
| S3 Vectors | 1,024-dimension cosine index with per-user metadata filter | `vector_store.py`, manifest |
| Dedicated MCP server | FastMCP service and authenticated private adapter in its own ECS service | `mcp_app.py`, ECS services |
| ACP conversational front end | Supplied WebUI plus production ACP WebSocket agent | `web/`, `server/strobe-agent.ts` |
| Images in both directions | ACP image attachments accepted; signed S3 results rendered inline | TS tests and live chat |
| Async event workflow | S3 EventBridge → SQS/DLQ → Lambda classification | `handlers.py`, queue/rule/logs |
| Persisted classification | Dedicated table plus A1 post annotation | `repositories.py`, DynamoDB row |
| Autonomous scheduled run | Daily EventBridge rule → heartbeat Lambda → agent-run table | `heartbeat.py`, timestamped row |
| Secrets Manager | Generated MCP API key stored as secret and resolved at runtime | ECS task definitions/secret ARN |
| ECS | Separate ACP agent and MCP services on Fargate | ECS cluster/service ARNs |
| Managed/serverless architecture | Lambda, SQS, EventBridge, DynamoDB, S3, S3 Vectors, Bedrock | architecture and manifest |
| Naming, region, tags | `n11553758` prefix, `ap-southeast-2`, mandatory tags | deployment inventory |
| Submission manifest descriptions | Deployer writes every dependency with plain-language purpose | `submission-agent-infra.yml` |
| Code quality | OOP services, dependency injection, Ruff, and unit tests | source and tests |
| Documentation and demo | Architecture, deployment, testing, traceability, Arabic presentation script | `docs/` |

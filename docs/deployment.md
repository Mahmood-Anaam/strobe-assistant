# Deployment and operations

## Prerequisites

- AWS CLI v2 authenticated to account `901444280953`
- default region `ap-southeast-2`
- Docker Desktop running
- Node.js 22+, npm, and Python 3.12+
- the shared CAB432 IAM roles referenced by `infra/deploy.py`

Do not copy temporary AWS credentials into `.env`. Verify the profile instead:

```powershell
aws sts get-caller-identity
aws configure get region
```

Expected identity includes account `901444280953`; expected region is `ap-southeast-2`.

## Configuration

Copy `.env.example` to `.env`. The deployer has assessment-safe defaults, but the file remains the authoritative inventory of settings. Never populate `MCP_API_KEY_SECRET_ARN` with a secret value; the deployer creates the secret and ECS consumes its ARN.

## Deploy or update

```powershell
npm ci
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe infra\deploy.py
```

The operation is idempotent and performs these phases:

1. retag reused Assessment 1 S3/DynamoDB resources;
2. enable S3 EventBridge notifications;
3. create new DynamoDB tables, secret, vector bucket/index, queues, Lambda functions, and rules;
4. build and push ACP and MCP images to ECR;
5. use the course network boundary and create ECS definitions/services plus internal MCP and public ACP load balancers;
6. write the exact deployed resources to `submission-agent-infra.yml`.

If only infrastructure wiring changed and both `latest` images exist, run:

```powershell
.\.venv\Scripts\python.exe infra\deploy.py --skip-images
```

## Operational verification

List the ECS state and events:

```powershell
aws ecs describe-services --cluster n11553758-strobe-cluster --services n11553758-strobe-agent n11553758-strobe-mcp --region ap-southeast-2
```

Inspect the asynchronous path:

```powershell
aws sqs get-queue-attributes --queue-url <classification-queue-url> --attribute-names All --region ap-southeast-2
aws logs tail /aws/lambda/n11553758-strobe-classifier --since 10m --region ap-southeast-2
aws dynamodb scan --table-name n11553758-strobe-classifications --max-items 5 --region ap-southeast-2
```

Inspect scheduled evidence:

```powershell
aws events describe-rule --name n11553758-strobe-daily-heartbeat --region ap-southeast-2
aws dynamodb scan --table-name n11553758-strobe-agent-runs --max-items 5 --region ap-southeast-2
```

## Upload a demonstration image

Use a real user and post from Assessment 1. The key must remain exactly three segments:

```powershell
aws s3 cp .\demo.jpg s3://n11553758-strobe-media/<userId>/<postId>/demo.jpg --content-type image/jpeg --region ap-southeast-2
```

Within several seconds, the queue should return to zero, the classifications table should contain the object key and labels, and the vector index should contain a searchable embedding. Do not upload a root-level object: it will fail the contract and eventually reach the DLQ.

## Known CAB432 policy restrictions

As verified on 2 October 2026, the organisation SCP denied runtime invocation of all tested generative Bedrock models. Titan Text Embeddings V2 remained available. The application exposes this state instead of hiding it; see the README for the controlled fallback. Ask teaching staff to restore Bedrock model invocation before the demonstration if generative narration is required.

The same teaching account denies selected nonessential operations such as custom log retention and ECR lifecycle policy updates. The deployer tolerates only those known optional denials; required resource failures still stop deployment.

## Rollback and cleanup

ECS task definitions and ECR images are immutable, so a service can be rolled back to its previous task-definition revision through the AWS console or `aws ecs update-service`. DynamoDB, S3 media, and vector data must not be deleted as part of an application rollback.

Assessment cleanup is intentionally not automated because it would be destructive and the shared account has teaching retention rules. Use AWS Resource Explorer with both mandatory tags, review the exact targets, and remove only resources after marking is complete.

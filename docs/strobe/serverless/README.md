# Strobe AWS Serverless Deployment

This folder contains the deployment implementation for Mesh Alsulami (`n11553758`).

## Architecture

- One HTTP API Gateway in `ap-southeast-2`
- Six Lambda functions: `auth`, `feed`, `moment`, `post`, `user`, `upload`
- Six distinct DynamoDB tables: users, posts, comments, likes, follows, moments
- One private S3 bucket for media, with all public access blocked
- One Cognito User Pool with `user` and `moderator` groups
- DynamoDB point-in-time recovery enabled with a 7-day target retention window where supported

## Deploy

Run from the repository root:

```powershell
conda activate msp
python serverless/deploy.py
```

The deploy script is idempotent and writes the required Gradescope files:

- `submission-infra.yml`
- `submission-routes.yml`

## Verify

After deployment:

```powershell
conda activate msp
python serverless/verify_deployment.py
```

The verifier logs in using the pre-created test account from `submission-infra.yml`, creates a post, comment, like, upload URL, and moment, and checks the deployed endpoint.

# Strobe AWS Deployment Report

Student: Mesh Alsulami (`n11553758`)

QUT username tag: `n11553758@qut.edu.au`

Region: `ap-southeast-2`

## Delivered Files

- `submission-infra.yml`: Gradescope infrastructure manifest.
- `submission-routes.yml`: Gradescope route-to-resource manifest.
- `serverless/lambda_app.py`: AWS Lambda application handler.
- `serverless/deploy.py`: Idempotent AWS deployment script.
- `serverless/verify_deployment.py`: End-to-end verification script.
- `serverless/README.md`: Deployment and verification commands.

## Deployed Endpoint

`https://n11553758.cab432.com`

Raw API Gateway endpoint retained behind the custom domain:
`https://wd3v0i07v3.execute-api.ap-southeast-2.amazonaws.com`

## Architecture

The backend has been migrated from the local FastAPI/JSON-file design to a serverless AWS architecture:

- API Gateway HTTP API: one API, using the `$default` stage and a TLS 1.2 custom domain.
- ACM/Route53: issued certificate and DNS alias for `n11553758.cab432.com`.
- Lambda: separate controller functions for `auth`, `feed`, `moment`, `post`, `user`, and `upload`.
- DynamoDB: six distinct tables for `user`, `post`, `comment`, `like`, `follow`, and `moment`.
- Cognito: managed identity service with `user` and `moderator` groups.
- S3: private media bucket with all public access blocked.

## Security Controls

- Authentication is handled by Cognito access tokens.
- Moderator-only actions are checked against Cognito group membership.
- Account deletion removes the Cognito identity and application-level DynamoDB data.
- S3 public access is blocked at bucket level.
- Upload URLs and media read URLs are short-lived SigV4 presigned URLs.
- DynamoDB point-in-time recovery is enabled with a 7-day retention window where supported by AWS.

## Verification Summary

The verification script completed successfully against the deployed endpoint. It checked:

- Login with the pre-created test account.
- New user registration.
- Duplicate registration rejection.
- Authenticated post creation and retrieval.
- Comment creation persisted to DynamoDB.
- Like creation persisted to DynamoDB.
- Regular user rejection for moderator-only post hide.
- Moderator post hide success.
- SigV4 presigned S3 upload URL generation.
- Direct PUT upload to S3 using only the presigned URL.
- Post update with uploaded image reference.
- Follow creation persisted to DynamoDB.
- Moment creation persisted to DynamoDB.
- Feed retrieval from followed user data.

Latest successful verification changed persisted counts as expected:

- `user`: 8 to 9
- `post`: 8 to 9
- `comment`: 5 to 6
- `like`: 5 to 6
- `follow`: 2 to 3
- `moment`: 3 to 4

## Notes

Autograder v1.0.9 still checks the custom domain and ACM certificate requirements, so the final manifest uses `apiRoute53Record: n11553758.cab432.com` with ACM certificate `arn:aws:acm:ap-southeast-2:901444280953:certificate/3e61fc2c-5f79-4351-b65b-536b5f83e491`.

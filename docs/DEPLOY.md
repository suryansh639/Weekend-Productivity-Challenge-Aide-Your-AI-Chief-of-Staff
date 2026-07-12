# Deploying Aide to AWS

Aide's backend is a SAM application. The frontend is a static build you can host
on S3 + CloudFront (or Amplify Hosting).

## Prerequisites

- An AWS account (Free Tier is fine).
- AWS CLI configured (`aws configure`).
- [AWS SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html).
- **Bedrock model access**: in the Bedrock console → *Model access*, enable
  *Anthropic Claude 3.5 Sonnet* and *Amazon Titan Text Embeddings V2* in your region.

## 1. Deploy the backend

```bash
cd infra
sam build
sam deploy --guided
```

Accept the defaults or override parameters (model id, owner name, CORS origins).
When it finishes, note the `ApiUrl` output — that's your API base URL.

Seed the deployed store once (hits the live API):

```bash
curl -X POST "<ApiUrl>/api/seed"
curl "<ApiUrl>/api/stats"
```

## 2. Deploy the frontend

Build the SPA pointing at your API, then host the static files.

```bash
cd frontend
# point the build at your deployed API
$env:VITE_API_BASE="<ApiUrl>"        # PowerShell   (bash: export VITE_API_BASE=<ApiUrl>)
npm run build                         # outputs frontend/dist

# host on S3 + CloudFront
aws s3 mb s3://aide-frontend-<unique>
aws s3 website s3://aide-frontend-<unique> --index-document index.html
aws s3 sync dist s3://aide-frontend-<unique> --delete
```

For HTTPS + a real URL, put a CloudFront distribution in front of the bucket
(origin access control, default root object `index.html`). Alternatively,
`amplify` or `aws amplify` hosting will build + host directly from the repo.

## 3. AWS services used

| Service | Role |
|---|---|
| **Amazon Bedrock** | Claude (Converse) for triage/prep/nudges; Titan for memory embeddings |
| **AWS Lambda** | FastAPI API + scheduled nudge worker |
| **Amazon API Gateway** | HTTP API front door |
| **Amazon DynamoDB** | Single-table store (items, actions, memory) |
| **Amazon EventBridge Scheduler** | Cron that triggers the proactive nudge scan |
| **Amazon S3 + CloudFront** | Static hosting for the React SPA |

## Cost

All services above have Free Tier allowances that comfortably cover a personal
assistant workload. DynamoDB is on-demand (pay-per-request), Lambda/API Gateway
have large free monthly quotas, and Bedrock is billed per token — a handful of
cents for a demo. Tear down with `sam delete` when you're done.

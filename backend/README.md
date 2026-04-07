# GMS — Gadget Management System (Backend)

AWS serverless backend for managing IT asset lifecycle: procurement, assignment, handover, returns, disposals, repairs, and software governance.

## Tech Stack

- Python 3.12, AWS CDK (Python)
- AWS: Lambda, API Gateway (REST + WebSocket), DynamoDB, Cognito, S3, SQS, DynamoDB Streams, SSM Parameter Store, X-Ray, CloudWatch
- Libraries: aws-lambda-powertools, boto3, simplejson, aws-xray-sdk, opensearch-py, requests + requests-aws4auth

## Project Structure

```
app.py                          # CDK entry point
stacks/                         # CDK stacks (one per domain)
services/lambdas/
  functions/{PascalCaseName}/   # Lambda: lambda_function.py + model.py
  layers/
    shared/python/utils/        # Shared enums, models, pagination, helpers
    dependencies/               # Third-party packages (Powertools, requests, opensearch)
  docker/                       # Docker-based Lambdas (PDF generation, asset scanning)
tests/unit/                     # pytest unit tests (moto for AWS mocking)
scripts/                        # One-off migration and seed scripts
typescript/                     # types.ts — frontend TypeScript types mirroring API responses
helpers/                        # CDK helpers: naming.py, environment.py, lambda_helpers.py
```

## CDK Stacks

| Stack | Purpose |
|-------|---------|
| `storage-stack` | DynamoDB table, S3 buckets |
| `layers-stack` | Lambda layers (shared, dependencies) |
| `auth-stack` | Cognito User Pool + Post Confirmation trigger |
| `api-stack` | API Gateway REST API + authorizer |
| `websocket-stack` | API Gateway WebSocket API |
| `user-stack` | User management Lambdas |
| `asset-stack` | Asset CRUD, approval, assignment, scan |
| `category-stack` | Asset category management |
| `handover-stack` | Handover form generation and signing |
| `return-stack` | Asset return workflow |
| `disposal-stack` | Disposal initiation and review |
| `disposal-notification-stack` | Finance email notifications for disposals |
| `issue-management-stack` | Issue reporting and repair workflow |
| `issue-events-stack` | DynamoDB Streams processor for issue events |
| `maintenance-stack` | Maintenance history stream processor |
| `software-governance-stack` | Software installation request workflow |
| `upload-stack` | Pre-signed S3 upload URL generation |
| `scan-stack` | Asset scan worker and result processor |
| `notification-stack` | In-app notification processor |
| `counter-stack` | Atomic domain ID counter processor |
| `dashboard-stack` | Dashboard stats and recent activity |
| `audit-stack` | Asset audit log |
| `frontend-pipeline-stack` | CI/CD pipeline for frontend deployment |

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
```

## Common CDK Commands

```bash
cdk ls        # list stacks
cdk synth     # synthesize CloudFormation templates
cdk diff      # diff against deployed stack
cdk deploy    # deploy all stacks
```

## Testing

```bash
pytest tests/unit/
```

Unit tests use `pytest` + `moto` for AWS mocking. No integration or e2e tests.

## Key Conventions

- Resource naming via `helpers/naming.py` — never raw f-strings in stack code
- Cross-stack references via SSM Parameter Store (not CDK exports)
- All entity IDs use domain-prefixed format: `{DOMAIN}-{YYYYMM}-{N}` (e.g. `ISSUE-202605-1`)
- Shared enums in `layers/shared/python/utils/enums.py`, Pydantic models in `models.py`
- All list endpoints use offset-based pagination via `utils.pagination.PaginationInput`

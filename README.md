# AWS Gadget Management System (GMS)

A full-stack serverless IT asset lifecycle management system built on AWS. Handles everything from procurement and AI-powered invoice scanning to employee assignment, issue tracking, software governance, returns, and disposal.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12, AWS CDK, 86 Lambda functions |
| Database | DynamoDB (single-table design, 14 GSIs) |
| Storage | S3 (invoices, photos, PDFs, signatures) |
| API | API Gateway REST (100+ endpoints) + WebSocket |
| Auth | Amazon Cognito (4 role-based groups) |
| AI/ML | AWS Textract (invoice OCR) |
| Frontend | React 19, TypeScript, TanStack Start |
| Styling | Tailwind CSS 4, shadcn/ui |
| State | TanStack Query |
| Routing | TanStack Router (file-based) |
| Monitoring | X-Ray, CloudWatch, CloudFront |
| CI/CD | CodePipeline + CodeBuild |

## Features

- Asset lifecycle management (create, approve, assign, return, dispose)
- AI-powered invoice scanning with AWS Textract
- PDF handover form generation with digital signature capture
- Role-based access control (IT Admin, Management, Employee, Finance)
- Issue reporting with repair/warranty/replacement workflows
- Software installation governance with approval workflows
- Real-time WebSocket notifications
- Dashboard with analytics and recent activity
- Complete audit trail logging
- Email notifications via SES + SQS

## Project Structure

```
├── backend/          # AWS CDK + Lambda functions (Python)
│   ├── app.py        # CDK entry point
│   ├── stacks/       # 23 CDK stacks
│   ├── services/     # Lambda functions, layers, Docker images
│   ├── helpers/      # CDK utilities (naming, environment)
│   └── tests/        # pytest unit tests
│
└── frontend/         # React + TanStack Start (TypeScript)
    ├── src/
    │   ├── routes/   # File-based routing
    │   ├── components/
    │   ├── lib/      # API clients, auth, utilities
    │   └── hooks/    # Custom React hooks
    ├── index.html
    └── vite.config.ts
```

## Architecture

100% serverless — no EC2 instances. Uses a single-table DynamoDB design with 14 GSIs, event-driven processing via DynamoDB Streams, and cross-stack references through SSM Parameter Store.

### User Roles

| Role | Capabilities |
|------|-------------|
| IT Admin | Asset CRUD, assignment, issue management, returns, disposals |
| Management | Approval workflows (assets, replacements, software, disposals) |
| Employee | View assigned assets, submit issues, accept handovers, sign returns |
| Finance | View disposal write-off notifications, financial reports |

## Getting Started

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# CDK commands
cdk ls          # list stacks
cdk synth       # synthesize CloudFormation templates
cdk deploy      # deploy all stacks
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Testing

```bash
# Backend
cd backend && pytest tests/unit/

# Frontend
cd frontend && npm run test
```

# Order Management System — AWS Serverless

A fully serverless order management system built on AWS. Supports full CRUD operations on orders, email notification subscriptions, S3-backed deletion backups, and on-demand PDF/CSV report generation.

---

## Architecture

```
                   ┌──────────────────────┐
                   │     AWS Amplify      │
                   │  (React SPA hosted)  │
                   └──────────┬───────────┘
                              │ HTTPS
                   ┌──────────▼───────────┐
                   │    API Gateway       │
                   │  (REST API — prod)   │
                   └──────────┬───────────┘
         ┌────────────────────┼───────────────────┐
         │                    │                   │
┌────────▼────────┐  ┌────────▼────────┐  ┌───────▼────────┐
│  Order Lambdas  │  │ Notification    │  │ Report Lambdas │
│ create / get /  │  │ Lambdas         │  │ export_orders  │
│ update / delete │  │ sub / unsub     │  │ generate_pdf   │
└────────┬────────┘  └────────┬────────┘  └───────┬────────┘
         │                    │                   │
┌────────▼────┐        ┌──────▼──────┐    ┌───────▼────────┐
│  DynamoDB   │        │     SNS     │    │      S3        │
│ orders      │        │ orders-     │    │ orders-bucket  │
│             │        │ notificati- │    │  backups/      │
│ GSI:        │        │ ons         │    │  summaries/    │
│ creation_   │        └──────┬──────┘    │  exports/      │
│ date_index  │               │ fan-out   └───────▲────────┘
└─────────────┘        ┌──────┴──────┐            │
                       │             │            │
                ┌──────▼──┐   ┌──────▼──────┐     │
                │  Email  │   │  SQS Queue  │     │
                │  (A2P)  │   │ orders-     │     │
                └─────────┘   │ backup-     │     │
                              │ queue       │     │
                              └──────┬──────┘     │
                                     │ polls      │
                            ┌────────▼────────┐   │
                            │  backup_order   ├───┘
                            │    Lambda       │
                            └────────┬────────┘
                                     │ on failure (3×)
                            ┌────────▼────────┐
                            │   SQS DLQ       │
                            │ orders-backup-  │
                            │ dlq             │
                            └─────────────────┘
```

---

## AWS Services

| Service | Purpose |
|---|---|
| **AWS Amplify** | Hosts and serves the React SPA over HTTPS |
| **API Gateway** | REST API (prod stage) — routes HTTP requests to Lambda |
| **Lambda** | Business logic — 10 functions, Python 3.12, IAM role: `LabRole` |
| **DynamoDB** | Primary order storage with GSI for efficient sorted queries |
| **S3** | Stores deletion backups (`.txt`), PDF summaries, and CSV exports |
| **SNS** | Fan-out on order deletion: email subscribers + backup Lambda |
| **SQS** | Decouples SNS from backup Lambda; retries failed messages up to 3× |
| **SQS DLQ** | Captures backup messages that failed all 3 retry attempts |

---

## Features

- **Order CRUD** — create, read, update, and delete orders via REST API
- **Email Notifications** — subscribe/unsubscribe to receive alerts when orders are deleted
- **Automatic Backups** — every deleted order is backed up to S3 asynchronously via SNS → SQS → Lambda
- **PDF Summary Report** — generates a formatted PDF of all deleted orders from S3 backups
- **CSV Export** — exports the full live orders table as a downloadable CSV
- **Single-Page Frontend** — React SPA with dark/light theme, stat tiles, and toast notifications

---

## Project Structure

```
Final_Project/
├── client/
│   └── index.html              
├── lambdas/
│   ├── create_order.py
│   ├── get_all_orders.py
│   ├── get_order.py
│   ├── update_order.py
│   ├── delete_order.py
│   ├── subscribe_notification.py
│   ├── unsubscribe_notification.py
│   ├── backup_order.py
│   ├── generate_pdf_summary.py
│   └── export_orders.py
└── README.md
```

---

## API Reference

Base URL: `https://dapejgoi60.execute-api.us-east-1.amazonaws.com/prod`

### Orders

| Method | Path | Description |
|---|---|---|
| `GET` | `/orders` | List all orders |
| `POST` | `/orders` | Create a new order |
| `GET` | `/orders/{order_id}` | Get a single order |
| `PUT` | `/orders/{order_id}` | Update an order |
| `DELETE` | `/orders/{order_id}` | Delete an order and trigger notifications |
| `GET` | `/orders/export` | Export all orders as CSV (pre-signed S3 URL) |
| `GET` | `/orders/summary/pdf` | Generate PDF of deleted orders (pre-signed S3 URL) |

### Notifications

| Method | Path | Description |
|---|---|---|
| `POST` | `/notifications/subscribe` | Subscribe an email to deletion alerts |
| `DELETE` | `/notifications/unsubscribe` | Unsubscribe an email |

### Request / Response Examples

**POST `/orders`**
```json
// Request
{ "description": "Widget A", "price": 49.99 }

// Response 201
{
  "order_id": "uuid",
  "entity_type": "ORDER",
  "description": "Widget A",
  "price": 49.99,
  "creation_date": "2026-05-17T10:00:00Z",
  "last_modified": "2026-05-17T10:00:00Z"
}
```

**POST `/notifications/subscribe`**
```json
// Request
{ "email": "user@example.com" }

// Response 200
{ "message": "Subscription pending. Check your email to confirm." }
```

**PUT `/orders/{order_id}`**
```json
// Request
{ "description": "Standing desk", "price": 300.0 }

// Response 200
{ "order_id": "uuid", "description": "Standing desk", "price": 300.0, "last_modified": "2026-05-17T12:00:00Z" }

// Response 404 — order does not exist (enforced via DynamoDB ConditionExpression)
{ "error": "Order not found" }
```

**DELETE `/orders/{order_id}`**
```json
// Response 200 — returns immediately; email and backup happen asynchronously
{ "message": "Order deleted successfully", "order_id": "uuid" }
```

**GET `/orders/export`**
```json
// Response 200
{
  "csv_url": "https://s3.amazonaws.com/...",
  "total_orders": 42,
  "filename": "orders_20260517_100000.csv"
}
```

---

## Lambda Functions

| Function | Trigger | Env Vars | AWS Services |
|---|---|---|---|
| `create_order` | API Gateway POST | `TABLE_NAME` | DynamoDB |
| `get_all_orders` | API Gateway GET | `TABLE_NAME` | DynamoDB (GSI) |
| `get_order` | API Gateway GET | `TABLE_NAME` | DynamoDB |
| `update_order` | API Gateway PUT | `TABLE_NAME` | DynamoDB |
| `delete_order` | API Gateway DELETE | `TABLE_NAME`, `SNS_TOPIC_ARN` | DynamoDB, SNS |
| `subscribe_notification` | API Gateway POST | `SNS_TOPIC_ARN` | SNS |
| `unsubscribe_notification` | API Gateway DELETE | `SNS_TOPIC_ARN` | SNS |
| `backup_order` | SQS (via SNS fan-out) | `BUCKET_NAME` | S3 — unwraps the SNS envelope from the SQS record before processing |
| `generate_pdf_summary` | API Gateway GET | `BUCKET_NAME` | S3 |
| `export_orders` | API Gateway GET | `TABLE_NAME`, `BUCKET_NAME` | DynamoDB, S3 |

---

## Environment Variables

Each Lambda function requires the following environment variables set in its configuration:

| Variable | Used By | Description |
|---|---|---|
| `TABLE_NAME` | CRUD + export Lambdas | DynamoDB table name |
| `SNS_TOPIC_ARN` | delete, subscribe, unsubscribe | Full ARN of the SNS topic |
| `BUCKET_NAME` | backup, generate_pdf, export | S3 bucket name for reports and backups |

---

## Infrastructure Setup

> No IaC files are included — resources must be provisioned manually or via your preferred tool (SAM / CDK / Terraform).

### Required AWS Resources

**DynamoDB Table**
- Partition key: `order_id` (String)
- GSI: `creation_date_index` — partition key `entity_type` (String), sort key `creation_date` (String)

**S3 Bucket**
- No public access; Lambda uses pre-signed URLs for client downloads
- Folders created automatically: `backups/`, `summaries/`, `exports/`

**SNS Topic**
- Standard topic (not FIFO)
- One SQS subscription (triggers `backup_order`)
- Email subscriptions managed at runtime via the subscribe/unsubscribe API

**SQS Queue** (`orders-backup-queue`)
- Standard queue subscribed to the SNS topic
- Event source for the `backup_order` Lambda (Lambda polls the queue)
- Max receive count: 3 — messages are retried up to 3 times on Lambda failure

**SQS Dead Letter Queue** (`orders-backup-dlq`)
- Receives messages that exhausted all 3 retries
- Inspect the DLQ to diagnose failures and reprocess messages manually

**API Gateway**
- REST API with CORS enabled (`Access-Control-Allow-Origin: *`)
- Lambda proxy integration for all routes

### Python Dependencies

The `generate_pdf_summary` Lambda requires `reportlab`, which is not in the Lambda runtime by default. Package it as a Lambda layer or include it in a deployment ZIP:

```bash
pip install reportlab -t ./layer/python
```

All other Lambdas use only `boto3` and the Python standard library, which are available in the default Lambda runtime.

---

## Frontend

The client is a single-file React SPA (`client/index.html`) with no build step. It loads React 18, ReactDOM, and Babel via CDN and transpiles JSX in the browser.

**Hosting:** AWS Amplify — **Live URL:** `https://staging.d12d32aqzx4uwe.amplifyapp.com/`

To point it at a different API, update the `API_BASE` constant near the top of `index.html`:

```js
const API_BASE = 'https://<your-api-id>.execute-api.us-east-1.amazonaws.com/prod';
```

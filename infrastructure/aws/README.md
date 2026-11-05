# AWS deployment reference

This is a **reference**, not a deployed stack. No live infrastructure is claimed.

## Recommended topology
- **ALB → ECS Fargate (backend)** · stateless; min 2 tasks for availability.
- **ECS Fargate (agent worker)** · consumes `agents-work` SQS queue; horizontal scale.
- **RDS Postgres** · multi-AZ; read replica for analytics endpoints if latency warrants.
- **S3** · synthetic data uploads, ML artifacts, exported evidence.
- **SNS → SQS fan-out** · one topic per event type, or EventBridge if the fleet has
  cross-service subscribers.
- **CloudWatch** + **OTEL collector** sidecar on each task → APM backend of choice.

## Event mapping
| Domain event | SNS topic | Consumer (SQS) |
|---|---|---|
| StockoutRiskDetected | `ct.stockout.detected` | `agents-work` |
| SupplierRiskDetected | `ct.supplier.detected` | `agents-work`, `notifications` |
| RecommendationGenerated | `ct.recommendation.generated` | `notifications` |
| RecommendationApproved | `ct.recommendation.approved` | `audit`, `action-adapter` |
| ActionExecuted | `ct.action.executed` | `audit` |

## Secrets
- `APP_SECRET_KEY`, `DATABASE_URL`, `OPENAI_API_KEY`/`AWS` → AWS Secrets Manager;
  injected into the task definition as `secret_arn` references, never in plaintext.

## Scaling levers
- Horizontal: increase desired ECS task count. Backend and agents are both stateless.
- Vertical: raise agent worker CPU first if GBM training becomes the bottleneck.
- Cost: back-pressure via SQS visibility timeout and the agent `max_steps` budget.

---
*Author: **Pradeep Sahoo**.*

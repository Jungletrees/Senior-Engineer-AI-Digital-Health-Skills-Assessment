# Production Deployment Plan

This document is the production deployment plan for the Last Mile Health RAG platform. It is not evidence that the system is already deployed. The repository currently contains Docker/Compose assets, but no Terraform/CDK/CloudFormation stack and no `.github/workflows/` directory.

## Target AWS Architecture

```text
CloudFront + WAF
      |
      v
Application Load Balancer or API Gateway
      |
      +--> Next.js frontend
      +--> Chainlit chat UI, after backend chat wiring is complete
      +--> FastAPI backend
              |
              +--> RDS PostgreSQL 16 + pgvector, private subnets
              +--> S3 private buckets for PDFs and page images
              +--> Bedrock or hosted model providers
              +--> Secrets Manager / SSM Parameter Store
              +--> CloudWatch logs, metrics, traces, dashboards
```

Recommended components:

| Layer | AWS choice | Rationale |
|---|---|---|
| Frontend | S3 + CloudFront for a static build, or ECS Fargate/App Runner for current Next.js server runtime | CloudFront gives edge caching when static; Fargate/App Runner avoids changing runtime assumptions. |
| Backend API | ECS Fargate for the current container | Warm container is better for local reranker loading, PDF parsing/OCR, and async DB pooling. |
| Chainlit | ECS Fargate behind ALB after wiring to `/api/v1/chat` | Keeps chat isolated while sharing backend logic. Omit from production until wired. |
| Database | Amazon RDS PostgreSQL 16 with pgvector | Managed backups, Multi-AZ, encryption, and PostgreSQL extension support. |
| Object storage | Amazon S3 private buckets | Durable storage for uploaded PDFs and rasterized page images. |
| Secrets | Secrets Manager or SSM Parameter Store | Runtime injection without committing or baking secrets into images. |
| Network boundary | CloudFront/WAF + ALB or API Gateway | Rate, bot, and request filtering before app services. |
| Networking | VPC with public ALB/API boundary and private app/database subnets | Database is never public; app egress is controlled. |
| IAM | Task/Lambda roles with least privilege | S3, Bedrock, CloudWatch, and secret access are scoped per workload. |

## Lambda Compute Rationale

Lambda is a strong fit for bursty, event-driven and idle-cost-sensitive workloads:

- corpus evaluation triggers
- scheduled grading kicks
- lightweight ingestion dispatch
- post-upload fanout events
- small health/smoke handlers
- notification and anomaly alert delivery

Lambda is not ideal for long-running local model inference, local CrossEncoder reranking, heavyweight CPU/GPU workloads, large PDF OCR/rasterization, or request paths that need a warm database pool without RDS Proxy. Those workloads should use ECS Fargate, Bedrock-hosted models, or queue-backed workers.

If the API is split onto Lambda, use API Gateway + Lambda + RDS Proxy. Mitigate cold starts with small deployment packages, provisioned concurrency for latency-sensitive handlers, model calls delegated to Bedrock, and no local ML model loading in function startup.

| Compute option | Use when | Trade-off |
|---|---|---|
| Lambda | Bursty jobs, event triggers, lightweight handlers | Cold starts, timeout limits, RDS Proxy needed for pooling |
| ECS Fargate | Current backend, OCR/PDF work, local reranker, persistent pool | Higher idle cost than Lambda |
| App Runner | Simple container deploy with fewer knobs | Less VPC/routing control than ECS |
| EKS | Many services and platform team ownership | Too much operational overhead for this scope |
| EC2 | Full host control or special hardware | Manual patching/scaling burden |

## Bedrock Model Switching and Cost Optimization

Amazon Bedrock is the preferred production model access layer where organizational governance, centralized model permissions, and AWS-native billing controls are required.

Routing policy:

- fast/low-cost model: summaries, classification, grading prechecks, query expansion, and low-risk transformations
- stronger model: final grounded answer generation and complex clinical reasoning
- pinned judge model: `JudgeAgent` uses a fixed model, temperature, and rubric version so trends are reproducible

Cost controls:

- Track per-model input/output token usage and cost through `MODEL_PRICING_JSON` or a Bedrock-aware equivalent.
- Configure AWS Budgets and CloudWatch anomaly alerts for model cost spikes.
- Keep exact cache, semantic cache, and prompt caching enabled only where safe.
- Run refusal/grounding gates before caching generated answers.
- Preserve exact numeric grounding regardless of which model produces the answer.

## Reliability and Scalability

- FastAPI uses async request handling and async SQLAlchemy sessions.
- Use RDS Proxy when Lambda handlers connect to RDS.
- Keep scheduler jobs behind PostgreSQL advisory-lock singleton guards so horizontal replicas do not duplicate work.
- Make ingestion and gold-eval jobs idempotent around document content hashes, run IDs, and audit lineage.
- Move large PDF processing to queue/event-backed workers at scale: S3 upload event -> SQS/EventBridge -> worker/Lambda/ECS task.
- Set autoscaling boundaries separately for frontend, backend, Chainlit, and worker tasks.
- Run RDS Multi-AZ with automated backups and periodic restore tests.
- Use S3 versioning/lifecycle rules and KMS encryption for PDFs and page images.
- Add ALB/API readiness checks against `/health`, plus deeper smoke checks after deployment.
- Keep WAF and application rate limits active; tune per-IP/session limits from observed traffic.
- Build CloudWatch dashboards for p95 latency, 5xx rate, cache hit rate, grounding failures, cost, anomaly flags, and gold-eval score trends.

## Security

- No hardcoded secrets. `.env` stays local and ignored; production secrets are injected from Secrets Manager or SSM.
- JWT session tokens protect document-management endpoints; `ANONYMOUS_CHAT_ALLOWED` controls chat access.
- CORS must be explicit per environment.
- Upload validation checks PDF magic bytes, MIME allow-list, size, and page count.
- S3 buckets remain private with bucket policies, KMS encryption, and no public ACLs.
- RDS, S3, Secrets Manager, and model-provider secrets use KMS encryption.
- ECS task and Lambda roles use least privilege; no static AWS access keys are needed.
- RDS is private and reachable only from backend/worker security groups.
- Bedrock access is least privilege by model/action and environment.
- Audit logs, `query_audit_log`, `agent_trace_log`, `response_grade`, and `anomaly_flag` support investigation.
- PII/sensitive-output guardrails should be kept before response send and before cache writes.

## CI/CD Plan

No GitHub Actions workflows are currently present. The intended pipeline is:

1. PR checks run backend `pytest`, frontend `npm test`, lint/typecheck where configured, Docker backend build, and Alembic migration validation.
2. Main branch deployment is gated with explicit `needs:` dependencies on all required checks.
3. Containers are built and pushed to Amazon ECR.
4. Infrastructure is deployed with Terraform, CDK, or CloudFormation.
5. Alembic migrations run as a one-off task against the target environment before backend rollout.
6. Environments are separated into dev, staging, and prod with distinct AWS accounts or at least distinct VPCs/secrets/databases.
7. Production requires manual approval.
8. Secrets are injected from Secrets Manager or SSM at runtime.
9. Post-deploy smoke tests hit `/health`, OpenAPI docs, a minimal upload path, and a minimal chat path.
10. Rollback returns services to the previous image/task definition and, when necessary, restores from RDS point-in-time recovery.
11. Gold-eval floor gating can be added after corpus PDFs are pinned, indexed, and expected answers are human-verified.

## Migration and Data Strategy

- Alembic remains the database migration tool.
- Migrations should run in staging before prod.
- Production migrations should be backward-compatible where possible, especially for rolling deployments.
- Use RDS snapshots and point-in-time recovery before risky migrations.
- Keep uploaded PDFs and page images in S3, not container filesystems.
- Do not commit downloaded PDFs, generated gold reports, local database volumes, pycache, Playwright reports, secrets, or `.env`.

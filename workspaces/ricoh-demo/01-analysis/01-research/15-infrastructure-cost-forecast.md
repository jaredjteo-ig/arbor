# Central HR Platform — Infrastructure & Cost Forecast for Ricoh Thailand

**For**: Client presentation / commercial proposal
**Date**: 2026-03-31
**Region**: AWS ap-southeast-1 (Singapore)

---

## At a Glance

|                          | HR Branch Pilot | Full Workforce                             |
| ------------------------ | --------------- | ------------------------------------------ |
| **Users**                | 20-50 HR admins | 2,000 employees + 50 HR admins             |
| **Monthly cost**         | **~$43**        | **~$180 - $295**                           |
| **Annual cost**          | **~$516**       | **~$2,157 - $3,541**                       |
| **Per employee/month**   | **$0.22**       | **$0.09 - $0.15**                          |
| **vs. traditional HRIS** | —               | **$4-10/employee/month = $96K-$240K/year** |

LLM API costs represent only 5-8% of total cost. Compute is the primary expense. Even at full scale with production-grade managed services, the platform costs under $300/month — compared to $8,000-$20,000/month for a traditional HRIS serving 2,000 employees.

---

## What Runs

Five containers on a single server:

| Container     | Purpose                                                | Memory         |
| ------------- | ------------------------------------------------------ | -------------- |
| Caddy         | Reverse proxy, auto-HTTPS (Let's Encrypt)              | ~50 MB         |
| Backend       | FastAPI + advisory engine + calculators + shadow agent | ~1-2 GB        |
| Frontend      | Next.js (standalone mode)                              | ~200-400 MB    |
| PostgreSQL 16 | Primary database + pgvector (KB embeddings)            | ~500 MB - 2 GB |
| Redis 7       | Session management, response cache                     | ~100 MB        |

---

## Scenario A: HR Branch Pilot

**Who uses it**: 20-50 HR managers and admins. No employee self-service yet. ~200 employees managed in the system.

**Usage profile**: ~50 advisory queries/day, ~5 payroll runs/month, ~25 shadow agent interactions/day.

### Infrastructure

| Component         | Specification                           | Monthly Cost |
| ----------------- | --------------------------------------- | ------------ |
| EC2 instance      | t3.medium (2 vCPU, 4 GB RAM)            | $33          |
| Storage           | 30 GB EBS gp3                           | $2           |
| Data transfer     | ~5 GB outbound                          | $0.50        |
| Elastic IP        | Attached to instance                    | $0           |
| Database          | PostgreSQL in Docker (on same instance) | $0           |
| Cache             | Redis in Docker (on same instance)      | $0           |
| **Compute total** |                                         | **~$36**     |

### LLM API (Gemini 2.5 Flash)

| Call Type                                | Volume/Month  | Cost/Call | Monthly |
| ---------------------------------------- | ------------- | --------- | ------- |
| Advisory queries (scope screen + engine) | 1,500         | $0.002    | $3.00   |
| Shadow Agent intent classification       | 750           | $0.0003   | $0.23   |
| KB embeddings (one-time load)            | 89 provisions | —         | ~$0.01  |
| **LLM total**                            |               |           | **~$3** |

**How $0.002/query breaks down**: Each advisory query makes 2-3 Gemini API calls (scope screening at 300 tokens, then 1-2 tool-calling rounds at ~6,500 tokens total). At Gemini 2.5 Flash pricing ($0.15/M input, $0.60/M output), a typical query costs ~$0.0015.

### Operations

| Item                           | Monthly |
| ------------------------------ | ------- |
| Domain + DNS                   | $1      |
| SSL (Let's Encrypt)            | $0      |
| Email (AWS SES, ~200 payslips) | $0.50   |
| Database backups (S3, 1 GB)    | $0.50   |
| Monitoring (CloudWatch basic)  | $2      |
| **Ops total**                  | **~$4** |

### Pilot Total

| Category   | Monthly | Annual   |
| ---------- | ------- | -------- |
| Compute    | $36     | $432     |
| LLM API    | $3      | $36      |
| Operations | $4      | $48      |
| **Total**  | **$43** | **$516** |

With 1-year reserved EC2: **$31/month, $367/year** (save 37% on compute).

---

## Scenario B: Full Workforce (2,000 Employees)

**Who uses it**: 2,000 employees on self-service (leave, payslips, attendance, claims) + 50 HR admins on advisory + operational features.

**Usage profile**: ~200 advisory queries/day, ~2,000 self-service sessions/day, ~400 shadow agent interactions/day, monthly payroll for 2,000.

### Infrastructure — Budget Path (All Containerized)

| Component         | Specification                 | Monthly Cost |
| ----------------- | ----------------------------- | ------------ |
| EC2 instance      | t3.xlarge (4 vCPU, 16 GB RAM) | $134         |
| Storage           | 100 GB EBS gp3                | $8           |
| Data transfer     | ~50 GB outbound               | $4.50        |
| Elastic IP        | Attached                      | $0           |
| Database          | PostgreSQL in Docker          | $0           |
| Cache             | Redis in Docker               | $0           |
| **Compute total** |                               | **~$146**    |

### Infrastructure — Production Path (Managed Services)

| Component         | Specification                       | Monthly Cost |
| ----------------- | ----------------------------------- | ------------ |
| EC2 instance      | t3.xlarge (4 vCPU, 16 GB RAM)       | $134         |
| Storage           | 100 GB EBS gp3                      | $8           |
| Data transfer     | ~50 GB outbound                     | $4.50        |
| Elastic IP        | Attached                            | $0           |
| Load balancer     | Application LB                      | $27          |
| RDS PostgreSQL    | db.t3.medium (2 vCPU, 4 GB) + 20 GB | $62          |
| ElastiCache Redis | cache.t3.small (1.37 GB)            | $26          |
| **Compute total** |                                     | **~$262**    |

**Why the production path**: RDS gives you automated backups, point-in-time recovery, and optional Multi-AZ failover. For a Fortune Global 500 subsidiary expecting SLA guarantees, this is the defensible choice. The extra ~$88/month buys operational resilience.

### LLM API (Gemini 2.5 Flash)

| Call Type            | Volume/Month | Cost/Call | Monthly  |
| -------------------- | ------------ | --------- | -------- |
| Advisory queries     | 6,000        | $0.002    | $12.00   |
| Shadow Agent intent  | 12,000       | $0.0003   | $3.60    |
| KB embedding updates | Negligible   | —         | $0       |
| **LLM total**        |              |           | **~$16** |

### Operations

| Item                                         | Monthly     |
| -------------------------------------------- | ----------- |
| Domain + DNS                                 | $1          |
| SSL (Let's Encrypt)                          | $0          |
| Email (SES, ~2,000 payslips + notifications) | $2          |
| Database backups (S3 or RDS built-in)        | $2.50       |
| Monitoring (CloudWatch)                      | $5-10       |
| Uptime monitoring                            | $5          |
| **Ops total**                                | **~$16-20** |

### Full Workforce Total

| Category          | Budget Path | Production Path |
| ----------------- | ----------- | --------------- |
| Compute           | $146        | $262            |
| LLM API           | $16         | $16             |
| Operations        | $18         | $18             |
| **Monthly total** | **$180**    | **$296**        |
| **Annual total**  | **$2,160**  | **$3,552**      |

With 1-year reserved: **$130/month ($1,562/yr)** budget or **$213/month ($2,557/yr)** production.

---

## LLM Cost Sensitivity — If Model Changes

The platform supports multiple AI providers. If a more capable model is needed later:

| Model                          | Cost/Query | Monthly (6K queries) | Annual |
| ------------------------------ | ---------- | -------------------- | ------ |
| **Gemini 2.5 Flash** (current) | $0.002     | $12                  | $144   |
| Gemini 2.5 Pro                 | $0.016     | $96                  | $1,152 |
| Claude Haiku 4.5               | $0.010     | $60                  | $720   |
| Claude Sonnet 4                | $0.038     | $228                 | $2,736 |
| OpenAI GPT-4o                  | $0.012     | $72                  | $864   |

Even with the most expensive model (Claude Sonnet 4), LLM costs remain under $230/month — still a fraction of traditional HR consulting fees.

---

## Cost Comparison vs Traditional HR Tools

| Solution                           | 2,000 Employees/Month | Annual      |
| ---------------------------------- | --------------------- | ----------- |
| SAP SuccessFactors                 | $16,000-$40,000       | $192K-$480K |
| Workday                            | $12,000-$20,000       | $144K-$240K |
| BambooHR / Personio                | $8,000-$20,000        | $96K-$240K  |
| Thai local HRIS (Humanica, ByteHR) | $4,000-$10,000        | $48K-$120K  |
| **Central (budget path)**          | **$180**              | **$2,160**  |
| **Central (production path)**      | **$296**              | **$3,552**  |

Central's total infrastructure cost is **less than what traditional HRIS vendors charge for a single employee per month**.

---

## Scaling Path

| Milestone                      | Infrastructure Change              | Cost Impact                              |
| ------------------------------ | ---------------------------------- | ---------------------------------------- |
| **Pilot → Full workforce**     | t3.medium → t3.xlarge              | +$100/month                              |
| **Add RDS + ElastiCache**      | Containerized → managed            | +$88/month                               |
| **Add Thailand KB**            | Same infrastructure, new content   | +$0 infrastructure, one-time development |
| **Add 2nd ASEAN country**      | Same infrastructure, new KB module | +$0 infrastructure                       |
| **Scale to 5,000+ employees**  | Add second EC2 behind ALB          | +$134/month                              |
| **Scale to 10,000+ employees** | Consider ECS Fargate or EKS        | Architecture review needed               |

The architecture scales vertically (bigger instance) up to ~5,000 employees on a single server. Beyond that, horizontal scaling with a load balancer is straightforward — the backend is stateless (session state in Redis, data in PostgreSQL).

---

## One-Time Setup Costs

| Item                                 | Cost                          | Notes                    |
| ------------------------------------ | ----------------------------- | ------------------------ |
| AWS account setup                    | $0                            | Free                     |
| Domain registration                  | $10-15/year                   | If new domain needed     |
| Thai KB development (PoC: 3 domains) | Development cost              | 4-6 weeks                |
| Thai legal counsel validation        | THB 50K-150K (~$1,400-$4,300) | Chandler MHM recommended |
| Data migration (from existing HRIS)  | Development cost              | Depends on source system |
| Gemini API key (billing-enabled)     | $0 setup                      | Pay-as-you-go            |

---

## What's Included at No Extra Infrastructure Cost

These features run on the same infrastructure — no additional services or API costs:

- All 22 HRIS modules (payroll, leave, attendance, claims, shifts, recruitment, appraisals, projects, inventory, documents, compliance, reports, alerts, emergency, approvals, policies, company profile, client management, help, settings, auth, search)
- 7 deterministic calculators (zero LLM cost)
- 89+ KB provisions with semantic search
- 13-step safety chain
- EATP trust lineage (cryptographic audit trail)
- Shadow agent (context, briefing, nudges — deterministic, no LLM cost)
- Full mobile app (Flutter)
- Multi-provider BYOK support
- PDPA compliance features
- Tenant isolation and security

The only per-usage cost is LLM API calls (~$0.002/advisory query).

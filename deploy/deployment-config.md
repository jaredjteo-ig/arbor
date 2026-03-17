# AITE Deployment Configuration

## Decision Summary

| Decision       | Choice                                   | Rationale                                                    |
| -------------- | ---------------------------------------- | ------------------------------------------------------------ |
| Cloud provider | AWS (ap-southeast-1)                     | Existing Integrum account with unused reserved instances     |
| Instance type  | t2.medium                                | Utilizing pre-paid reserved instance capacity                |
| Orchestration  | Docker Compose                           | Single-server deployment, simpler than K8s for current scale |
| Reverse proxy  | Caddy                                    | Zero-config automatic HTTPS with Let's Encrypt               |
| Domain         | aite.kailash.ai                          | Route53 A record to Elastic IP                               |
| Database       | PostgreSQL 16 + pgvector (containerized) | Vector search for KB embeddings                              |
| Cache          | Redis 7 (containerized)                  | Session management                                           |

## Architecture

```
Internet
  │
  ▼
┌──────────────────────────────────────────────────────────┐
│  EC2 t2.medium (i-0632bfeef01ee415b)                     │
│  Amazon Linux 2023 │ Elastic IP: 52.220.50.167           │
│                                                          │
│  ┌─────────────────────────────────────────────┐         │
│  │ Caddy (aite-caddy)         ports 80, 443    │         │
│  │ Auto HTTPS via Let's Encrypt                │         │
│  │ /api/* → backend:8000                       │         │
│  │ /*     → frontend:3000                      │         │
│  └────────┬──────────────────┬─────────────────┘         │
│           │                  │                           │
│  ┌────────▼────────┐  ┌─────▼──────────────┐            │
│  │ Next.js (3000)  │  │ FastAPI (8000)     │            │
│  │ aite-frontend   │  │ aite-backend       │            │
│  │ standalone mode  │  │ AsyncLocalRuntime  │            │
│  └─────────────────┘  └──┬─────────┬───────┘            │
│                          │         │                     │
│  ┌───────────────────────▼┐  ┌─────▼──────────────────┐ │
│  │ PostgreSQL 16 (5432)   │  │ Redis 7 (6379)         │ │
│  │ aite-postgres           │  │ aite-redis              │ │
│  │ pgvector extension     │  │ password-protected     │ │
│  │ Volume: aite_pgdata    │  │ Volume: aite_redis     │ │
│  └────────────────────────┘  └────────────────────────┘ │
└──────────────────────────────────────────────────────────┘
```

## AWS Infrastructure

| Resource       | ID / Value                                     |
| -------------- | ---------------------------------------------- |
| EC2 Instance   | `i-0632bfeef01ee415b`                          |
| Instance Type  | `t2.medium` (reserved)                         |
| AMI            | Amazon Linux 2023                              |
| Elastic IP     | `52.220.50.167`                                |
| Security Group | `sg-08193a91dc92c2bfc` (aite-kailash)          |
| VPC            | `vpc-22408344`                                 |
| Subnet         | `subnet-b8ca7dde` (ap-southeast-1a)            |
| Key Pair       | `ai-coach` (~/.ssh/ai-coach.pem)               |
| Route53 Zone   | `Z0197289202NLLMMA8HP0` (kailash.ai)           |
| DNS Record     | `aite.kailash.ai` → `52.220.50.167` (A record) |
| AWS Account    | `884647653201` (integrumglobal)                |
| AWS Profile    | `esperie`                                      |
| Region         | `ap-southeast-1` (Singapore)                   |

### Security Group Rules

| Port | Protocol | Source    | Purpose                   |
| ---- | -------- | --------- | ------------------------- |
| 22   | TCP      | 0.0.0.0/0 | SSH                       |
| 80   | TCP      | 0.0.0.0/0 | HTTP (redirects to HTTPS) |
| 443  | TCP      | 0.0.0.0/0 | HTTPS                     |

## Container Images

### Backend (Python)

- Dockerfile: `deploy/Dockerfile.backend`
- Base: `python:3.11-slim`
- Runtime: `AsyncLocalRuntime` (required for containers — LocalRuntime hangs)
- Entrypoint: `python -m hr_advisory.api.server`
- Health check: `GET /health`
- Port: 8000

### Frontend (React/Next.js)

- Dockerfile: `deploy/Dockerfile.frontend`
- Base: `node:20-alpine` (build) → `node:20-alpine` (runtime)
- Build: `npm run build` with `output: "standalone"`
- Port: 3000

## Environment Variables

### Required (set in deploy/.env.prod)

| Variable            | Description                     |
| ------------------- | ------------------------------- |
| `DATABASE_URL`      | PostgreSQL connection string    |
| `POSTGRES_USER`     | PostgreSQL username             |
| `POSTGRES_PASSWORD` | PostgreSQL password             |
| `POSTGRES_DB`       | PostgreSQL database name        |
| `REDIS_URL`         | Redis connection string         |
| `REDIS_PASSWORD`    | Redis password                  |
| `JWT_SECRET_KEY`    | JWT signing key                 |
| `OPENAI_API_KEY`    | OpenAI API key (for LLM agents) |

### Optional

| Variable            | Default                   | Description          |
| ------------------- | ------------------------- | -------------------- |
| `ANTHROPIC_API_KEY` | —                         | Anthropic API key    |
| `DEFAULT_LLM_MODEL` | `gpt-4o`                  | Default LLM model    |
| `LOG_LEVEL`         | `INFO`                    | Logging level        |
| `APP_ENV`           | `production`              | Environment name     |
| `CORS_ORIGINS`      | `https://aite.kailash.ai` | Allowed CORS origins |

### Integration Layer (MCP Servers — all optional, enable as needed)

| Variable                     | Default       | Description                                                    |
| ---------------------------- | ------------- | -------------------------------------------------------------- |
| `INTEGRATION_ENCRYPTION_KEY` | —             | Fernet key for OAuth token encryption (REQUIRED in production) |
| `ENVIRONMENT`                | `development` | Set to `production` to enforce encryption key                  |
| `DATA_GOV_SG_API_KEY`        | —             | data.gov.sg API key (free, self-service)                       |
| `RESEND_API_KEY`             | —             | Resend email delivery                                          |
| `TELEGRAM_BOT_TOKEN`         | —             | Telegram notification bot                                      |
| `TELEGRAM_MONITOR_BOT_TOKEN` | —             | Telegram regulatory monitoring bot                             |
| `WHATSAPP_ACCESS_TOKEN`      | —             | WhatsApp Cloud API token                                       |
| `WHATSAPP_PHONE_NUMBER_ID`   | —             | WhatsApp phone number ID                                       |
| `SLACK_BOT_TOKEN`            | —             | Slack bot token                                                |
| `AWS_S3_BUCKET`              | —             | S3 bucket for document storage                                 |
| `XERO_CLIENT_ID`             | —             | Xero OAuth app client ID                                       |
| `XERO_CLIENT_SECRET`         | —             | Xero OAuth app client secret                                   |
| `QBO_CLIENT_ID`              | —             | QuickBooks OAuth client ID                                     |
| `QBO_CLIENT_SECRET`          | —             | QuickBooks OAuth client secret                                 |
| `ZOHO_CLIENT_ID`             | —             | Zoho Books OAuth client ID                                     |
| `ZOHO_CLIENT_SECRET`         | —             | Zoho Books OAuth client secret                                 |
| `ASPIRE_CLIENT_ID`           | —             | Aspire API client ID                                           |
| `ASPIRE_API_KEY`             | —             | Aspire API key                                                 |
| `WISE_API_KEY`               | —             | Wise Business API key                                          |
| `SSG_API_KEY`                | —             | SkillsFuture SSG developer portal key                          |

**Note**: Integration env vars are only needed when enabling specific connectors. The platform starts and runs without them — connectors gracefully degrade to "not configured" status.

## SSL/TLS

- Provider: Let's Encrypt (automated via Caddy)
- Certificate CN: `aite.kailash.ai`
- Renewal: Automatic (Caddy handles renewal before expiry)
- HSTS: Enabled (`max-age=31536000; includeSubDomains`)
- Security headers: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`

## Deployment Runbook

### Prerequisites

- AWS CLI configured with SSO profile `esperie`
- SSH key `~/.ssh/ai-coach.pem`

### Deploy New Version

```bash
# 1. SSH into server
ssh -i ~/.ssh/ai-coach.pem ec2-user@52.220.50.167

# 2. Sync code (from local machine)
rsync -avz --exclude='.git' --exclude='node_modules' --exclude='.venv' \
  --exclude='__pycache__' --exclude='.next' --exclude='*.pyc' \
  -e "ssh -i ~/.ssh/ai-coach.pem" \
  . ec2-user@52.220.50.167:/opt/aite/

# 3. On server: rebuild and restart
cd /opt/aite/deploy
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build

# 4. Verify
docker ps  # all 5 containers healthy
curl -f https://aite.kailash.ai/health  # 200 OK
```

### Rollback

```bash
# SSH into server
ssh -i ~/.ssh/ai-coach.pem ec2-user@52.220.50.167

# Roll back to previous code
cd /opt/aite
git checkout <previous-commit>

# Rebuild
cd deploy
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build

# Verify
curl -f https://aite.kailash.ai/health
```

### Server Setup (fresh instance)

```bash
# From local machine — provision a fresh Amazon Linux 2023 instance
ssh ec2-user@<IP> 'bash -s' < deploy/setup-server.sh
```

## Health Check Endpoints

| Endpoint           | Method | Expected | Description               |
| ------------------ | ------ | -------- | ------------------------- |
| `/health`          | GET    | 200 OK   | Basic liveness            |
| `/health/ready`    | GET    | 200 OK   | Readiness (DB connected)  |
| `/health/detailed` | GET    | 200 OK   | Detailed component status |

## Backup and Recovery

### Database Backups

- Daily automated backups via `pg_dump`
- Retain 30 days of daily backups
- Weekly backups retained for 90 days
- Data volume: `aite_pgdata` (persistent Docker volume)

### Recovery Procedure

1. Stop application containers
2. Restore PostgreSQL from backup
3. Verify data integrity
4. Restart application containers
5. Run health checks
6. Verify advisory responses

## Monitoring (TODO)

Not yet configured. When ready:

- Health check: `GET /health` (Caddy handles basic uptime)
- Consider: AWS CloudWatch, Uptime Robot, or similar
- Alert on: container restarts, 5xx errors, disk usage > 80%

## Cost

- EC2 t2.medium: **$0** (using pre-paid reserved instance)
- EIP: $0 (attached to running instance)
- Route53: ~$0.50/month (hosted zone)
- Data transfer: Variable (~$0.12/GB outbound)
- **Estimated monthly: < $5**

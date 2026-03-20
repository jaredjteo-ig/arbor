# Arbor Deployment Configuration

## Decision Summary

| Decision       | Choice                                   | Rationale                                                    |
| -------------- | ---------------------------------------- | ------------------------------------------------------------ |
| Cloud provider | GCP (asia-southeast1)                    | Terrene Foundation GCP account (terrene-care project)        |
| Instance type  | e2-medium                                | Cost-effective for current scale                             |
| Orchestration  | Docker Compose                           | Single-server deployment, simpler than K8s for current scale |
| Reverse proxy  | Caddy                                    | Zero-config automatic HTTPS with Let's Encrypt               |
| Domain         | arbor.terrene.foundation                 | DNS A record to GCE static IP                                |
| Database       | PostgreSQL 16 + pgvector (containerized) | Vector search for KB embeddings                              |
| Cache          | Redis 7 (containerized)                  | Session management                                           |

## Architecture

```
Internet
  │
  ▼
┌──────────────────────────────────────────────────────────┐
│  GCE e2-medium (arbor-prod)                              │
│  Container-Optimized OS │ Static IP: 34.87.60.241        │
│                                                          │
│  ┌─────────────────────────────────────────────┐         │
│  │ Caddy (arbor-caddy)         ports 80, 443    │         │
│  │ Auto HTTPS via Let's Encrypt                │         │
│  │ /api/* → backend:8000                       │         │
│  │ /*     → frontend:3000                      │         │
│  └────────┬──────────────────┬─────────────────┘         │
│           │                  │                           │
│  ┌────────▼────────┐  ┌─────▼──────────────┐            │
│  │ Next.js (3000)  │  │ FastAPI (8000)     │            │
│  │ arbor-frontend   │  │ arbor-backend       │            │
│  │ standalone mode  │  │ AsyncLocalRuntime  │            │
│  └─────────────────┘  └──┬─────────┬───────┘            │
│                          │         │                     │
│  ┌───────────────────────▼┐  ┌─────▼──────────────────┐ │
│  │ PostgreSQL 16 (5432)   │  │ Redis 7 (6379)         │ │
│  │ arbor-postgres           │  │ arbor-redis              │ │
│  │ pgvector extension     │  │ password-protected     │ │
│  │ Volume: arbor_pgdata    │  │ Volume: arbor_redis     │ │
│  └────────────────────────┘  └────────────────────────┘ │
└──────────────────────────────────────────────────────────┘
```

## GCP Infrastructure

| Resource     | ID / Value                                             |
| ------------ | ------------------------------------------------------ |
| GCE Instance | `arbor-prod`                                           |
| Machine Type | `e2-medium`                                            |
| OS           | Container-Optimized OS (cos-stable)                    |
| Zone         | `asia-southeast1-b`                                    |
| Static IP    | `34.87.60.241`                                         |
| Firewall     | `allow-http-https` (tcp:80,443)                        |
| GCP Project  | `terrene-care`                                         |
| GCP Account  | `jack@terrene.foundation`                              |
| DNS Record   | `arbor.terrene.foundation` → `34.87.60.241` (A record) |
| Region       | `asia-southeast1` (Singapore)                          |

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

| Variable                 | Description                                        |
| ------------------------ | -------------------------------------------------- |
| `DATABASE_URL`           | PostgreSQL connection string                       |
| `POSTGRES_USER`          | PostgreSQL username                                |
| `POSTGRES_PASSWORD`      | PostgreSQL password                                |
| `POSTGRES_DB`            | PostgreSQL database name                           |
| `REDIS_URL`              | Redis connection string                            |
| `REDIS_PASSWORD`         | Redis password                                     |
| `JWT_SECRET_KEY`         | JWT signing key                                    |
| `OPENAI_API_KEY`         | Server default OpenAI key (optional with BYOK)     |
| `LLM_KEY_ENCRYPTION_KEY` | Fernet key for encrypting user API keys (REQUIRED) |

### Optional

| Variable            | Default                            | Description          |
| ------------------- | ---------------------------------- | -------------------- |
| `ANTHROPIC_API_KEY` | —                                  | Anthropic API key    |
| `DEFAULT_LLM_MODEL` | `gpt-5-mini-2025-08-07`            | Default LLM model    |
| `OPENAI_PROD_MODEL` | `gpt-5-mini-2025-08-07`            | Production model     |
| `OLLAMA_BASE_URL`   | `http://localhost:11434`           | Ollama endpoint      |
| `OLLAMA_MODEL`      | —                                  | Ollama model name    |
| `LOG_LEVEL`         | `INFO`                             | Logging level        |
| `APP_ENV`           | `production`                       | Environment name     |
| `CORS_ORIGINS`      | `https://arbor.terrene.foundation` | Allowed CORS origins |

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
- Certificate CN: `arbor.terrene.foundation`
- Renewal: Automatic (Caddy handles renewal before expiry)
- HSTS: Enabled (`max-age=31536000; includeSubDomains`)
- Security headers: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`

## Deployment Runbook

### Prerequisites

- `gcloud` CLI authenticated with `jack@terrene.foundation`
- SSH access to `arbor-prod` instance via `gcloud compute ssh`

### Deploy New Version

```bash
# 1. Sync code to server (from local machine)
rsync -avz --exclude='.git' --exclude='node_modules' --exclude='.venv' \
  --exclude='__pycache__' --exclude='.next' --exclude='*.pyc' \
  -e "gcloud compute ssh arbor-prod --zone=asia-southeast1-b --project=terrene-care --" \
  . :/opt/arbor/

# 2. SSH into server
gcloud compute ssh arbor-prod --zone=asia-southeast1-b --project=terrene-care

# 3. On server: rebuild and restart
cd /opt/arbor/deploy
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build

# 4. Verify
docker ps  # all 5 containers healthy
curl -f https://arbor.terrene.foundation/health  # 200 OK
```

### Rollback

```bash
# SSH into server
gcloud compute ssh arbor-prod --zone=asia-southeast1-b --project=terrene-care

# Roll back to previous code
cd /opt/arbor
git checkout <previous-commit>

# Rebuild
cd deploy
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build

# Verify
curl -f https://arbor.terrene.foundation/health
```

### Server Setup (fresh instance)

```bash
# From local machine — provision a fresh Container-Optimized OS instance
gcloud compute ssh arbor-prod --zone=asia-southeast1-b --project=terrene-care \
  -- 'bash -s' < deploy/setup-server.sh
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
- Data volume: `arbor_pgdata` (persistent Docker volume)

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
- Consider: GCP Cloud Monitoring, Uptime Robot, or similar
- Alert on: container restarts, 5xx errors, disk usage > 80%

## Cost

- GCE e2-medium: ~$25/month (on-demand, asia-southeast1)
- Static IP: $0 (attached to running instance)
- DNS: Managed externally (terrene.foundation)
- Data transfer: Variable (~$0.12/GB outbound)
- **Estimated monthly: ~$30**

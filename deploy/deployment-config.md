# Central Deployment Configuration

## Decision Summary

| Decision       | Choice                                   | Rationale                                                    |
| -------------- | ---------------------------------------- | ------------------------------------------------------------ |
| Cloud provider | AWS (ap-southeast-1, Singapore)          | Available infrastructure                                     |
| Instance type  | t3.medium (2 vCPU, 4GB RAM)              | Cost-effective for current scale                             |
| Orchestration  | Docker Compose                           | Single-server deployment, simpler than K8s for current scale |
| Reverse proxy  | Caddy                                    | Zero-config automatic HTTPS with Let's Encrypt               |
| Domain         | central.kailash.ai                       | DNS A record to EC2 Elastic IP                               |
| Database       | PostgreSQL 16 + pgvector (containerized) | Vector search for KB embeddings                              |
| Cache          | Redis 7 (containerized)                  | Session management                                           |

## Architecture

```
Internet
  │
  ▼
┌──────────────────────────────────────────────────────────┐
│  EC2 t3.medium (central-prod)                            │
│  Ubuntu 22.04 LTS │ Elastic IP: TBD (after provision)   │
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

## AWS Infrastructure

| Resource       | ID / Value                               |
| -------------- | ---------------------------------------- |
| EC2 Instance   | `central-prod`                           |
| Instance Type  | `t3.medium` (2 vCPU, 4 GB RAM)           |
| AMI            | Ubuntu 22.04 LTS                         |
| Region         | `ap-southeast-1` (Singapore)             |
| Elastic IP     | TBD (after provisioning)                 |
| Security Group | `central-sg` (tcp:22,80,443)             |
| Key Pair       | `central-prod` (~/.ssh/central-prod.pem) |
| DNS Record     | `central.kailash.ai` → Elastic IP        |

### Security Group Rules

| Port | Protocol | Source    | Purpose                   |
| ---- | -------- | --------- | ------------------------- |
| 22   | TCP      | Your IP   | SSH (restrict to your IP) |
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
| `GOOGLE_API_KEY`         | Server default Google API key (optional with BYOK) |
| `LLM_KEY_ENCRYPTION_KEY` | Fernet key for encrypting user API keys (REQUIRED) |

### Optional

| Variable            | Default                      | Description          |
| ------------------- | ---------------------------- | -------------------- |
| `ANTHROPIC_API_KEY` | —                            | Anthropic API key    |
| `DEFAULT_LLM_MODEL` | `gemini-2.5-flash`           | Default LLM model    |
| `GEMINI_MODEL`      | `gemini-2.5-flash`           | Production model     |
| `OLLAMA_BASE_URL`   | `http://localhost:11434`     | Ollama endpoint      |
| `OLLAMA_MODEL`      | —                            | Ollama model name    |
| `LOG_LEVEL`         | `INFO`                       | Logging level        |
| `APP_ENV`           | `production`                 | Environment name     |
| `CORS_ORIGINS`      | `https://central.kailash.ai` | Allowed CORS origins |

## SSL/TLS

- Provider: Let's Encrypt (automated via Caddy)
- Certificate CN: `central.kailash.ai`
- Renewal: Automatic (Caddy handles renewal before expiry)
- HSTS: Enabled (`max-age=31536000; includeSubDomains`)
- Security headers: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`

## Deployment Runbook

### Prerequisites

- AWS CLI configured (`aws configure`)
- SSH key `~/.ssh/central-prod.pem` (or ssh-agent)
- `CENTRAL_INSTANCE_IP` exported in your shell

### Quick Deploy (from local machine)

```bash
export CENTRAL_INSTANCE_IP=<your-ec2-elastic-ip>
./deploy/ship.sh
```

### Manual Deploy

```bash
# 1. SSH into server
ssh -i ~/.ssh/central-prod.pem ubuntu@<elastic-ip>

# 2. Pull latest code
cd /opt/arbor
git pull origin main

# 3. Rebuild and restart
cd deploy
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build

# 4. Verify
docker ps  # all 5 containers healthy
curl -f https://central.kailash.ai/api/health  # 200 OK
```

### Rollback

```bash
ssh -i ~/.ssh/central-prod.pem ubuntu@<elastic-ip>
cd /opt/arbor
git checkout <previous-commit>
cd deploy
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build
curl -f https://central.kailash.ai/api/health
```

### Fresh EC2 Setup

```bash
# 1. Launch EC2 instance (Ubuntu 22.04, t3.medium, ap-southeast-1)
# 2. Allocate and associate Elastic IP
# 3. SSH in:
ssh -i ~/.ssh/central-prod.pem ubuntu@<elastic-ip>

# 4. Install Docker
sudo apt update && sudo apt install -y docker.io docker-compose-v2 git
sudo usermod -aG docker ubuntu
# Log out and back in for group to take effect

# 5. Clone repo
sudo mkdir -p /opt/arbor && sudo chown ubuntu:ubuntu /opt/arbor
git clone https://github.com/terrene-foundation/arbor.git /opt/arbor

# 6. Create production env file
cp /opt/arbor/deploy/.env.prod.example /opt/arbor/deploy/.env.prod
nano /opt/arbor/deploy/.env.prod  # Fill in real values

# 7. Start everything
cd /opt/arbor/deploy
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d

# 8. Verify
docker ps
curl -f https://central.kailash.ai/api/health
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

## Cost

- EC2 t3.medium: ~$30/month (on-demand, ap-southeast-1)
- Elastic IP: $0 (attached to running instance)
- DNS: Managed externally (kailash.ai)
- Data transfer: Variable (~$0.09/GB outbound)
- **Estimated monthly: ~$35**

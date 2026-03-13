# AITE Deployment Configuration

## Architecture

```
┌─────────────────────────────────────────────────┐
│                 Load Balancer (TLS)              │
├─────────────────┬───────────────────────────────┤
│   React Web     │      FastAPI Backend          │
│   (Next.js)     │   (AsyncLocalRuntime)         │
│   Port 3000     │      Port 8000                │
├─────────────────┴───────────────────────────────┤
│              PostgreSQL + pgvector               │
│                  Port 5432                       │
├─────────────────────────────────────────────────┤
│                    Redis                         │
│              Port 6379 (caching)                 │
└─────────────────────────────────────────────────┘
```

## Environment Configuration

### Development

- Docker Compose: `docker-compose.dev.yml`
- Hot reload enabled for both frontend and backend
- SQLite for local development (optional)
- No SSL required

### Staging

- Docker Compose with production images
- PostgreSQL + pgvector
- Redis for caching
- Self-signed SSL certificates
- Monitoring enabled

### Production

- Kubernetes or Docker Compose
- PostgreSQL + pgvector (managed service recommended)
- Redis (managed service recommended)
- Let's Encrypt SSL certificates
- Full monitoring and alerting
- Secrets via cloud provider's secrets manager

## Container Images

### Backend (Python)

- Base: `python:3.11-slim`
- Runtime: `AsyncLocalRuntime` (required for containers)
- Health check: `GET /health`
- Port: 8000

### Frontend (React)

- Base: `node:20-alpine`
- Build: `npm run build`
- Server: Next.js production server
- Port: 3000

## Health Check Endpoints

| Endpoint           | Method | Expected | Description               |
| ------------------ | ------ | -------- | ------------------------- |
| `/health`          | GET    | 200 OK   | Basic liveness            |
| `/health/ready`    | GET    | 200 OK   | Readiness (DB connected)  |
| `/health/detailed` | GET    | 200 OK   | Detailed component status |

## Environment Variables

### Required

| Variable            | Description           | Example                                 |
| ------------------- | --------------------- | --------------------------------------- |
| `DATABASE_URL`      | PostgreSQL connection | `postgresql://user:pass@host:5432/aite` |
| `REDIS_URL`         | Redis connection      | `redis://host:6379/0`                   |
| `JWT_SECRET`        | JWT signing key       | (generated)                             |
| `ANTHROPIC_API_KEY` | Claude API key        | `sk-ant-...`                            |

### Optional

| Variable             | Description          | Default                 |
| -------------------- | -------------------- | ----------------------- |
| `LOG_LEVEL`          | Logging level        | `INFO`                  |
| `CORS_ORIGINS`       | Allowed origins      | `http://localhost:3000` |
| `RATE_LIMIT_ENABLED` | Enable rate limiting | `true`                  |
| `CACHE_TTL_SECONDS`  | Default cache TTL    | `300`                   |

## Backup and Recovery

### Database Backups

- Daily automated backups via `pg_dump`
- Retain 30 days of daily backups
- Weekly backups retained for 90 days
- Test restore monthly

### Recovery Procedure

1. Stop application containers
2. Restore PostgreSQL from backup
3. Verify data integrity
4. Restart application containers
5. Run health checks
6. Verify advisory responses

## Monitoring

### Metrics

- Request rate and latency (per endpoint)
- Error rate (4xx, 5xx)
- Advisory response time (first token)
- Calculator computation time
- Cache hit rate
- Database query time

### Alerting

- Error rate > 5%: Page on-call
- Response time > 5s (P95): Warn
- Database connection failures: Page immediately
- Cache miss rate > 50%: Warn
- Disk usage > 80%: Warn

## Rollback Procedure

1. Identify the issue (monitoring alerts or user reports)
2. Determine last known good version
3. Deploy previous container images
4. Verify rollback via health checks
5. Investigate root cause
6. Document in incident log

## SSL/TLS Configuration

- TLS 1.2+ only
- Strong cipher suites
- HSTS enabled (max-age=31536000)
- Certificate renewal automated via Let's Encrypt

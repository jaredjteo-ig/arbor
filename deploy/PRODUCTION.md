# Production Deploy — GCP VM

This is the **slow, careful path**. Use this for actual production cutovers,
demos, and post-release smoke tests. For iteration, use `LOCAL.md` instead.

**Round-trip time:** ~3–5 minutes per cycle (backend rebuild dominates).

## Live deployment

- Host: GCP Compute Engine VM at `136.110.51.61`
- SSH user: `jaredteo`
- SSH key: `~/.ssh/google_compute_engine`
- Repo path on VM: `/opt/arbor`
- Compose file: `deploy/docker-compose.prod.yml`
- Env file: `deploy/.env.prod` (NOT the default `.env` — must use `--env-file`)
- Reverse proxy: Caddy on `:80` and `:443`
- Domain: served via VM IP at the moment

## Containers

| Container        | Purpose             | Port (in network) |
| ---------------- | ------------------- | ----------------- |
| `arbor-caddy`    | Reverse proxy + TLS | host `:80/:443`   |
| `arbor-frontend` | Next.js (built)     | `3000`            |
| `arbor-backend`  | FastAPI/Nexus       | `8000`            |
| `arbor-postgres` | pgvector/pg16       | `5432`            |
| `arbor-redis`    | Redis 7             | `6379`            |

DB volume: `arbor_pgdata` (named docker volume, persists across rebuilds).
Redis volume: `arbor_redis`.

## Standard deploy sequence

Run these from your laptop. **Always backup the DB before pulling.**

```bash
# 0. Pre-flight: confirm push has landed
git log --oneline -3   # confirm what you're about to deploy

# 1. SSH and backup the DB (5 sec)
ssh -i ~/.ssh/google_compute_engine jaredteo@136.110.51.61 \
  'cd /opt/arbor && docker exec arbor-postgres pg_dump -U arbor arbor > /tmp/arbor-pre-$(date +%Y%m%d-%H%M).sql && ls -lh /tmp/arbor-pre-*.sql | tail -1'

# 2. Quick role pre-flight (only matters if RBAC changed)
ssh -i ~/.ssh/google_compute_engine jaredteo@136.110.51.61 \
  'docker exec arbor-postgres psql -U arbor -d arbor -c "SELECT id, email, role FROM users WHERE role IN (\"consultant\");"'
# If any rows: UPDATE users SET role='hr_manager' WHERE role='consultant';

# 3. Pull, rebuild, restart in one command
ssh -i ~/.ssh/google_compute_engine jaredteo@136.110.51.61 'cd /opt/arbor && \
  git pull origin main && \
  docker compose --env-file deploy/.env.prod -f deploy/docker-compose.prod.yml up -d --build backend frontend'

# Backend rebuild takes ~3 min. Frontend ~30 sec.

# 4. Run migration if there's one (idempotent)
ssh -i ~/.ssh/google_compute_engine jaredteo@136.110.51.61 'cd /opt/arbor && \
  docker cp scripts/migrate_recruitment_fields.py arbor-backend:/tmp/migrate.py && \
  docker exec arbor-backend python /tmp/migrate.py'

# 5. Smoke test
ssh -i ~/.ssh/google_compute_engine jaredteo@136.110.51.61 '
  echo "Public site: $(curl -s -o /dev/null -w "%{http_code}" http://136.110.51.61/)"
  echo "Public careers: $(curl -s -o /dev/null -w "%{http_code}" http://136.110.51.61/careers/central-solutions-pte-ltd)"
  docker ps --format "table {{.Names}}\t{{.Status}}"'
```

## Critical gotchas

### 1. Use `--env-file` flag — NEVER just `up`

```bash
# RIGHT
docker compose --env-file deploy/.env.prod -f deploy/docker-compose.prod.yml up -d ...

# WRONG (env vars come up empty, redis fails with `requirepass` error)
docker compose -f deploy/docker-compose.prod.yml up -d ...
```

The compose file uses `${REDIS_PASSWORD}`, `${DATABASE_URL}` etc. as direct
substitutions, not `environment:` injections. Without `--env-file`, those
substitutions resolve to empty strings.

### 2. Migration script lives outside the backend image

`scripts/migrate_recruitment_fields.py` is in the repo at `/opt/arbor/scripts/`
but the backend Dockerfile only `COPY src/`. You MUST `docker cp` it into the
container before running:

```bash
docker cp scripts/migrate_recruitment_fields.py arbor-backend:/tmp/migrate.py
docker exec arbor-backend python /tmp/migrate.py
```

The script is idempotent — safe to re-run.

### 3. Single-VM, single-worker — no replicas

The backend runs as ONE container. The in-memory rate limiter works on this
single-VM deployment. If you ever add replicas / horizontal scale, the
in-memory limiter becomes a no-op across workers — you'd need T-RX07 (Redis
rate limiter).

### 4. No CI auto-deploy

`git push origin main` does NOT trigger a deploy. There's no `.github/workflows/`
in this repo. The `deploy/ship.sh` script is for a different deployment
(central.kailash.ai on AWS) and won't work for Arbor.

## Rollback

```bash
ssh -i ~/.ssh/google_compute_engine jaredteo@136.110.51.61 'cd /opt/arbor && \
  git reset --hard <last-known-good-sha> && \
  docker compose --env-file deploy/.env.prod -f deploy/docker-compose.prod.yml up -d --build backend frontend'

# If the migration was destructive too:
ssh -i ~/.ssh/google_compute_engine jaredteo@136.110.51.61 \
  'docker exec -i arbor-postgres psql -U arbor -d arbor < /tmp/arbor-pre-<TIMESTAMP>.sql'
```

## Common smoke tests

```bash
# From laptop
curl -fsS http://136.110.51.61/                                                        # public site → 200
curl -s -o /dev/null -w "%{http_code}\n" http://136.110.51.61/api/clients              # → 404 (retired)
curl -s -o /dev/null -w "%{http_code}\n" http://136.110.51.61/api/company              # → 401 (auth-gated)
curl -s -o /dev/null -w "%{http_code}\n" http://136.110.51.61/careers/central-solutions-pte-ltd  # → 200

# On the VM
docker logs arbor-backend --tail 100
docker logs arbor-frontend --tail 100
docker exec arbor-postgres psql -U arbor -d arbor -c "SELECT id, name, slug FROM companies;"
```

## When things go wrong

| Symptom                                        | Likely cause                                 | Fix                                                                             |
| ---------------------------------------------- | -------------------------------------------- | ------------------------------------------------------------------------------- |
| Redis won't start, "wrong number of arguments" | Forgot `--env-file` flag                     | Re-run with `--env-file deploy/.env.prod`                                       |
| 500 on company create                          | Migration didn't run on prod                 | `docker cp` + `docker exec` migration                                           |
| 403 everywhere for one user                    | DB has stale role string                     | `UPDATE users SET role='hr_manager' WHERE role='<old_role>'`                    |
| Frontend stale after deploy                    | Browser cache                                | Hard refresh / clear localStorage                                               |
| Backend won't start, schema mismatch           | Code requires DB column that's not there yet | Run migration; if still broken, `git reset --hard` to last-good and rollback DB |
| Stuck "deploying" build                        | Disk full, OOM                               | `docker system prune -af`, check `df -h`                                        |

## DB backup retention

Backups go to `/tmp/arbor-pre-<TIMESTAMP>.sql` on the VM. **They evaporate on
VM reboot** (since `/tmp` is tmpfs). If you need a durable backup:

```bash
# From laptop, after a backup:
scp -i ~/.ssh/google_compute_engine \
  jaredteo@136.110.51.61:/tmp/arbor-pre-*.sql \
  ~/Documents/arbor-backups/
```

## See also

- `LOCAL.md` — fast local iteration loop (use this for development)
- `deploy/docker-compose.prod.yml` — the prod compose definition
- `deploy/Dockerfile.backend` / `deploy/Dockerfile.frontend` — image builds
- `deploy/Caddyfile` — reverse proxy config

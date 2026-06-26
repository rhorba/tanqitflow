# TanqitFlow — Deployment Guide

**Version**: 1.0  
**Target**: Ubuntu 22.04 VPS — 4 vCPU / 8 GB RAM / 100 GB SSD  
**Stack**: Docker Compose (prod) · Nginx · PostgreSQL/TimescaleDB · Celery · MinIO

---

## Prerequisites

| Tool | Version |
|------|---------|
| Docker | ≥ 24.0 |
| Docker Compose | ≥ 2.20 (plugin, not standalone) |
| Git | ≥ 2.40 |
| curl, openssl, jq | any recent |

```bash
# Install Docker on Ubuntu 22.04
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker
```

---

## 1. Provision the VPS

Minimum specs for a production pilot:

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| CPU | 4 vCPU | 8 vCPU |
| RAM | 8 GB | 16 GB |
| Disk | 100 GB SSD | 200 GB SSD |
| OS | Ubuntu 22.04 LTS | Ubuntu 22.04 LTS |
| Open ports | 22 (SSH), 80 (HTTP), 443 (HTTPS) | same |

---

## 2. Add GitHub Secrets

In your repository: **Settings → Secrets and variables → Actions → New repository secret**

| Secret | Value |
|--------|-------|
| `VPS_HOST` | Your VPS IP or domain (e.g. `tanqitflow.onee.ma`) |
| `VPS_USER` | SSH user (e.g. `ubuntu`) |
| `VPS_SSH_KEY` | Private key for SSH access (paste the full PEM contents) |
| `VPS_DEPLOY_PATH` | Absolute path on VPS (e.g. `/opt/tanqitflow`) |

The `GITHUB_TOKEN` is provided automatically by Actions — no extra secret needed for GHCR push/pull.

---

## 3. First-time server setup

```bash
# On the VPS as root or sudo user
mkdir -p /opt/tanqitflow
cd /opt/tanqitflow

# Clone the repository
git clone https://github.com/rhorba/tanqitflow.git .
```

### Create the `.env` file

```bash
cp .env.example .env
nano .env   # fill in all values
```

**Required secrets** (startup fails without these):

```bash
POSTGRES_PASSWORD=<generate: openssl rand -hex 32>
JWT_SECRET=<generate: python -c "import secrets; print(secrets.token_hex(32))">
PII_ENCRYPTION_KEY=<generate: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())">
MINIO_ROOT_PASSWORD=<generate: openssl rand -hex 24>
REDIS_PASSWORD=<generate: openssl rand -hex 24>
```

**All other required fields**:

```bash
POSTGRES_USER=tanqit
POSTGRES_DB=tanqitflow
MINIO_ROOT_USER=tanqitminio
MINIO_BUCKET=tanqitflow-uploads
ENVIRONMENT=production
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your@email.com
SMTP_PASSWORD=your-app-password
```

---

## 4. TLS certificate (Let's Encrypt)

```bash
# Install Certbot
sudo apt install certbot -y

# Obtain certificate (stop nginx first if running)
sudo certbot certonly --standalone -d tanqitflow.yourdomain.ma

# Certificates are saved to:
#   /etc/letsencrypt/live/tanqitflow.yourdomain.ma/fullchain.pem
#   /etc/letsencrypt/live/tanqitflow.yourdomain.ma/privkey.pem

# Copy to the nginx/certs directory
mkdir -p /opt/tanqitflow/nginx/certs
cp /etc/letsencrypt/live/tanqitflow.yourdomain.ma/fullchain.pem /opt/tanqitflow/nginx/certs/
cp /etc/letsencrypt/live/tanqitflow.yourdomain.ma/privkey.pem /opt/tanqitflow/nginx/certs/

# Auto-renew hook (add to /etc/letsencrypt/renewal-hooks/deploy/)
cat > /etc/letsencrypt/renewal-hooks/deploy/tanqitflow.sh <<'EOF'
#!/bin/bash
cp /etc/letsencrypt/live/tanqitflow.yourdomain.ma/fullchain.pem /opt/tanqitflow/nginx/certs/
cp /etc/letsencrypt/live/tanqitflow.yourdomain.ma/privkey.pem /opt/tanqitflow/nginx/certs/
docker compose -f /opt/tanqitflow/docker-compose.prod.yml restart nginx
EOF
chmod +x /etc/letsencrypt/renewal-hooks/deploy/tanqitflow.sh
```

---

## 5. Initial deployment

```bash
cd /opt/tanqitflow

# Pull images (CI/CD pushes these after a successful pipeline)
echo "$GITHUB_TOKEN" | docker login ghcr.io -u rhorba --password-stdin
docker compose -f docker-compose.prod.yml pull

# Start all services
docker compose -f docker-compose.prod.yml up -d

# Watch logs during first startup
docker compose -f docker-compose.prod.yml logs -f
```

Services start order: `db` → `redis` + `minio` → `api` → `worker` + `beat` → `frontend` → `nginx`

---

## 6. Run database migrations

```bash
docker compose -f docker-compose.prod.yml exec api \
  alembic upgrade head
```

---

## 7. Create the pilot tenant + admin user

```bash
# Enter the API container
docker compose -f docker-compose.prod.yml exec api bash

# Create the ONEE Casablanca tenant
curl -X POST http://localhost:8000/api/v1/tenants \
  -H "Content-Type: application/json" \
  -d '{"name": "ONEE Casablanca", "slug": "onee-casa"}'

# Create the admin user (use the tenant_id from the response above)
curl -X POST http://localhost:8000/api/v1/users \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@onee.ma",
    "password": "SecurePass123!",
    "role": "utility_admin",
    "tenant_id": "<tenant_id_from_above>"
  }'
```

---

## 8. Smoke test checklist

After deployment, verify the following:

```bash
BASE=https://tanqitflow.yourdomain.ma

# 1. Health check
curl -s $BASE/api/v1/health | jq
# Expected: {"status":"ok","db":"ok","redis":"ok","minio":"ok"}

# 2. Login
TOKEN=$(curl -s -X POST $BASE/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@onee.ma","password":"SecurePass123!"}' \
  | jq -r '.access_token')
echo "Token: $TOKEN"

# 3. Dashboard KPIs
curl -s -H "Authorization: Bearer $TOKEN" $BASE/api/v1/balance/summary | jq

# 4. DMA list
curl -s -H "Authorization: Bearer $TOKEN" "$BASE/api/v1/dmas?page=1" | jq '.meta'

# 5. Language switch (frontend loads at root)
curl -s -o /dev/null -w "%{http_code}" $BASE/
# Expected: 200
```

Manual checklist:

- [ ] Login as `utility_admin` → dashboard loads
- [ ] Upload sample `DMA_INFLOW` CSV → job completes, rows visible
- [ ] Water balance computed → NRW% visible in dashboard  
- [ ] Map loads with at least 1 DMA polygon
- [ ] Language switch FR ↔ AR works
- [ ] `/api/v1/health` returns `{"status":"ok",...}`
- [ ] `/docs` returns 401 without JWT, 200 with utility_admin JWT

---

## 9. Subsequent deployments (CI/CD)

After the initial setup, all deployments are automated via **GitHub Actions**:

1. Push to `main` branch
2. Pipeline runs: Lint → Test → Semgrep SAST → Build+Push → ZAP DAST → SSH Deploy
3. VPS automatically pulls new images and restarts containers
4. GitHub Deployments tab shows status

**Manual redeploy** if needed:

```bash
cd /opt/tanqitflow
git pull origin main
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d --remove-orphans
docker system prune -f
```

---

## 10. Monitoring & Logs

```bash
# Live logs for all services
docker compose -f docker-compose.prod.yml logs -f

# API logs only
docker compose -f docker-compose.prod.yml logs -f api

# Celery worker logs
docker compose -f docker-compose.prod.yml logs -f worker

# Check resource usage
docker stats

# Check service health
docker compose -f docker-compose.prod.yml ps
```

---

## 11. Backup strategy

```bash
# Database backup
docker compose -f docker-compose.prod.yml exec db \
  pg_dump -U tanqit tanqitflow | gzip > /backups/db_$(date +%Y%m%d).sql.gz

# MinIO data is in the minio_data volume
# Optionally sync to S3/Backblaze B2 with rclone
```

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| `db` container fails to start | Missing `POSTGRES_PASSWORD` | Check `.env` |
| `api` starts then crashes | Missing `JWT_SECRET` or `PII_ENCRYPTION_KEY` | Check `.env` |
| Nginx 502 | API not ready yet | Wait 40s for healthcheck → `docker compose ps` |
| SSL cert errors | Certs not in `nginx/certs/` | Re-run certbot copy step |
| MinIO unreachable | `MINIO_ROOT_PASSWORD` mismatch | Check `.env` vs volume state |

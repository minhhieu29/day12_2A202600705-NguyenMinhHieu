# Deployment Information

**Student:** Nguyen Minh Hieu (2A202600705)  
**Date:** 12/06/2026

---

## Public URL

```
https://day122a202600705-nguyenminhhieu-production.up.railway.app
```

## Platform

**Railway** — deploy từ GitHub repo, builder Dockerfile, Redis add-on.

---

## Environment Variables Set

| Variable | Mô tả |
|----------|-------|
| `PORT` | Railway tự inject |
| `REDIS_URL` | `${{Redis.REDIS_URL}}` |
| `AGENT_API_KEY` | API key bảo mật (set trên Railway Variables) |
| `ENVIRONMENT` | `production` |
| `RATE_LIMIT_PER_MINUTE` | `10` |
| `MONTHLY_BUDGET_USD` | `10.0` |

---

## Test Commands (Production)

### Health Check

```powershell
curl.exe https://day122a202600705-nguyenminhhieu-production.up.railway.app/health
```

**Kết quả:** `{"status":"ok","version":"1.0.0","environment":"production",...}` — HTTP 200

### Readiness Check

```powershell
curl.exe https://day122a202600705-nguyenminhhieu-production.up.railway.app/ready
```

**Kết quả:** `{"ready":true,"instance_id":"instance-f13cd2"}`

### Authentication Required (401)

```powershell
curl.exe -X POST https://day122a202600705-nguyenminhhieu-production.up.railway.app/ask `
  -H "Content-Type: application/json" -d "@body.json"
```

**Kết quả:** HTTP 401 — `Invalid or missing API key`

### API Test (with authentication)

```powershell
curl.exe -X POST https://day122a202600705-nguyenminhhieu-production.up.railway.app/ask `
  -H "X-API-Key: YOUR_KEY" -H "Content-Type: application/json" -d "@body.json"
```

**Kết quả:** HTTP 200 — trả về `answer` từ mock LLM

### Rate Limiting (429 after 10 requests)

```powershell
1..12 | ForEach-Object {
  curl.exe -s -w " Request $_`: HTTP %{http_code}`n" -X POST `
    https://day122a202600705-nguyenminhhieu-production.up.railway.app/ask `
    -H "X-API-Key: YOUR_KEY" -H "Content-Type: application/json" -d "@body.json"
}
```

**Kết quả:** Request 1–10 → HTTP 200, Request 11–12 → HTTP 429 `Rate limit exceeded: 10 req/min`

---

## Local Deployment (Optional)

```bash
cd 06-lab-complete
docker compose up --build -d
curl http://localhost:8080/health
```

---

## Architecture

```
Client → Railway Proxy → FastAPI Agent (:PORT) → Redis
```

- **Stateless:** Conversation history, rate limits, budget trong Redis
- **Multi-stage Docker:** Image ~307 MB
- **Health:** `/health` (liveness), `/ready` (readiness + Redis ping)

---

## Screenshots

| File | Mô tả |
|------|-------|
| [screenshots/dashboard.png](screenshots/dashboard.png) | Railway dashboard — Redis + Agent Online |
| [screenshots/running.png](screenshots/running.png) | Trang chủ app trên browser (GET /) |
| [screenshots/test.png](screenshots/test.png) | Test health, ready, auth 401/200 (PowerShell) |
| [screenshots/rate-limit.png](screenshots/rate-limit.png) | Test rate limit — 10×200, 11–12×429 |

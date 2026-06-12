# Deployment Information

**Student:** Nguyen Minh Hieu (2A202600705)

---

## Local Deployment (Verified)

Stack chạy local với Docker Compose:

```bash
cd 06-lab-complete
docker compose up --build -d
```

### Public URL (Local)

```
http://localhost:8080
```

## Platform (Cloud)

**Recommended:** Railway hoặc Render

### Deploy Railway

```bash
cd 06-lab-complete
npm i -g @railway/cli
railway login
railway init
railway variables set AGENT_API_KEY=your-secret-key
railway variables set REDIS_URL=redis://...   # Railway Redis add-on
railway variables set ENVIRONMENT=production
railway variables set RATE_LIMIT_PER_MINUTE=10
railway variables set MONTHLY_BUDGET_USD=10.0
railway up
railway domain
```

> **Lưu ý:** Sau khi deploy, cập nhật Public URL bên dưới.

### Public URL (Cloud)

```
https://YOUR-APP.railway.app
```

*(Thay bằng URL thật sau khi deploy)*

---

## Test Commands

### Health Check

```bash
curl http://localhost:8080/health
# Expected: {"status":"ok",...}
```

### Readiness Check

```bash
curl http://localhost:8080/ready
# Expected: {"ready":true,"instance_id":"..."}
```

### Authentication Required (401)

```bash
curl -X POST http://localhost:8080/ask \
  -H "Content-Type: application/json" \
  -d '{"user_id":"test","question":"Hello"}'
# Expected: 401 Unauthorized
```

### API Test (with authentication)

```bash
curl -X POST http://localhost:8080/ask \
  -H "X-API-Key: dev-key-change-me" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test", "question": "Hello"}'
# Expected: 200 with answer JSON
```

### Rate Limiting (429 after 10 requests)

```powershell
1..15 | ForEach-Object {
  curl.exe -s -X POST http://localhost:8080/ask `
    -H "X-API-Key: dev-key-change-me" `
    -H "Content-Type: application/json" `
    -d '{"user_id":"test","question":"test"}'
}
# Request 11+ should return 429
```

---

## Environment Variables Set

| Variable | Value (example) |
|----------|-----------------|
| PORT | 8000 |
| REDIS_URL | redis://redis:6379/0 |
| AGENT_API_KEY | dev-key-change-me |
| LOG_LEVEL | INFO |
| RATE_LIMIT_PER_MINUTE | 10 |
| MONTHLY_BUDGET_USD | 10.0 |
| ENVIRONMENT | staging |

---

## Architecture

```
Client → Nginx (:80) → Agent (FastAPI :8000) → Redis
```

- **Stateless:** Conversation history, rate limits, budget trong Redis
- **Multi-stage Docker:** Image < 500 MB
- **Health:** `/health` (liveness), `/ready` (readiness + Redis ping)

---

## Screenshots

Thêm screenshots sau khi deploy cloud vào thư mục `screenshots/`:

- `screenshots/dashboard.png` — Railway/Render dashboard
- `screenshots/running.png` — Service running
- `screenshots/test.png` — curl test results

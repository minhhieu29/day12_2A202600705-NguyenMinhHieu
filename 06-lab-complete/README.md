# Lab 12 — Production AI Agent

**Student:** Nguyen Minh Hieu (2A202600705)

Production-ready AI agent kết hợp tất cả concepts Day 12.

## Features

- REST API `/ask` với conversation history (Redis)
- API key authentication (`X-API-Key`)
- Rate limiting: 10 req/min per user
- Cost guard: $10/month per user
- Health + readiness probes
- Graceful shutdown (SIGTERM)
- Multi-stage Docker (< 500 MB)
- Nginx load balancer

## Quick Start

```bash
# 1. Chạy stack
docker compose up --build -d

# 2. Health check
curl http://localhost:8080/health

# 3. Ask (cần API key)
curl -X POST http://localhost:8080/ask \
  -H "X-API-Key: dev-key-change-me" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "user1", "question": "What is deployment?"}'
```

## Scale với Load Balancer

```bash
docker compose up --build --scale agent=3 -d
```

## Validation

```bash
python check_production_ready.py
# Expected: 20/20 checks passed
```

## Deploy Cloud

Xem [DEPLOYMENT.md](../DEPLOYMENT.md) ở root repo.

```bash
railway login
railway init
railway variables set AGENT_API_KEY=your-secret
railway variables set REDIS_URL=redis://...
railway up
```

## Project Structure

```
app/
├── main.py          # FastAPI entry point
├── config.py        # 12-factor config
├── auth.py          # API key verification
├── rate_limiter.py  # Redis sliding window
├── cost_guard.py    # Monthly budget
└── redis_client.py  # Redis connection
utils/
└── mock_llm.py      # Mock LLM (no API key needed)
```

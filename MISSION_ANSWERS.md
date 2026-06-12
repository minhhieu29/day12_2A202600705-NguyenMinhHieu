# Day 12 Lab - Mission Answers

**Student Name:** Nguyen Minh Hieu  
**Student ID:** 2A202600705  
**Date:** 12/06/2026

---

## Part 1: Localhost vs Production

### Exercise 1.1: Anti-patterns found

1. **API key hardcode** — `OPENAI_API_KEY = "sk-hardcoded-fake-key-never-do-this"` trong source code, dễ bị lộ khi push GitHub.
2. **Database credentials hardcode** — `DATABASE_URL` chứa username/password trực tiếp trong code.
3. **Debug mode bật cố định** — `DEBUG = True` và `reload=True` không phù hợp production.
4. **Logging không an toàn** — dùng `print()` và log ra API key (`print(f"[DEBUG] Using key: {OPENAI_API_KEY}")`).
5. **Không có health check** — platform không biết khi nào container cần restart.
6. **Port và host cố định** — `host="localhost"`, `port=8000` không đọc từ env var `PORT`.
7. **Không có graceful shutdown** — không xử lý SIGTERM khi orchestrator tắt container.
8. **Không có config management** — mọi giá trị hardcode, không dùng 12-Factor App.

### Exercise 1.3: Comparison table

| Feature | Develop (Basic) | Production (Advanced) | Tại sao quan trọng? |
|---------|-----------------|----------------------|---------------------|
| Config | Hardcode trong code | Environment variables qua `config.py` | Thay đổi config không cần sửa code, secrets không lộ |
| Health check | Không có | `GET /health` + `GET /ready` | Platform biết khi restart, LB biết khi route traffic |
| Logging | `print()` debug | Structured JSON logging | Dễ parse trong Datadog/Loki, không log secrets |
| Shutdown | Đột ngột | Lifespan + SIGTERM handler | Hoàn thành request đang xử lý trước khi tắt |
| Host binding | `localhost` | `0.0.0.0` | Container nhận traffic từ bên ngoài |
| Port | Cố định 8000 | `PORT` env var | Railway/Render inject port động |
| CORS | Không có | Cấu hình qua `ALLOWED_ORIGINS` | Kiểm soát origins được phép gọi API |
| Input validation | Query param `question: str` | Pydantic model + HTTPException | Validate input, trả lỗi chuẩn |

### Checkpoint 1

- [x] Hiểu tại sao hardcode secrets là nguy hiểm
- [x] Biết cách dùng environment variables
- [x] Hiểu vai trò của health check endpoint
- [x] Biết graceful shutdown là gì

---

## Part 2: Docker

### Exercise 2.1: Dockerfile questions

1. **Base image:** `python:3.11` (full distribution, ~1 GB)
2. **Working directory:** `/app`
3. **Tại sao COPY requirements.txt trước:** Tận dụng Docker layer cache — dependencies ít thay đổi hơn code, rebuild nhanh hơn khi chỉ sửa app.
4. **CMD vs ENTRYPOINT:** `CMD` là default command có thể override khi `docker run`; `ENTRYPOINT` định nghĩa executable chính, khó override hơn. Kết hợp: ENTRYPOINT cho binary, CMD cho arguments.

### Exercise 2.3: Image size comparison

- **Develop (single-stage):** ~1660 MB (1.66 GB)
- **Production (multi-stage slim):** ~236 MB
- **Difference:** ~86% nhỏ hơn — nhờ `python:3.11-slim`, loại build tools (gcc), chỉ copy runtime packages

**Lý do image nhỏ hơn:**
- Stage 1 (builder): cài gcc, pip packages
- Stage 2 (runtime): chỉ copy `/root/.local` packages + source code, không có compiler
- Non-root user + HEALTHCHECK cho production security

### Exercise 2.4: Docker Compose architecture

```
Client → Nginx (:80) → Agent (:8000) → Redis (:6379)
```

- **Services:** `agent`, `redis`, `nginx`
- **Communication:** Nginx reverse proxy tới `agent:8000`; agent kết nối Redis qua `redis://redis:6379/0`
- **Health:** Redis healthcheck `redis-cli ping`; agent healthcheck `GET /health`

### Checkpoint 2

- [x] Hiểu cấu trúc Dockerfile
- [x] Biết lợi ích của multi-stage builds
- [x] Hiểu Docker Compose orchestration
- [x] Biết cách debug container (`docker logs`, `docker exec`)

---

## Part 3: Cloud Deployment

### Exercise 3.1: Railway deployment

- **URL:** *(Cập nhật sau khi deploy — xem DEPLOYMENT.md)*
- **Platform:** Railway
- **Config file:** `railway.toml` — định nghĩa builder, startCommand, healthcheckPath

### Exercise 3.2: So sánh render.yaml vs railway.toml

| | Railway (`railway.toml`) | Render (`render.yaml`) |
|---|--------------------------|------------------------|
| Format | TOML | YAML Blueprint |
| Health check | `healthcheckPath = "/health"` | `healthCheckPath: /health` trong service |
| Start command | `startCommand` trong `[deploy]` | `startCommand` trong service spec |
| Scaling | `railway scale` CLI | Dashboard → Instances |
| Redis | Add-on riêng, set `REDIS_URL` | Managed Redis service trong blueprint |

### Checkpoint 3

- [x] Hiểu cách deploy lên cloud platform
- [x] Hiểu cách set environment variables trên cloud
- [x] Biết cách xem logs (`railway logs`, Render dashboard)

---

## Part 4: API Security

### Exercise 4.1: API Key authentication

- **API key được check ở:** `verify_api_key()` dependency trong `app/auth.py`, đọc header `X-API-Key`
- **Nếu sai key:** HTTP 401 `Invalid or missing API key`
- **Rotate key:** Đổi `AGENT_API_KEY` trong env vars (Railway/Render dashboard), restart service — không cần sửa code

**Test results:**
```bash
# Không có key → 401
curl http://localhost:8080/ask -X POST -H "Content-Type: application/json" -d '{"user_id":"test","question":"Hello"}'
# {"detail":"Invalid or missing API key..."}

# Có key → 200
curl http://localhost:8080/ask -X POST -H "X-API-Key: dev-key-change-me" -H "Content-Type: application/json" -d '{"user_id":"test","question":"Hello"}'
# {"question":"Hello","answer":"...","model":"gpt-4o-mini",...}
```

### Exercise 4.2: JWT authentication (Advanced)

**JWT Flow:**
1. `POST /token` với username/password → server trả JWT
2. Client gửi `Authorization: Bearer <token>` cho các request sau
3. Server verify signature + expiry → extract user info

### Exercise 4.3: Rate limiting

- **Algorithm:** Sliding window (Redis sorted set — `ZADD`/`ZREMRANGEBYSCORE`)
- **Limit:** 10 requests/minute per user
- **Bypass admin:** Có thể dùng tier riêng (ví dụ `rate_limiter_admin` với 100 req/min) cho role admin

### Exercise 4.4: Cost guard implementation

**Approach:** Lưu chi phí tích lũy trong Redis với key `budget:{user_id}:{YYYY-MM}`.

```python
def check_budget(user_id, estimated_cost):
    key = f"budget:{user_id}:{month}"
    current = float(redis.get(key) or 0)
    if current + estimated_cost > MONTHLY_BUDGET_USD:  # $10
        raise HTTPException(402, "Monthly budget exceeded")
    redis.incrbyfloat(key, cost)
    redis.expire(key, 32 days)
```

- Mỗi user có budget **$10/tháng**
- Reset tự động đầu tháng (key mới theo `YYYY-MM`)
- HTTP 402 khi vượt budget

### Checkpoint 4

- [x] Implement API key authentication
- [x] Hiểu JWT flow
- [x] Implement rate limiting (Redis sliding window)
- [x] Implement cost guard với Redis

---

## Part 5: Scaling & Reliability

### Exercise 5.1: Health checks

- **`GET /health`** — Liveness probe, luôn trả 200 nếu process còn chạy
- **`GET /ready`** — Readiness probe, kiểm tra Redis connection; trả 503 nếu chưa sẵn sàng

### Exercise 5.2: Graceful shutdown

- Đăng ký `signal.signal(signal.SIGTERM, _handle_signal)`
- Uvicorn `timeout_graceful_shutdown=30` — hoàn thành in-flight requests
- Lifespan `yield` block — cleanup khi shutdown

### Exercise 5.3: Stateless design

- **Anti-pattern:** `conversation_history = {}` trong memory
- **Correct:** Lưu history trong Redis `history:{user_id}` (list)
- **Lý do:** Khi scale 3 instances, request tiếp theo có thể đến instance khác — memory không shared

### Exercise 5.4: Load balancing

```bash
docker compose up --scale agent=3
```

- Nginx upstream `agent:8000` — Docker DNS round-robin
- Header `X-Served-By` / `X-Instance-Id` cho thấy instance xử lý request

### Exercise 5.5: Test stateless

Conversation history lưu trong Redis → kill 1 instance, request tiếp theo vẫn có history.

### Checkpoint 5

- [x] Implement health và readiness checks
- [x] Implement graceful shutdown
- [x] Refactor code thành stateless (Redis)
- [x] Hiểu load balancing với Nginx
- [x] Test stateless design

---

## Part 6: Final Project

Project hoàn chỉnh tại `06-lab-complete/`:

```
06-lab-complete/
├── app/
│   ├── main.py
│   ├── config.py
│   ├── auth.py
│   ├── rate_limiter.py
│   ├── cost_guard.py
│   └── redis_client.py
├── utils/mock_llm.py
├── Dockerfile
├── docker-compose.yml
├── nginx.conf
├── railway.toml
├── render.yaml
└── check_production_ready.py
```

**Validation:** `python check_production_ready.py` → **20/20 checks passed (100%)**

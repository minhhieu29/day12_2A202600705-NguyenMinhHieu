"""
Production AI Agent — Day 12 Final Project

Features:
  - Config từ environment (12-factor)
  - Structured JSON logging
  - API Key authentication
  - Redis rate limiting + cost guard
  - Conversation history (stateless, Redis)
  - Health + readiness probes
  - Graceful shutdown
"""
import json
import logging
import signal
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.auth import verify_api_key
from app.config import settings
from app.cost_guard import check_budget, estimate_cost, record_cost
from app.rate_limiter import check_rate_limit
from app.redis_client import get_redis, ping_redis
from utils.mock_llm import ask as llm_ask

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format='{"ts":"%(asctime)s","lvl":"%(levelname)s","msg":"%(message)s"}',
)
logger = logging.getLogger(__name__)

START_TIME = time.time()
_is_ready = False
_request_count = 0
_error_count = 0
INSTANCE_ID = f"instance-{uuid.uuid4().hex[:6]}"


def _get_history(user_id: str) -> list[dict]:
    r = get_redis()
    key = f"history:{user_id}"
    items = r.lrange(key, 0, -1)
    return [json.loads(item) for item in items]


def _append_history(user_id: str, role: str, content: str) -> None:
    r = get_redis()
    key = f"history:{user_id}"
    entry = json.dumps({
        "role": role,
        "content": content,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    r.rpush(key, entry)
    r.ltrim(key, -20, -1)
    r.expire(key, 7 * 24 * 3600)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _is_ready
    logger.info(json.dumps({
        "event": "startup",
        "instance": INSTANCE_ID,
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
    }))
    if ping_redis():
        _is_ready = True
        logger.info(json.dumps({"event": "ready", "instance": INSTANCE_ID}))
    else:
        logger.error(json.dumps({
            "event": "redis_unavailable",
            "instance": INSTANCE_ID,
            "hint": "Set REDIS_URL environment variable",
        }))

    yield

    _is_ready = False
    logger.info(json.dumps({"event": "shutdown", "instance": INSTANCE_ID}))


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/docs" if settings.environment != "production" else None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key"],
)


@app.middleware("http")
async def request_middleware(request: Request, call_next):
    global _request_count, _error_count
    start = time.time()
    _request_count += 1
    try:
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Instance-Id"] = INSTANCE_ID
        if "server" in response.headers:
            del response.headers["server"]
        duration = round((time.time() - start) * 1000, 1)
        logger.info(json.dumps({
            "event": "request",
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "ms": duration,
            "instance": INSTANCE_ID,
        }))
        return response
    except Exception:
        _error_count += 1
        raise


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    user_id: str = Field(..., min_length=1, max_length=100)


class AskResponse(BaseModel):
    question: str
    answer: str
    model: str
    user_id: str
    history_length: int
    timestamp: str
    instance_id: str


@app.get("/", tags=["Info"])
def root():
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "instance_id": INSTANCE_ID,
        "endpoints": {
            "ask": "POST /ask (requires X-API-Key)",
            "health": "GET /health",
            "ready": "GET /ready",
        },
    }


@app.post("/ask", response_model=AskResponse, tags=["Agent"])
async def ask_agent(
    body: AskRequest,
    request: Request,
    _key: str = Depends(verify_api_key),
):
    check_rate_limit(body.user_id)

    input_tokens = len(body.question.split()) * 2
    estimated = estimate_cost(input_tokens, 0)
    check_budget(body.user_id, estimated)

    logger.info(json.dumps({
        "event": "agent_call",
        "user_id": body.user_id,
        "q_len": len(body.question),
        "client": str(request.client.host) if request.client else "unknown",
        "instance": INSTANCE_ID,
    }))

    history = _get_history(body.user_id)
    _append_history(body.user_id, "user", body.question)

    answer = llm_ask(body.question)
    _append_history(body.user_id, "assistant", answer)

    output_tokens = len(answer.split()) * 2
    actual_cost = estimate_cost(input_tokens, output_tokens)
    record_cost(body.user_id, actual_cost)

    return AskResponse(
        question=body.question,
        answer=answer,
        model=settings.llm_model,
        user_id=body.user_id,
        history_length=len(history) + 2,
        timestamp=datetime.now(timezone.utc).isoformat(),
        instance_id=INSTANCE_ID,
    )


@app.get("/health", tags=["Operations"])
def health():
    return {
        "status": "ok",
        "version": settings.app_version,
        "environment": settings.environment,
        "instance_id": INSTANCE_ID,
        "uptime_seconds": round(time.time() - START_TIME, 1),
        "total_requests": _request_count,
        "checks": {"llm": "mock" if not settings.openai_api_key else "openai"},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/ready", tags=["Operations"])
def ready():
    if not _is_ready or not ping_redis():
        raise HTTPException(503, "Not ready")
    return {"ready": True, "instance_id": INSTANCE_ID}


@app.get("/metrics", tags=["Operations"])
def metrics(_key: str = Depends(verify_api_key)):
    r = get_redis()
    return {
        "instance_id": INSTANCE_ID,
        "uptime_seconds": round(time.time() - START_TIME, 1),
        "total_requests": _request_count,
        "error_count": _error_count,
        "redis_connected": ping_redis(),
        "redis_info": r.info("memory") if ping_redis() else {},
    }


def _handle_signal(signum, _frame):
    logger.info(json.dumps({"event": "signal", "signum": signum, "instance": INSTANCE_ID}))


signal.signal(signal.SIGTERM, _handle_signal)


if __name__ == "__main__":
    logger.info(f"Starting {settings.app_name} on {settings.host}:{settings.port}")
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        timeout_graceful_shutdown=30,
    )

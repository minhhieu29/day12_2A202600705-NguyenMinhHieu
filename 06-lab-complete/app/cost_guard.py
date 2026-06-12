"""Redis-based monthly cost guard per user."""
from datetime import datetime

from fastapi import HTTPException

from app.config import settings
from app.redis_client import get_redis

PRICE_PER_1K_INPUT_TOKENS = 0.00015
PRICE_PER_1K_OUTPUT_TOKENS = 0.0006


def _month_key(user_id: str) -> str:
    month = datetime.now().strftime("%Y-%m")
    return f"budget:{user_id}:{month}"


def estimate_cost(input_tokens: int, output_tokens: int) -> float:
    return (
        (input_tokens / 1000) * PRICE_PER_1K_INPUT_TOKENS
        + (output_tokens / 1000) * PRICE_PER_1K_OUTPUT_TOKENS
    )


def check_budget(user_id: str, estimated_cost: float) -> None:
    """Check monthly budget before LLM call. Raises HTTP 402 if exceeded."""
    r = get_redis()
    key = _month_key(user_id)
    current = float(r.get(key) or 0)

    if current + estimated_cost > settings.monthly_budget_usd:
        raise HTTPException(
            status_code=402,
            detail={
                "error": "Monthly budget exceeded",
                "used_usd": round(current, 4),
                "budget_usd": settings.monthly_budget_usd,
            },
        )


def record_cost(user_id: str, cost: float) -> None:
    """Record actual cost after LLM call."""
    r = get_redis()
    key = _month_key(user_id)
    r.incrbyfloat(key, cost)
    r.expire(key, 32 * 24 * 3600)

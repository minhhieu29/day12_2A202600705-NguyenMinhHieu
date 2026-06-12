"""Redis-based sliding window rate limiter."""
import time

from fastapi import HTTPException

from app.config import settings
from app.redis_client import get_redis


def check_rate_limit(user_id: str) -> None:
    """
    Sliding window rate limit per user.
    Raises HTTP 429 when limit exceeded.
    """
    r = get_redis()
    now = time.time()
    window_start = now - 60
    key = f"rate:{user_id}"

    pipe = r.pipeline()
    pipe.zremrangebyscore(key, 0, window_start)
    pipe.zcard(key)
    pipe.zadd(key, {str(now): now})
    pipe.expire(key, 120)
    results = pipe.execute()

    current_count = results[1]
    if current_count >= settings.rate_limit_per_minute:
        r.zrem(key, str(now))
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded: {settings.rate_limit_per_minute} req/min",
            headers={"Retry-After": "60"},
        )

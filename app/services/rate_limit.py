import time
from collections import defaultdict

from fastapi import HTTPException
from redis import Redis

from app.core.config import settings

_memory: dict[str, list[float]] = defaultdict(list)


def check_rate_limit(key: str) -> None:
    now = time.monotonic()
    values = [value for value in _memory[key] if now - value < settings.rate_limit_window_seconds]
    if len(values) >= settings.rate_limit_requests:
        raise HTTPException(429, "Too many submissions; try again later")
    values.append(now)
    _memory[key] = values
    try:
        client = Redis.from_url(settings.redis_url, socket_connect_timeout=0.2)
        redis_key = f"rate:{key}:{int(time.time() // settings.rate_limit_window_seconds)}"
        count = client.incr(redis_key)
        client.expire(redis_key, settings.rate_limit_window_seconds)
        if count > settings.rate_limit_requests:
            raise HTTPException(429, "Too many submissions; try again later")
    except HTTPException:
        raise
    except Exception:
        pass

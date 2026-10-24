import logging
import time
from typing import Callable, Optional
from fastapi import Request, HTTPException, status
import redis

from app.core.config import settings

logger = logging.getLogger(__name__)

# Lazily initialized Redis client
_redis_client: Optional[redis.Redis] = None


def get_redis_client() -> Optional[redis.Redis]:
    global _redis_client
    if _redis_client is None:
        try:
            _redis_client = redis.from_url(
                settings.REDIS_URL,
                socket_connect_timeout=1.0,
                socket_timeout=1.0,
                decode_responses=True
            )
            # Test connectivity
            _redis_client.ping()
        except Exception as exc:
            logger.warning("Redis rate limiter connection unavailable: %s. Operating in fail-open mode.", exc)
            _redis_client = None
    return _redis_client


def rate_limit(key_prefix: str, max_requests: int = 10, window_seconds: int = 60) -> Callable:
    """
    FastAPI dependency that enforces rate limiting per client IP.
    Uses Redis fixed-window counters with automatic expiry.
    Fails open safely if Redis is unreachable to prevent application outages.
    """
    def dependency(request: Request):
        # Extract direct client host to prevent header spoofing bypass
        client_ip = "127.0.0.1"
        if request.client and request.client.host:
            client_ip = request.client.host

        r = get_redis_client()
        if r is None:
            # Redis is offline; fail-open to preserve core availability
            return

        rate_key = f"rl:{key_prefix}:{client_ip}"
        try:
            current_count = r.incr(rate_key)
            if current_count == 1:
                r.expire(rate_key, window_seconds)

            if current_count > max_requests:
                ttl = r.ttl(rate_key)
                retry_after = str(max(ttl, 1))
                logger.warning("Rate limit exceeded for %s on %s (count=%d, max=%d)", client_ip, key_prefix, current_count, max_requests)
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Too many requests. Please wait {retry_after} seconds before retrying.",
                    headers={"Retry-After": retry_after}
                )
        except HTTPException:
            raise
        except Exception as exc:
            logger.warning("Error communicating with Redis in rate limiter: %s", exc)
            # Fail open on cache errors
            return

    return dependency

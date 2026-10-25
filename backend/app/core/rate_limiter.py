import ipaddress
import logging
import time
from typing import Callable, Optional, List
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


def is_ip_trusted(ip_str: str, trusted_list: List[str]) -> bool:
    """Checks whether an IP address belongs to the trusted proxies/networks list."""
    ip_str = (ip_str or "").strip()
    if not ip_str:
        return False
    if ip_str.lower() in [t.lower().strip() for t in trusted_list]:
        return True

    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return False

    for trusted in trusted_list:
        trusted = trusted.strip()
        try:
            if "/" in trusted:
                network = ipaddress.ip_network(trusted, strict=False)
                if ip in network:
                    return True
            else:
                trusted_ip = ipaddress.ip_address(trusted)
                if ip == trusted_ip:
                    return True
        except ValueError:
            continue
    return False


def get_client_ip(request: Request, trusted_proxies: Optional[List[str]] = None) -> str:
    """
    Extracts the legitimate client IP address.
    Behind a trusted reverse proxy (e.g. Nginx), inspects X-Forwarded-For or X-Real-IP,
    walking backwards through the proxy chain to prevent header spoofing.
    If the immediate peer is not in trusted_proxies, forwarding headers are ignored.
    """
    if trusted_proxies is None:
        trusted_proxies = getattr(settings, "TRUSTED_PROXIES", ["127.0.0.1", "::1"])

    direct_ip = "127.0.0.1"
    if request.client and request.client.host:
        direct_ip = request.client.host.strip()

    # If the direct peer is not trusted, never trust forwarded headers
    if not is_ip_trusted(direct_ip, trusted_proxies):
        return direct_ip

    # Peer is a trusted reverse proxy; parse X-Forwarded-For
    xff = request.headers.get("x-forwarded-for")
    if xff:
        raw_ips = [ip.strip() for ip in xff.split(",") if ip.strip()]
        # Walk right to left, skipping trusted proxies; the first untrusted IP is the real client
        for candidate in reversed(raw_ips):
            try:
                ipaddress.ip_address(candidate)
            except ValueError:
                continue
            if not is_ip_trusted(candidate, trusted_proxies):
                return candidate
        if raw_ips:
            return raw_ips[0]

    # Fallback to X-Real-IP if XFF was not present or valid
    x_real_ip = request.headers.get("x-real-ip")
    if x_real_ip:
        real_ip = x_real_ip.strip()
        try:
            ipaddress.ip_address(real_ip)
            return real_ip
        except ValueError:
            pass

    return direct_ip


def rate_limit(key_prefix: str, max_requests: int = 10, window_seconds: int = 60) -> Callable:
    """
    FastAPI dependency that enforces rate limiting per client IP.
    Uses Redis fixed-window counters with automatic expiry.
    Fails open safely if Redis is unreachable to prevent application outages.
    """
    def dependency(request: Request):
        client_ip = get_client_ip(request)

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

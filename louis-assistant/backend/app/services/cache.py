"""
루이스 개인비서 - 응답 캐시
Redis 우선, 없으면 메모리 TTL 캐시 사용.
동일한 날씨/환율 질문은 캐시로 비용 절감.
"""
import json
import logging
import time
from typing import Any

log = logging.getLogger("louis.services.cache")

# 메모리 캐시 (Redis 없을 때 폴백)
_mem_cache: dict[str, tuple[float, Any]] = {}

_redis_client = None


def _get_redis():
    """Redis 클라이언트를 지연 초기화합니다."""
    global _redis_client
    if _redis_client is None:
        try:
            import redis
            from app.config import settings
            _redis_client = redis.from_url(settings.redis_url, decode_responses=True)
            _redis_client.ping()
            log.info("Redis 연결 성공")
        except Exception as exc:
            log.info(f"Redis 없음, 메모리 캐시 사용: {exc}")
            _redis_client = False  # 연결 불가 마킹
    return _redis_client if _redis_client else None


def get(key: str) -> Any | None:
    """캐시에서 값을 가져옵니다."""
    r = _get_redis()
    if r:
        try:
            val = r.get(key)
            return json.loads(val) if val else None
        except Exception:
            pass

    # 메모리 캐시
    entry = _mem_cache.get(key)
    if entry:
        ts, val = entry
        if time.time() - ts < 600:  # 10분
            return val
        del _mem_cache[key]
    return None


def set(key: str, value: Any, ttl: int = 600):
    """캐시에 값을 저장합니다."""
    r = _get_redis()
    if r:
        try:
            r.setex(key, ttl, json.dumps(value, ensure_ascii=False))
            return
        except Exception:
            pass

    # 메모리 캐시
    _mem_cache[key] = (time.time(), value)


def delete(key: str):
    """캐시 항목을 삭제합니다."""
    r = _get_redis()
    if r:
        try:
            r.delete(key)
        except Exception:
            pass
    _mem_cache.pop(key, None)


def make_weather_key(city: str) -> str:
    return f"weather:{city.lower()}"


def make_rate_key(from_ccy: str) -> str:
    return f"rate:{from_ccy.upper()}"

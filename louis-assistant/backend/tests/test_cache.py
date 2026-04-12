"""
캐시 서비스 테스트
get / set / delete / 메모리 TTL / make_weather_key / make_rate_key /
Redis 폴백 동작을 검증합니다.
"""
import time
import pytest
from unittest.mock import patch, MagicMock


# ── 헬퍼: 각 테스트 전에 메모리 캐시 초기화 ─────────────────────

@pytest.fixture(autouse=True)
def clear_cache():
    """각 테스트 전후로 메모리 캐시와 Redis 클라이언트를 초기화합니다."""
    import app.services.cache as cache_mod
    cache_mod._mem_cache.clear()
    cache_mod._redis_client = None
    yield
    cache_mod._mem_cache.clear()
    cache_mod._redis_client = None


def _force_memory_only():
    """Redis 없음 상태를 강제합니다 (False = 연결 불가 마킹)."""
    import app.services.cache as cache_mod
    cache_mod._redis_client = False


# ════════════════════════════════════════════════════════════
# 키 생성 헬퍼
# ════════════════════════════════════════════════════════════

class TestMakeKeys:

    def test_weather_key_format(self):
        from app.services.cache import make_weather_key
        assert make_weather_key("Seoul") == "weather:seoul"

    def test_weather_key_lowercase(self):
        from app.services.cache import make_weather_key
        assert make_weather_key("BUSAN") == "weather:busan"

    def test_rate_key_format(self):
        from app.services.cache import make_rate_key
        assert make_rate_key("usd") == "rate:USD"

    def test_rate_key_uppercase(self):
        from app.services.cache import make_rate_key
        assert make_rate_key("eur") == "rate:EUR"

    def test_weather_key_mixed_case(self):
        from app.services.cache import make_weather_key
        assert make_weather_key("NewYork") == "weather:newyork"


# ════════════════════════════════════════════════════════════
# 메모리 캐시 (Redis 없을 때)
# ════════════════════════════════════════════════════════════

class TestMemoryCache:

    def test_get_missing_returns_none(self):
        _force_memory_only()
        from app.services.cache import get
        assert get("nonexistent") is None

    def test_set_and_get(self):
        _force_memory_only()
        from app.services.cache import set, get
        set("city", "Seoul")
        assert get("city") == "Seoul"

    def test_set_dict_value(self):
        _force_memory_only()
        from app.services.cache import set, get
        data = {"temp": 18, "condition": "맑음"}
        set("weather:seoul", data)
        assert get("weather:seoul") == data

    def test_set_list_value(self):
        _force_memory_only()
        from app.services.cache import set, get
        set("items", [1, 2, 3])
        assert get("items") == [1, 2, 3]

    def test_delete_removes_key(self):
        _force_memory_only()
        from app.services.cache import set, get, delete
        set("temp_key", "value")
        delete("temp_key")
        assert get("temp_key") is None

    def test_delete_nonexistent_key_no_error(self):
        _force_memory_only()
        from app.services.cache import delete
        delete("ghost_key")  # 예외 없이 통과해야 합니다

    def test_overwrite_value(self):
        _force_memory_only()
        from app.services.cache import set, get
        set("k", "first")
        set("k", "second")
        assert get("k") == "second"

    def test_ttl_expired_returns_none(self):
        """만료된 항목은 None을 반환합니다."""
        _force_memory_only()
        import app.services.cache as cache_mod
        # 601초 전에 저장된 항목으로 직접 삽입
        old_ts = time.time() - 601
        cache_mod._mem_cache["expired_key"] = (old_ts, "stale_value")
        assert cache_mod.get("expired_key") is None

    def test_ttl_within_window_returns_value(self):
        """아직 유효한 항목은 값을 반환합니다."""
        _force_memory_only()
        import app.services.cache as cache_mod
        fresh_ts = time.time() - 300  # 5분 전
        cache_mod._mem_cache["fresh_key"] = (fresh_ts, "fresh_value")
        assert cache_mod.get("fresh_key") == "fresh_value"

    def test_expired_entry_cleaned_up(self):
        """만료된 항목은 get 호출 시 제거됩니다."""
        _force_memory_only()
        import app.services.cache as cache_mod
        old_ts = time.time() - 700
        cache_mod._mem_cache["to_clean"] = (old_ts, "dead")
        cache_mod.get("to_clean")
        assert "to_clean" not in cache_mod._mem_cache


# ════════════════════════════════════════════════════════════
# Redis 연동 (Mock)
# ════════════════════════════════════════════════════════════

class TestRedisCache:

    def _make_redis_mock(self, get_return=None):
        """Redis 클라이언트 Mock을 반환합니다."""
        mock_r = MagicMock()
        mock_r.ping.return_value = True
        mock_r.get.return_value = get_return
        mock_r.setex.return_value = True
        mock_r.delete.return_value = 1
        return mock_r

    def test_get_from_redis(self):
        """Redis에서 값을 가져옵니다."""
        import json
        import app.services.cache as cache_mod

        mock_r = self._make_redis_mock(get_return=json.dumps({"temp": 20}))
        cache_mod._redis_client = mock_r

        from app.services.cache import get
        result = get("weather:seoul")
        assert result == {"temp": 20}
        mock_r.get.assert_called_once_with("weather:seoul")

    def test_get_redis_miss_falls_to_memory(self):
        """Redis에 없으면 메모리 캐시를 확인합니다."""
        import app.services.cache as cache_mod

        mock_r = self._make_redis_mock(get_return=None)
        cache_mod._redis_client = mock_r
        cache_mod._mem_cache["fallback_key"] = (time.time(), "mem_value")

        from app.services.cache import get
        assert get("fallback_key") == "mem_value"

    def test_set_uses_redis(self):
        """값을 Redis에 저장합니다."""
        import json
        import app.services.cache as cache_mod

        mock_r = self._make_redis_mock()
        cache_mod._redis_client = mock_r

        from app.services.cache import set
        set("rate:USD", 1350.5, ttl=300)
        mock_r.setex.assert_called_once_with(
            "rate:USD", 300, json.dumps(1350.5, ensure_ascii=False)
        )

    def test_set_redis_error_falls_to_memory(self):
        """Redis 저장 실패 시 메모리 캐시에 저장합니다."""
        import app.services.cache as cache_mod

        mock_r = self._make_redis_mock()
        mock_r.setex.side_effect = Exception("Redis 연결 끊김")
        cache_mod._redis_client = mock_r

        from app.services.cache import set, get
        set("fallback_write", "data")

        # 메모리 캐시에서 읽혀야 합니다 (Redis mock은 None 반환하므로 메모리 폴백)
        mock_r.get.return_value = None
        assert get("fallback_write") == "data"

    def test_delete_calls_redis(self):
        """delete가 Redis에서 키를 삭제합니다."""
        import app.services.cache as cache_mod

        mock_r = self._make_redis_mock()
        cache_mod._redis_client = mock_r

        from app.services.cache import delete
        delete("old_key")
        mock_r.delete.assert_called_once_with("old_key")

    def test_delete_redis_error_still_clears_memory(self):
        """Redis 삭제 실패해도 메모리 캐시에서는 삭제됩니다."""
        import app.services.cache as cache_mod

        mock_r = self._make_redis_mock()
        mock_r.delete.side_effect = Exception("연결 끊김")
        cache_mod._redis_client = mock_r
        cache_mod._mem_cache["dual_key"] = (time.time(), "mem_val")

        from app.services.cache import delete, get
        delete("dual_key")
        mock_r.get.return_value = None
        assert get("dual_key") is None

    def test_get_redis_exception_falls_to_memory(self):
        """Redis get 예외 시 메모리 캐시로 폴백합니다."""
        import app.services.cache as cache_mod

        mock_r = self._make_redis_mock()
        mock_r.get.side_effect = Exception("타임아웃")
        cache_mod._redis_client = mock_r
        cache_mod._mem_cache["safe_key"] = (time.time(), "safe_val")

        from app.services.cache import get
        assert get("safe_key") == "safe_val"


# ════════════════════════════════════════════════════════════
# Redis 초기화 실패 폴백
# ════════════════════════════════════════════════════════════

class TestRedisInitFallback:

    def test_redis_unavailable_uses_memory(self):
        """Redis 연결 실패 시 메모리 캐시를 사용합니다."""
        import app.services.cache as cache_mod
        cache_mod._redis_client = None

        with patch("redis.from_url", side_effect=Exception("연결 거부")):
            from app.services.cache import set, get
            set("no_redis", "value")
            assert get("no_redis") == "value"

    def test_redis_marked_false_after_failure(self):
        """Redis 초기화 실패 후 _redis_client는 False로 마킹됩니다."""
        import app.services.cache as cache_mod
        cache_mod._redis_client = None

        with patch("redis.from_url", side_effect=Exception("연결 거부")):
            cache_mod._get_redis()

        assert cache_mod._redis_client is False

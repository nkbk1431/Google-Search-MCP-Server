"""
루이스 개인비서 - API 할당량 관리
Google API 분당 호출 한도를 초과하지 않도록 보호합니다.
"""
from datetime import datetime
from threading import Lock


class QuotaGuard:
    """분당 API 호출 횟수를 제한하는 가드."""

    def __init__(self, max_per_minute: int = 50, name: str = "api"):
        self.max = max_per_minute
        self.name = name
        self._calls: list[datetime] = []
        self._lock = Lock()

    def check(self):
        """
        현재 호출이 분당 한도를 초과하지 않는지 확인합니다.

        Raises:
            RuntimeError: 한도 초과 시
        """
        with self._lock:
            now = datetime.now()
            self._calls = [t for t in self._calls if (now - t).total_seconds() < 60]
            if len(self._calls) >= self.max:
                raise RuntimeError(
                    f"{self.name} API 호출 한도({self.max}/분)를 초과했어요. 잠시 후 다시 시도해주세요."
                )
            self._calls.append(now)

    @property
    def current_count(self) -> int:
        """현재 분에 이미 발생한 호출 수."""
        with self._lock:
            now = datetime.now()
            self._calls = [t for t in self._calls if (now - t).total_seconds() < 60]
            return len(self._calls)


# 전역 인스턴스
google_quota = QuotaGuard(max_per_minute=50, name="Google")

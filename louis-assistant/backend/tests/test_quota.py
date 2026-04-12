"""
API 할당량 관리 서비스 테스트
QuotaGuard.check() / current_count를 검증합니다.
"""
import time
import threading
import pytest

from app.services.quota import QuotaGuard


class TestQuotaGuard:

    def test_first_call_succeeds(self):
        """첫 번째 호출은 성공합니다."""
        guard = QuotaGuard(max_per_minute=5, name="test")
        guard.check()  # 예외 없이 통과

    def test_calls_within_limit_succeed(self):
        """한도 이하의 호출은 모두 성공합니다."""
        guard = QuotaGuard(max_per_minute=5, name="test")
        for _ in range(5):
            guard.check()

    def test_exceeds_limit_raises_runtime_error(self):
        """한도 초과 시 RuntimeError가 발생합니다."""
        guard = QuotaGuard(max_per_minute=3, name="test")
        for _ in range(3):
            guard.check()

        with pytest.raises(RuntimeError) as exc_info:
            guard.check()

        assert "한도" in str(exc_info.value) or "초과" in str(exc_info.value)

    def test_error_message_contains_name_and_limit(self):
        """오류 메시지에 서비스 이름과 한도가 포함됩니다."""
        guard = QuotaGuard(max_per_minute=1, name="Google")
        guard.check()  # 1회 허용

        with pytest.raises(RuntimeError) as exc_info:
            guard.check()

        error_msg = str(exc_info.value)
        assert "Google" in error_msg
        assert "1" in error_msg

    def test_current_count_starts_at_zero(self):
        """초기 current_count는 0입니다."""
        guard = QuotaGuard(max_per_minute=10)
        assert guard.current_count == 0

    def test_current_count_increments(self):
        """호출 후 current_count가 증가합니다."""
        guard = QuotaGuard(max_per_minute=10)
        guard.check()
        assert guard.current_count == 1
        guard.check()
        assert guard.current_count == 2

    def test_current_count_does_not_exceed_calls(self):
        """current_count가 실제 호출 횟수를 초과하지 않습니다."""
        guard = QuotaGuard(max_per_minute=10)
        for _ in range(5):
            guard.check()
        assert guard.current_count == 5

    def test_default_max_is_50(self):
        """기본 한도는 50입니다."""
        guard = QuotaGuard()
        assert guard.max == 50

    def test_default_name_is_api(self):
        """기본 이름은 'api'입니다."""
        guard = QuotaGuard()
        assert guard.name == "api"

    def test_thread_safety(self):
        """동시 다중 스레드에서도 한도가 정확히 지켜집니다."""
        guard = QuotaGuard(max_per_minute=10, name="concurrent")
        success_count = 0
        error_count = 0
        lock = threading.Lock()

        def make_call():
            nonlocal success_count, error_count
            try:
                guard.check()
                with lock:
                    success_count += 1
            except RuntimeError:
                with lock:
                    error_count += 1

        threads = [threading.Thread(target=make_call) for _ in range(15)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 정확히 10번만 성공해야 합니다
        assert success_count == 10
        assert error_count == 5

    def test_independent_guards_do_not_interfere(self):
        """두 QuotaGuard 인스턴스는 서로 독립적입니다."""
        guard_a = QuotaGuard(max_per_minute=2, name="A")
        guard_b = QuotaGuard(max_per_minute=2, name="B")

        guard_a.check()
        guard_a.check()
        guard_b.check()  # B는 아직 여유 있음

        with pytest.raises(RuntimeError):
            guard_a.check()  # A만 초과

        guard_b.check()  # B는 정상 통과

    def test_calls_list_is_cleaned_after_minute(self):
        """1분이 지난 호출 기록은 제거됩니다 (만료 처리 확인)."""
        from datetime import datetime, timedelta
        guard = QuotaGuard(max_per_minute=5)

        # 1분 1초 전 호출 기록을 수동으로 삽입
        old_time = datetime.now() - timedelta(seconds=61)
        guard._calls = [old_time] * 5  # 만료된 기록 5개

        # 만료된 기록이 정리되므로 새 호출은 성공해야 합니다
        guard.check()
        assert guard.current_count == 1

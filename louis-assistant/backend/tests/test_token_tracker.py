"""
토큰 사용량 추적 유틸리티 테스트
record_usage / get_daily_usage / get_monthly_cost_usd 를 검증합니다.
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock


# ── record_usage ─────────────────────────────────────────

class TestRecordUsage:

    def test_record_usage_success(self):
        """토큰 사용량이 DB에 정상 저장됩니다."""
        from app.utils.token_tracker import record_usage

        mock_db = MagicMock()
        mock_db.__enter__ = MagicMock(return_value=mock_db)
        mock_db.__exit__ = MagicMock(return_value=False)

        with patch("app.utils.token_tracker.get_sync_db", return_value=mock_db):
            record_usage(
                user_id="alice",
                session_id="sess-001",
                model="claude-haiku-4-5",
                input_tokens=120,
                output_tokens=80,
            )

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    def test_record_usage_db_error_silently_ignored(self):
        """DB 오류 시 예외가 전파되지 않습니다 (fire-and-forget)."""
        from app.utils.token_tracker import record_usage

        with patch("app.utils.token_tracker.get_sync_db", side_effect=Exception("DB 연결 실패")):
            # 예외가 발생하지 않아야 합니다
            record_usage("user", "sess", "model", 100, 50)

    def test_record_usage_adds_correct_model(self):
        """저장되는 TokenUsage 객체에 올바른 모델명이 반영됩니다."""
        from app.utils.token_tracker import record_usage
        from app.db.models import TokenUsage

        captured = []
        mock_db = MagicMock()
        mock_db.__enter__ = MagicMock(return_value=mock_db)
        mock_db.__exit__ = MagicMock(return_value=False)
        mock_db.add.side_effect = lambda obj: captured.append(obj)

        with patch("app.utils.token_tracker.get_sync_db", return_value=mock_db):
            record_usage("bob", "s1", "claude-sonnet-4-6", 200, 100)

        assert len(captured) == 1
        assert captured[0].model == "claude-sonnet-4-6"
        assert captured[0].input_tokens == 200
        assert captured[0].output_tokens == 100


# ── get_daily_usage ──────────────────────────────────────

class TestGetDailyUsage:

    def _mock_db_result(self, total_in: int, total_out: int):
        mock_db = MagicMock()
        mock_db.__enter__ = MagicMock(return_value=mock_db)
        mock_db.__exit__ = MagicMock(return_value=False)

        mock_result = MagicMock()
        mock_result.total_in = total_in
        mock_result.total_out = total_out
        mock_db.query.return_value.filter.return_value.first.return_value = mock_result
        return mock_db

    def test_returns_token_counts(self):
        from app.utils.token_tracker import get_daily_usage

        mock_db = self._mock_db_result(total_in=500, total_out=300)
        with patch("app.utils.token_tracker.get_sync_db", return_value=mock_db):
            result = get_daily_usage("alice")

        assert result["in"] == 500
        assert result["out"] == 300

    def test_returns_zero_on_no_data(self):
        from app.utils.token_tracker import get_daily_usage

        mock_db = self._mock_db_result(total_in=None, total_out=None)
        with patch("app.utils.token_tracker.get_sync_db", return_value=mock_db):
            result = get_daily_usage("alice")

        assert result["in"] == 0
        assert result["out"] == 0

    def test_returns_correct_date_key(self):
        from app.utils.token_tracker import get_daily_usage

        mock_db = self._mock_db_result(0, 0)
        today = datetime.now().date().isoformat()
        with patch("app.utils.token_tracker.get_sync_db", return_value=mock_db):
            result = get_daily_usage("alice")

        assert result["date"] == today

    def test_custom_date(self):
        from app.utils.token_tracker import get_daily_usage

        target_date = datetime(2026, 3, 15)
        mock_db = self._mock_db_result(100, 50)
        with patch("app.utils.token_tracker.get_sync_db", return_value=mock_db):
            result = get_daily_usage("alice", date=target_date)

        assert result["date"] == "2026-03-15"

    def test_db_error_returns_zeros(self):
        from app.utils.token_tracker import get_daily_usage

        with patch("app.utils.token_tracker.get_sync_db", side_effect=Exception("DB 오류")):
            result = get_daily_usage("alice")

        assert result["in"] == 0
        assert result["out"] == 0


# ── get_monthly_cost_usd ─────────────────────────────────

class TestGetMonthlyCostUsd:

    def _mock_db_monthly(self, total_in: int, total_out: int):
        mock_db = MagicMock()
        mock_db.__enter__ = MagicMock(return_value=mock_db)
        mock_db.__exit__ = MagicMock(return_value=False)

        mock_result = MagicMock()
        mock_result.total_in = total_in
        mock_result.total_out = total_out
        mock_db.query.return_value.filter.return_value.first.return_value = mock_result
        return mock_db

    def test_cost_calculation_haiku_pricing(self):
        """Haiku 가격 기준: Input $1/1M, Output $5/1M."""
        from app.utils.token_tracker import get_monthly_cost_usd

        # 1M input + 200K output → $1.00 + $1.00 = $2.00
        mock_db = self._mock_db_monthly(1_000_000, 200_000)
        with patch("app.utils.token_tracker.get_sync_db", return_value=mock_db):
            cost = get_monthly_cost_usd("alice")

        assert abs(cost - 2.0) < 0.001

    def test_zero_usage_returns_zero_cost(self):
        from app.utils.token_tracker import get_monthly_cost_usd

        mock_db = self._mock_db_monthly(0, 0)
        with patch("app.utils.token_tracker.get_sync_db", return_value=mock_db):
            cost = get_monthly_cost_usd("alice")

        assert cost == 0.0

    def test_cost_rounded_to_4_decimal_places(self):
        from app.utils.token_tracker import get_monthly_cost_usd

        mock_db = self._mock_db_monthly(12345, 6789)
        with patch("app.utils.token_tracker.get_sync_db", return_value=mock_db):
            cost = get_monthly_cost_usd("alice")

        # 소수점 4자리로 반올림 확인
        assert cost == round(cost, 4)

    def test_none_values_treated_as_zero(self):
        from app.utils.token_tracker import get_monthly_cost_usd

        mock_db = self._mock_db_monthly(None, None)
        with patch("app.utils.token_tracker.get_sync_db", return_value=mock_db):
            cost = get_monthly_cost_usd("alice")

        assert cost == 0.0

    def test_db_error_returns_zero(self):
        from app.utils.token_tracker import get_monthly_cost_usd

        with patch("app.utils.token_tracker.get_sync_db", side_effect=Exception("DB 오류")):
            cost = get_monthly_cost_usd("alice")

        assert cost == 0.0

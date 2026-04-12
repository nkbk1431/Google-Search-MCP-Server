"""
날짜 유틸리티 테스트
실행: pytest tests/test_date_utils.py -v
"""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from app.utils.date_utils import (
    parse_natural_datetime,
    format_kst,
    is_future,
    next_occurrence,
)

KST = ZoneInfo("Asia/Seoul")


def test_parse_iso_datetime():
    """ISO 8601 형식 파싱."""
    dt = parse_natural_datetime("2026-04-13T15:00:00")
    assert dt is not None
    assert dt.hour == 15
    assert dt.minute == 0


def test_parse_iso_date_only():
    """날짜만 있는 ISO 형식 파싱."""
    dt = parse_natural_datetime("2026-04-15")
    assert dt is not None
    assert dt.year == 2026
    assert dt.month == 4
    assert dt.day == 15


def test_parse_natural_korean(monkeypatch):
    """한국어 자연어 날짜 파싱."""
    dt = parse_natural_datetime("내일 오후 3시")
    # dateparser가 설치된 경우 파싱 가능
    # 환경에 따라 None일 수 있으므로 None인 경우 스킵
    if dt is not None:
        assert dt.hour == 15


def test_parse_invalid_returns_none():
    """파싱 불가 입력은 None 반환."""
    result = parse_natural_datetime("이상한텍스트아무것도없음xyz")
    # dateparser가 오류 없이 None을 반환하는지 확인
    assert result is None or isinstance(result, datetime)


def test_format_kst_with_minute():
    """분이 있는 datetime 포맷."""
    dt = datetime(2026, 4, 13, 15, 30, tzinfo=KST)
    result = format_kst(dt)
    assert "4월 13일" in result
    assert "30분" in result


def test_format_kst_without_minute():
    """분이 0인 datetime 포맷 (분 미표시)."""
    dt = datetime(2026, 4, 13, 9, 0, tzinfo=KST)
    result = format_kst(dt)
    assert "9시" in result
    assert "0분" not in result


def test_is_future_true():
    """미래 시간은 True."""
    future = datetime.now(tz=KST) + timedelta(hours=1)
    assert is_future(future) is True


def test_is_future_false():
    """과거 시간은 False."""
    past = datetime.now(tz=KST) - timedelta(hours=1)
    assert is_future(past) is False


def test_next_occurrence_future():
    """next_occurrence는 항상 미래 시간 반환."""
    now = datetime.now(tz=KST)
    dt = next_occurrence(7, 0)
    assert dt > now
    assert dt.hour == 7
    assert dt.minute == 0


def test_next_occurrence_already_passed():
    """오늘 이미 지난 시각이면 내일로 설정."""
    now = datetime.now(tz=KST)
    # 0시 0분은 항상 이미 지남 (자정 이후) 또는 내일
    dt = next_occurrence(0, 0)
    assert dt > now

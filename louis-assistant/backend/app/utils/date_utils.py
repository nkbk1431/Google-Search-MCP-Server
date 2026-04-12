"""
루이스 개인비서 - 날짜/시간 파싱 유틸리티
자연어 표현("내일 오후 3시", "다음 주 금요일")을 datetime으로 변환합니다.
"""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from typing import Optional

import dateparser

KST = ZoneInfo("Asia/Seoul")

_DATEPARSER_SETTINGS = {
    "PREFER_DATES_FROM": "future",
    "TIMEZONE": "Asia/Seoul",
    "RETURN_AS_TIMEZONE_AWARE": True,
    "DATE_ORDER": "YMD",
}


def parse_natural_datetime(text: str) -> Optional[datetime]:
    """
    자연어 날짜/시간 표현을 KST datetime으로 변환합니다.

    Args:
        text: "내일 오후 3시", "다음 주 월요일", "2026-04-15T10:00:00" 등

    Returns:
        timezone-aware datetime (KST) 또는 None
    """
    # ISO 8601 우선 시도
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            naive = datetime.strptime(text.strip(), fmt)
            return naive.replace(tzinfo=KST)
        except ValueError:
            continue

    # dateparser 자연어 파싱
    try:
        dt = dateparser.parse(text, settings=_DATEPARSER_SETTINGS, languages=["ko", "en"])
        if dt:
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=KST)
            return dt
    except Exception:
        pass

    return None


def format_kst(dt: datetime) -> str:
    """datetime을 한국어로 포맷합니다. 예: '4월 13일 오후 3시 0분'"""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=KST)
    dt_kst = dt.astimezone(KST)
    hour = dt_kst.hour
    minute = dt_kst.minute
    ampm = "오전" if hour < 12 else "오후"
    h12 = hour % 12 or 12
    if minute:
        return f"{dt_kst.month}월 {dt_kst.day}일 {ampm} {h12}시 {minute}분"
    return f"{dt_kst.month}월 {dt_kst.day}일 {ampm} {h12}시"


def is_future(dt: datetime) -> bool:
    """datetime이 현재 시각 이후인지 확인합니다."""
    now = datetime.now(tz=KST)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=KST)
    return dt > now


def next_occurrence(hour: int, minute: int = 0) -> datetime:
    """오늘 또는 내일 해당 시각의 datetime을 반환합니다."""
    now = datetime.now(tz=KST)
    candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if candidate <= now:
        candidate += timedelta(days=1)
    return candidate

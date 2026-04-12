"""
루이스 개인비서 - Google Calendar 도구
일정 추가/조회/수정/삭제 기능 제공.
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import dateparser
from langchain_core.tools import tool

from app.services.google_auth import get_google_service
from app.services.quota import google_quota

log = logging.getLogger("louis.tools.calendar")

KST = timezone(timedelta(hours=9))
DEFAULT_TZ = "Asia/Seoul"


def _parse_time(time_str: str) -> Optional[datetime]:
    """자연어 시간 문자열을 datetime으로 변환합니다."""
    settings_dp = {
        "PREFER_DATES_FROM": "future",
        "TIMEZONE": "Asia/Seoul",
        "RETURN_AS_TIMEZONE_AWARE": True,
    }
    try:
        dt = dateparser.parse(time_str, settings=settings_dp, languages=["ko", "en"])
        return dt
    except Exception:
        return None


def _fmt_dt(dt: datetime) -> str:
    """datetime을 한국어 문자열로 포맷합니다."""
    return dt.strftime("%m월 %d일 %H시 %M분")


@tool
def add_calendar_event(
    title: str,
    start_time: str,
    duration_minutes: int = 60,
    description: str = "",
    location: str = "",
) -> str:
    """Google Calendar에 일정을 등록합니다.

    Args:
        title: 일정 제목
        start_time: 시작 시간 (ISO 8601 또는 자연어, 예: "내일 오후 3시")
        duration_minutes: 일정 길이(분). 기본 60분.
        description: 메모/설명
        location: 장소

    Returns:
        등록 결과 메시지
    """
    try:
        google_quota.check()
        svc = get_google_service("calendar", "v3")

        start = _parse_time(start_time)
        if start is None:
            return f"시간 형식을 인식하지 못했어요. 예: '내일 오후 3시' 또는 '2026-04-13T15:00:00'"

        end = start + timedelta(minutes=duration_minutes)
        event_body = {
            "summary": title,
            "description": description,
            "location": location,
            "start": {"dateTime": start.isoformat(), "timeZone": DEFAULT_TZ},
            "end": {"dateTime": end.isoformat(), "timeZone": DEFAULT_TZ},
            "reminders": {
                "useDefault": False,
                "overrides": [{"method": "popup", "minutes": 10}],
            },
        }
        result = svc.events().insert(calendarId="primary", body=event_body).execute()
        return f"일정 등록 완료: '{result.get('summary')}' ({_fmt_dt(start)})"

    except RuntimeError as exc:
        return str(exc)
    except Exception as exc:
        log.error(f"캘린더 등록 실패: {exc}", exc_info=True)
        return "일정 등록에 실패했어요. 잠시 후 다시 시도해주세요."


@tool
def list_calendar_events(days_ahead: int = 1, max_results: int = 10) -> str:
    """앞으로 n일 이내의 일정을 조회합니다.

    Args:
        days_ahead: 조회할 기간(일). 기본 1일.
        max_results: 최대 결과 수. 기본 10개.

    Returns:
        일정 목록 문자열
    """
    try:
        google_quota.check()
        svc = get_google_service("calendar", "v3")

        now_utc = datetime.utcnow().isoformat() + "Z"
        end_utc = (datetime.utcnow() + timedelta(days=days_ahead)).isoformat() + "Z"

        events = svc.events().list(
            calendarId="primary",
            timeMin=now_utc,
            timeMax=end_utc,
            singleEvents=True,
            orderBy="startTime",
            maxResults=max_results,
        ).execute().get("items", [])

        if not events:
            period = "오늘" if days_ahead == 1 else f"앞으로 {days_ahead}일"
            return f"{period} 예정된 일정이 없어요."

        lines = []
        for e in events:
            s = e["start"].get("dateTime", e["start"].get("date", ""))
            title = e.get("summary", "(제목 없음)")
            try:
                dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
                s_fmt = _fmt_dt(dt.astimezone(KST))
            except Exception:
                s_fmt = s
            lines.append(f"- {title} / {s_fmt}")

        return "\n".join(lines)

    except RuntimeError as exc:
        return str(exc)
    except Exception as exc:
        log.error(f"캘린더 조회 실패: {exc}", exc_info=True)
        return "일정 조회에 실패했어요."


@tool
def delete_calendar_event(event_id: str) -> str:
    """Google Calendar에서 특정 일정을 삭제합니다.

    Args:
        event_id: 삭제할 이벤트 ID (list_calendar_events로 확인)

    Returns:
        삭제 결과 메시지
    """
    try:
        google_quota.check()
        svc = get_google_service("calendar", "v3")
        svc.events().delete(calendarId="primary", eventId=event_id).execute()
        return "일정을 삭제했어요."
    except RuntimeError as exc:
        return str(exc)
    except Exception as exc:
        log.error(f"캘린더 삭제 실패: {exc}", exc_info=True)
        return "일정 삭제에 실패했어요."


@tool
def search_calendar_events(keyword: str, days_range: int = 30) -> str:
    """Google Calendar에서 키워드로 일정을 검색합니다.

    Args:
        keyword: 검색 키워드
        days_range: 검색 기간(일, 오늘 기준 앞뒤). 기본 30일.

    Returns:
        검색된 일정 목록
    """
    try:
        google_quota.check()
        svc = get_google_service("calendar", "v3")

        start_utc = (datetime.utcnow() - timedelta(days=days_range)).isoformat() + "Z"
        end_utc = (datetime.utcnow() + timedelta(days=days_range)).isoformat() + "Z"

        events = svc.events().list(
            calendarId="primary",
            timeMin=start_utc,
            timeMax=end_utc,
            q=keyword,
            singleEvents=True,
            orderBy="startTime",
            maxResults=10,
        ).execute().get("items", [])

        if not events:
            return f"'{keyword}' 관련 일정을 찾지 못했어요."

        lines = []
        for e in events:
            s = e["start"].get("dateTime", e["start"].get("date", ""))
            lines.append(f"- {e.get('summary','(제목없음)')} / {s} (ID: {e['id']})")
        return "\n".join(lines)

    except RuntimeError as exc:
        return str(exc)
    except Exception as exc:
        log.error(f"캘린더 검색 실패: {exc}", exc_info=True)
        return "일정 검색에 실패했어요."

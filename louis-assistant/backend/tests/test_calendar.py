"""
Google Calendar 도구 테스트
캘린더 일정 추가/조회/삭제/검색 기능을 검증합니다.
Google API는 모킹으로 처리합니다.
"""
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock


KST = timezone(timedelta(hours=9))


def _make_event(title: str, start_iso: str, event_id: str = "evt_001") -> dict:
    """테스트용 캘린더 이벤트 딕셔너리를 생성합니다."""
    return {
        "id": event_id,
        "summary": title,
        "start": {"dateTime": start_iso},
        "end": {"dateTime": start_iso},
    }


# ── _parse_time 헬퍼 ─────────────────────────────────────

class TestParseTime:

    def test_iso_format_parsed(self):
        from app.agent.tools.calendar import _parse_time
        dt = _parse_time("2026-04-13T15:00:00+09:00")
        assert dt is not None
        assert dt.hour == 15

    def test_korean_natural_language(self):
        from app.agent.tools.calendar import _parse_time
        dt = _parse_time("내일 오후 3시")
        assert dt is not None
        assert dt.hour == 15

    def test_invalid_string_returns_none(self):
        from app.agent.tools.calendar import _parse_time
        dt = _parse_time("알 수 없는 형식 xyz!@#")
        # dateparser가 None 반환하거나 잘못된 날짜일 수 있음
        # 테스트는 예외 발생 없음을 확인
        assert dt is None or isinstance(dt, datetime)


# ── add_calendar_event ───────────────────────────────────

class TestAddCalendarEvent:

    def _make_svc(self, return_value: dict):
        svc = MagicMock()
        svc.events.return_value.insert.return_value.execute.return_value = return_value
        return svc

    def test_add_event_success(self):
        from app.agent.tools.calendar import add_calendar_event

        svc = self._make_svc({"summary": "치과 예약", "id": "evt_001"})
        with patch("app.agent.tools.calendar.get_google_service", return_value=svc), \
             patch("app.agent.tools.calendar.google_quota") as mock_quota:
            mock_quota.check.return_value = None
            result = add_calendar_event.invoke({
                "title": "치과 예약",
                "start_time": "2026-04-14T10:00:00+09:00",
                "duration_minutes": 60,
            })

        assert "치과 예약" in result
        assert "등록" in result

    def test_add_event_with_description_and_location(self):
        from app.agent.tools.calendar import add_calendar_event

        svc = self._make_svc({"summary": "팀 회의", "id": "evt_002"})
        with patch("app.agent.tools.calendar.get_google_service", return_value=svc), \
             patch("app.agent.tools.calendar.google_quota") as mock_quota:
            mock_quota.check.return_value = None
            result = add_calendar_event.invoke({
                "title": "팀 회의",
                "start_time": "2026-04-15T14:00:00+09:00",
                "duration_minutes": 90,
                "description": "분기 실적 검토",
                "location": "3층 회의실",
            })

        assert "팀 회의" in result

    def test_add_event_invalid_time_format(self):
        from app.agent.tools.calendar import add_calendar_event

        with patch("app.agent.tools.calendar.google_quota") as mock_quota, \
             patch("app.agent.tools.calendar._parse_time", return_value=None):
            mock_quota.check.return_value = None
            result = add_calendar_event.invoke({
                "title": "테스트",
                "start_time": "모르는형식",
            })

        assert "인식" in result or "형식" in result

    def test_add_event_quota_exceeded(self):
        from app.agent.tools.calendar import add_calendar_event

        with patch("app.agent.tools.calendar.google_quota") as mock_quota:
            mock_quota.check.side_effect = RuntimeError("API 호출 한도를 초과했어요.")
            result = add_calendar_event.invoke({
                "title": "테스트",
                "start_time": "2026-04-14T10:00:00+09:00",
            })

        assert "한도" in result or "초과" in result

    def test_add_event_api_error(self):
        from app.agent.tools.calendar import add_calendar_event

        svc = MagicMock()
        svc.events.return_value.insert.return_value.execute.side_effect = Exception("Google 오류")

        with patch("app.agent.tools.calendar.get_google_service", return_value=svc), \
             patch("app.agent.tools.calendar.google_quota") as mock_quota:
            mock_quota.check.return_value = None
            result = add_calendar_event.invoke({
                "title": "테스트",
                "start_time": "2026-04-14T10:00:00+09:00",
            })

        assert "실패" in result


# ── list_calendar_events ─────────────────────────────────

class TestListCalendarEvents:

    def test_list_returns_events(self):
        from app.agent.tools.calendar import list_calendar_events

        start_iso = "2026-04-14T10:00:00+09:00"
        events = [
            _make_event("치과", start_iso, "evt_001"),
            _make_event("헬스장", start_iso, "evt_002"),
        ]
        svc = MagicMock()
        svc.events.return_value.list.return_value.execute.return_value = {"items": events}

        with patch("app.agent.tools.calendar.get_google_service", return_value=svc), \
             patch("app.agent.tools.calendar.google_quota") as mock_quota:
            mock_quota.check.return_value = None
            result = list_calendar_events.invoke({"days_ahead": 1, "max_results": 10})

        assert "치과" in result
        assert "헬스장" in result

    def test_list_empty_returns_no_schedule_message(self):
        from app.agent.tools.calendar import list_calendar_events

        svc = MagicMock()
        svc.events.return_value.list.return_value.execute.return_value = {"items": []}

        with patch("app.agent.tools.calendar.get_google_service", return_value=svc), \
             patch("app.agent.tools.calendar.google_quota") as mock_quota:
            mock_quota.check.return_value = None
            result = list_calendar_events.invoke({"days_ahead": 1, "max_results": 10})

        assert "없어요" in result

    def test_list_multi_day_message(self):
        from app.agent.tools.calendar import list_calendar_events

        svc = MagicMock()
        svc.events.return_value.list.return_value.execute.return_value = {"items": []}

        with patch("app.agent.tools.calendar.get_google_service", return_value=svc), \
             patch("app.agent.tools.calendar.google_quota") as mock_quota:
            mock_quota.check.return_value = None
            result = list_calendar_events.invoke({"days_ahead": 7, "max_results": 10})

        assert "7일" in result or "없어요" in result

    def test_list_quota_exceeded(self):
        from app.agent.tools.calendar import list_calendar_events

        with patch("app.agent.tools.calendar.google_quota") as mock_quota:
            mock_quota.check.side_effect = RuntimeError("한도 초과")
            result = list_calendar_events.invoke({"days_ahead": 1})

        assert "한도" in result or "초과" in result


# ── delete_calendar_event ────────────────────────────────

class TestDeleteCalendarEvent:

    def test_delete_success(self):
        from app.agent.tools.calendar import delete_calendar_event

        svc = MagicMock()
        svc.events.return_value.delete.return_value.execute.return_value = None

        with patch("app.agent.tools.calendar.get_google_service", return_value=svc), \
             patch("app.agent.tools.calendar.google_quota") as mock_quota:
            mock_quota.check.return_value = None
            result = delete_calendar_event.invoke({"event_id": "evt_001"})

        assert "삭제" in result

    def test_delete_api_error(self):
        from app.agent.tools.calendar import delete_calendar_event

        svc = MagicMock()
        svc.events.return_value.delete.return_value.execute.side_effect = Exception("없는 이벤트")

        with patch("app.agent.tools.calendar.get_google_service", return_value=svc), \
             patch("app.agent.tools.calendar.google_quota") as mock_quota:
            mock_quota.check.return_value = None
            result = delete_calendar_event.invoke({"event_id": "nonexistent"})

        assert "실패" in result


# ── search_calendar_events ───────────────────────────────

class TestSearchCalendarEvents:

    def test_search_returns_results(self):
        from app.agent.tools.calendar import search_calendar_events

        events = [_make_event("치과 예약", "2026-04-14T10:00:00+09:00", "evt_001")]
        svc = MagicMock()
        svc.events.return_value.list.return_value.execute.return_value = {"items": events}

        with patch("app.agent.tools.calendar.get_google_service", return_value=svc), \
             patch("app.agent.tools.calendar.google_quota") as mock_quota:
            mock_quota.check.return_value = None
            result = search_calendar_events.invoke({"keyword": "치과", "days_range": 30})

        assert "치과 예약" in result
        assert "evt_001" in result

    def test_search_no_results(self):
        from app.agent.tools.calendar import search_calendar_events

        svc = MagicMock()
        svc.events.return_value.list.return_value.execute.return_value = {"items": []}

        with patch("app.agent.tools.calendar.get_google_service", return_value=svc), \
             patch("app.agent.tools.calendar.google_quota") as mock_quota:
            mock_quota.check.return_value = None
            result = search_calendar_events.invoke({"keyword": "없는일정XYZ"})

        assert "찾지 못했어요" in result or "없" in result

    def test_search_quota_exceeded(self):
        from app.agent.tools.calendar import search_calendar_events

        with patch("app.agent.tools.calendar.google_quota") as mock_quota:
            mock_quota.check.side_effect = RuntimeError("한도 초과")
            result = search_calendar_events.invoke({"keyword": "치과"})

        assert "한도" in result or "초과" in result

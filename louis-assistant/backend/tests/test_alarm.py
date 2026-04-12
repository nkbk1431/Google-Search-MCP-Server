"""
알람 도구 테스트
실행: pytest tests/test_alarm.py -v
"""
from unittest.mock import patch, MagicMock

import pytest


def test_set_alarm_hhmm_format():
    """HH:MM 형식 알람 설정."""
    with patch("app.agent.tools.alarm._scheduler") as mock_sched:
        mock_sched.add_job = MagicMock()
        from app.agent.tools.alarm import set_alarm
        result = set_alarm.invoke({"time_str": "07:30", "label": "기상"})
        assert "07시 30분" in result or "기상" in result
        assert mock_sched.add_job.called


def test_set_alarm_invalid_time():
    """인식 불가 시간 문자열 처리."""
    with patch("app.utils.date_utils.parse_natural_datetime", return_value=None):
        from app.agent.tools.alarm import set_alarm
        result = set_alarm.invoke({"time_str": "알수없는시간", "label": "테스트"})
        assert "인식하지 못했어요" in result


def test_set_alarm_repeat_daily():
    """매일 반복 알람 설정."""
    with patch("app.agent.tools.alarm._scheduler") as mock_sched:
        mock_sched.add_job = MagicMock()
        from app.agent.tools.alarm import set_alarm
        result = set_alarm.invoke({"time_str": "07:00", "label": "아침 알람", "repeat_daily": True})
        assert "매일" in result
        # cron 트리거로 등록되었는지 확인
        call_kwargs = mock_sched.add_job.call_args
        assert call_kwargs[0][1] == "cron"


def test_cancel_alarm_not_found():
    """없는 알람 취소."""
    with patch("app.agent.tools.alarm._scheduler") as mock_sched:
        mock_sched.get_jobs = MagicMock(return_value=[])
        from app.agent.tools.alarm import cancel_alarm
        result = cancel_alarm.invoke({"label": "없는알람"})
        assert "찾지 못했어요" in result


def test_list_alarms_empty():
    """등록된 알람 없을 때."""
    with patch("app.agent.tools.alarm._scheduler") as mock_sched:
        mock_sched.get_jobs = MagicMock(return_value=[])
        from app.agent.tools.alarm import list_alarms
        result = list_alarms.invoke({})
        assert "없어요" in result

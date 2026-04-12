"""
루이스 개인비서 - 알람 도구
특정 시각(매일 반복 포함)에 기상 알람을 등록합니다.
APScheduler의 cron 트리거로 반복 알람을 지원합니다.
"""
import logging

from langchain_core.tools import tool

from app.agent.tools.reminder import _scheduler, _notify
from app.utils.date_utils import parse_natural_datetime, format_kst, next_occurrence

log = logging.getLogger("louis.tools.alarm")


@tool
def set_alarm(time_str: str, label: str = "알람", repeat_daily: bool = False) -> str:
    """알람을 등록합니다.

    Args:
        time_str: 알람 시각 (자연어 또는 ISO 8601, 예: '내일 오전 7시', '07:30')
        label: 알람 이름. 기본값 '알람'.
        repeat_daily: True면 매일 반복. False면 1회성.

    Returns:
        등록 결과 메시지
    """
    try:
        # "07:30" 형태 처리
        if ":" in time_str and len(time_str) <= 5:
            h, m = map(int, time_str.split(":"))
            trigger_dt = next_occurrence(h, m)
        else:
            trigger_dt = parse_natural_datetime(time_str)
            if trigger_dt is None:
                return f"시간 형식을 인식하지 못했어요. '내일 오전 7시' 또는 '07:30' 형식으로 말씀해주세요."

        job_id = f"alarm-{label}-{trigger_dt.strftime('%H%M')}"

        if repeat_daily:
            _scheduler.add_job(
                _notify,
                "cron",
                hour=trigger_dt.hour,
                minute=trigger_dt.minute,
                id=job_id,
                replace_existing=True,
                args=[label],
            )
            return f"매일 {trigger_dt.strftime('%H시 %M분')}에 '{label}' 알람 설정했어요."
        else:
            _scheduler.add_job(
                _notify,
                "date",
                run_date=trigger_dt,
                id=job_id,
                replace_existing=True,
                args=[label],
            )
            return f"{format_kst(trigger_dt)}에 '{label}' 알람 설정했어요."

    except Exception as exc:
        log.error(f"알람 등록 실패: {exc}", exc_info=True)
        return "알람 등록에 실패했어요."


@tool
def cancel_alarm(label: str) -> str:
    """등록된 알람을 취소합니다.

    Args:
        label: 취소할 알람 이름

    Returns:
        취소 결과 메시지
    """
    try:
        removed = []
        for job in _scheduler.get_jobs():
            if label in job.id:
                job.remove()
                removed.append(job.id)

        if not removed:
            return f"'{label}' 알람을 찾지 못했어요."
        return f"'{label}' 알람을 취소했어요."
    except Exception as exc:
        log.error(f"알람 취소 실패: {exc}", exc_info=True)
        return "알람 취소에 실패했어요."


@tool
def list_alarms() -> str:
    """등록된 알람 목록을 조회합니다."""
    try:
        jobs = [j for j in _scheduler.get_jobs() if "alarm-" in j.id]
        if not jobs:
            return "등록된 알람이 없어요."
        lines = []
        for j in jobs:
            next_run = j.next_run_time
            next_str = format_kst(next_run) if next_run else "시간 미정"
            lines.append(f"- {j.id.replace('alarm-', '')} ({next_str})")
        return "\n".join(lines)
    except Exception as exc:
        log.error(f"알람 목록 조회 실패: {exc}", exc_info=True)
        return "알람 목록 조회에 실패했어요."

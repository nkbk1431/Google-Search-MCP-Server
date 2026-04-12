"""
루이스 개인비서 - 리마인더 / 타이머 도구
APScheduler를 사용하여 n분 뒤 또는 특정 시각에 알림을 등록합니다.
"""
import logging
import threading
from datetime import datetime, timedelta

import dateparser
from apscheduler.schedulers.background import BackgroundScheduler
from langchain_core.tools import tool

log = logging.getLogger("louis.tools.reminder")

_scheduler = BackgroundScheduler(timezone="Asia/Seoul")
_scheduler.start()

# 알림 콜백: 실제 배포 시 FCM 푸시로 교체
_reminder_callbacks: list = []


def register_reminder_callback(fn):
    """알림 발생 시 호출될 콜백 함수 등록."""
    _reminder_callbacks.append(fn)


def _fire(content: str, reminder_id: str):
    log.info(f"[리마인더] {reminder_id}: {content}")
    for cb in _reminder_callbacks:
        try:
            cb(content=content, reminder_id=reminder_id)
        except Exception as exc:
            log.warning(f"콜백 실패: {exc}")


def _set_timer_direct(total_seconds: int, label: str) -> str:
    """LLM 없이 타이머를 직접 설정합니다 (router에서 호출)."""
    trigger = datetime.now() + timedelta(seconds=total_seconds)
    rid = f"timer-{trigger.timestamp():.0f}"
    _scheduler.add_job(_fire, "date", run_date=trigger, args=[label, rid], id=rid)
    return f"{label} 시작 ({trigger.strftime('%H시 %M분')}에 알림)"


@tool
def set_reminder(content: str, minutes_later: int) -> str:
    """n분 뒤에 알려주는 리마인더를 등록합니다.

    Args:
        content: 알림 내용
        minutes_later: 몇 분 뒤에 알릴지

    Returns:
        등록 결과 메시지
    """
    try:
        if minutes_later <= 0:
            return "시간을 1분 이상으로 설정해주세요."
        trigger = datetime.now() + timedelta(minutes=minutes_later)
        rid = f"reminder-{trigger.timestamp():.0f}"
        _scheduler.add_job(_fire, "date", run_date=trigger, args=[content, rid], id=rid)
        return f"{minutes_later}분 뒤 '{content}' 알려드릴게요."
    except Exception as exc:
        log.error(f"리마인더 등록 실패: {exc}", exc_info=True)
        return "리마인더 등록에 실패했어요."


@tool
def set_reminder_at(content: str, at_time: str) -> str:
    """특정 시각에 리마인더를 등록합니다.

    Args:
        content: 알림 내용
        at_time: 알림 시각 (ISO 8601 또는 자연어, 예: '내일 오전 7시')

    Returns:
        등록 결과 메시지
    """
    try:
        settings_dp = {
            "PREFER_DATES_FROM": "future",
            "TIMEZONE": "Asia/Seoul",
            "RETURN_AS_TIMEZONE_AWARE": False,
        }
        trigger = dateparser.parse(at_time, settings=settings_dp, languages=["ko", "en"])
        if trigger is None:
            try:
                trigger = datetime.fromisoformat(at_time)
            except ValueError:
                return f"시간 형식을 인식하지 못했어요: {at_time}"

        if trigger < datetime.now():
            return "과거 시간으로는 리마인더를 설정할 수 없어요."

        rid = f"reminder-{trigger.timestamp():.0f}"
        _scheduler.add_job(_fire, "date", run_date=trigger, args=[content, rid], id=rid)
        return f"{trigger.strftime('%m월 %d일 %H시 %M분')}에 '{content}' 알려드릴게요."
    except Exception as exc:
        log.error(f"리마인더 등록 실패: {exc}", exc_info=True)
        return "리마인더 등록에 실패했어요."


def shutdown_scheduler():
    """앱 종료 시 스케줄러를 정상 종료합니다."""
    if _scheduler.running:
        _scheduler.shutdown(wait=False)

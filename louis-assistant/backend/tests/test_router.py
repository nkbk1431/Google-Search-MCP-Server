"""
의도 분류 라우터 테스트
실행: pytest tests/test_router.py -v
"""
import pytest

from app.agent.router import classify_intent, Intent


def test_weather_intent():
    result = classify_intent("오늘 날씨 어때?")
    assert result.intent == Intent.WEATHER


def test_weather_outfit():
    result = classify_intent("오늘 뭐 입을까?")
    assert result.intent == Intent.WEATHER


def test_calendar_intent():
    result = classify_intent("내일 오후 3시 치과 예약 추가해줘")
    assert result.intent == Intent.CALENDAR


def test_reminder_intent():
    result = classify_intent("30분 뒤에 빨래 알려줘")
    assert result.intent in (Intent.REMINDER, Intent.TIMER)


def test_timer_no_llm():
    """타이머는 명확한 분 수가 있을 때 LLM 불필요."""
    result = classify_intent("5분 타이머 설정해줘")
    assert result.intent == Intent.TIMER
    if result.extracted.get("minutes"):
        assert result.needs_llm is False


def test_todo_intent():
    result = classify_intent("장보기 목록에 우유 추가해줘")
    assert result.intent == Intent.TODO


def test_memo_intent():
    result = classify_intent("아이디어 메모해줘")
    assert result.intent == Intent.MEMO


def test_finance_intent():
    result = classify_intent("100달러 얼마야?")
    assert result.intent == Intent.FINANCE
    assert result.extracted.get("currency") == "USD"
    assert result.extracted.get("amount") == 100.0


def test_translate_intent():
    result = classify_intent("안녕을 영어로 뭐야?")
    assert result.intent == Intent.TRANSLATE


def test_general_fallback():
    result = classify_intent("오늘 기분이 좀 별로야")
    assert result.intent == Intent.GENERAL
    assert result.needs_llm is True


def test_korean_city_extracted():
    result = classify_intent("부산 날씨 알려줘")
    assert result.extracted.get("city") == "부산"

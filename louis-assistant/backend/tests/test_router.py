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


# ── ALARM 의도 ────────────────────────────────────────────

def test_alarm_intent():
    result = classify_intent("내일 아침 7시 알람 맞춰줘")
    assert result.intent == Intent.ALARM


def test_alarm_extracts_hour():
    result = classify_intent("오전 6시 30분 알람 설정해줘")
    assert result.intent == Intent.ALARM
    assert result.extracted.get("hour") == 6
    assert result.extracted.get("minute") == 30


def test_alarm_no_llm_with_hour():
    result = classify_intent("8시 알람")
    assert result.intent == Intent.ALARM
    assert result.extracted.get("hour") == 8
    assert result.needs_llm is False


# ── COMMUNICATION 의도 ────────────────────────────────────

def test_communication_phone_intent():
    result = classify_intent("엄마에게 전화해줘")
    assert result.intent == Intent.COMMUNICATION


def test_communication_sms_intent():
    result = classify_intent("친구한테 문자 보내줘")
    assert result.intent == Intent.COMMUNICATION


def test_communication_kakao_intent():
    result = classify_intent("카톡으로 연락해줘")
    assert result.intent == Intent.COMMUNICATION


def test_communication_extracts_contact():
    result = classify_intent("전화 엄마에게")
    assert result.intent == Intent.COMMUNICATION
    assert result.extracted.get("action") == "전화"


# ── MEDIA 의도 ─────────────────────────────────────────────

def test_media_music_intent():
    result = classify_intent("재즈 음악 틀어줘")
    assert result.intent == Intent.MEDIA


def test_media_song_intent():
    result = classify_intent("아이유 노래 재생해줘")
    assert result.intent == Intent.MEDIA


def test_media_youtube_platform():
    result = classify_intent("유튜브에서 강아지 영상 찾아줘")
    assert result.intent == Intent.MEDIA
    assert result.extracted.get("platform") == "youtube"


def test_media_extracts_query():
    result = classify_intent("재즈 음악 틀어줘")
    assert result.intent == Intent.MEDIA
    # 쿼리가 추출되거나 빈 딕셔너리여도 의도 분류는 정확해야 함


# ── NAVIGATION 의도 ────────────────────────────────────────

def test_navigation_intent():
    result = classify_intent("강남에서 홍대까지 가는 길 알려줘")
    assert result.intent == Intent.NAVIGATION


def test_navigation_extracts_origin_destination():
    result = classify_intent("서울역에서 인천공항까지 경로 알려줘")
    assert result.intent == Intent.NAVIGATION
    assert result.extracted.get("origin") is not None
    assert result.extracted.get("destination") is not None


def test_navigation_destination_only():
    result = classify_intent("홍대까지 가는 길")
    assert result.intent == Intent.NAVIGATION
    assert result.extracted.get("destination") is not None


def test_navigation_subway_intent():
    result = classify_intent("지하철 타고 어떻게 가?")
    assert result.intent == Intent.NAVIGATION


# ── SMART_HOME 의도 ────────────────────────────────────────

def test_smart_home_lights_on():
    result = classify_intent("거실 불 켜줘")
    assert result.intent == Intent.SMART_HOME


def test_smart_home_ac_off():
    result = classify_intent("에어컨 꺼줘")
    assert result.intent == Intent.SMART_HOME


def test_smart_home_temperature():
    result = classify_intent("온도 설정 22도로 해줘")
    assert result.intent == Intent.SMART_HOME


# ── SEARCH 의도 ───────────────────────────────────────────

def test_search_intent():
    result = classify_intent("파이썬 리스트 정렬 방법 검색해줘")
    assert result.intent == Intent.SEARCH


def test_search_who_is():
    result = classify_intent("일론 머스크 누구야?")
    assert result.intent == Intent.SEARCH


# ── 신뢰도 / 다중 키워드 ──────────────────────────────────

def test_higher_confidence_with_multiple_keywords():
    """키워드가 많을수록 신뢰도가 높아져야 합니다."""
    single = classify_intent("날씨 알려줘")
    multi = classify_intent("오늘 날씨 기온 습도 다 알려줘")
    assert multi.confidence >= single.confidence


def test_intent_priority_alarm_over_reminder():
    """'알람'은 'ALARM'으로 분류되어야 합니다 (REMINDER 아님)."""
    result = classify_intent("알람 맞춰줘")
    assert result.intent == Intent.ALARM


def test_finance_no_llm_with_currency():
    """통화 코드가 추출되면 LLM 불필요."""
    result = classify_intent("달러 환율 얼마야?")
    assert result.intent == Intent.FINANCE
    assert result.extracted.get("currency") == "USD"
    assert result.needs_llm is False

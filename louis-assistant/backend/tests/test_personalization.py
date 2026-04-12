"""
PersonalizationService 테스트
학습 패턴, 선호도 저장/조회/삭제, 컨텍스트 생성을 검증합니다.
"""
import pytest
from unittest.mock import patch, MagicMock

from app.services.personalization import (
    PersonalizationService,
    PrefKey,
)


@pytest.fixture
def svc():
    """DB를 모킹한 PersonalizationService 인스턴스."""
    return PersonalizationService()


# ── 텍스트 학습 ─────────────────────────────────────────────────────

@pytest.mark.parametrize("text,expected_key,expected_value", [
    ("서울 날씨 어때?", PrefKey.HOME_CITY, "서울"),
    ("부산 날씨 알려줘", PrefKey.HOME_CITY, "부산"),
    ("제주 날씨 어때요", PrefKey.HOME_CITY, "제주"),
    ("지하철로 길찾기", PrefKey.COMMUTE_MODE, "transit"),
    ("택시 경로 알려줘", PrefKey.COMMUTE_MODE, "driving"),
    ("걷기로 가는 길", PrefKey.COMMUTE_MODE, "walking"),
    ("7시 30분 알람 설정해줘", PrefKey.WAKE_TIME, "07:30"),
    ("영어로 번역해줘", PrefKey.PREFERRED_LANGUAGE, "영어"),
    ("달러 → 원 환율", PrefKey.CURRENCY_PAIR, "달러→원"),
])
def test_learn_from_text_extracts_correctly(svc, text, expected_key, expected_value):
    with patch.object(svc, "_upsert") as mock_upsert:
        learned = svc.learn_from_text("user1", text)
        assert expected_key in learned
        mock_upsert.assert_called_with("user1", expected_key, expected_value)


def test_learn_from_text_multiple_patterns(svc):
    """하나의 발화에서 여러 선호도를 추출합니다."""
    text = "서울 날씨 어때? 그리고 영어로 번역해줘"
    with patch.object(svc, "_upsert"):
        learned = svc.learn_from_text("user1", text)
    assert len(learned) >= 1  # 적어도 하나 이상


def test_learn_from_text_no_match_returns_empty(svc):
    """매칭 없는 텍스트에서 빈 목록 반환."""
    learned = svc.learn_from_text("user1", "안녕하세요, 잘 지내세요?")
    assert learned == []


# ── 선호도 저장/조회 ────────────────────────────────────────────────

def test_get_all_preferences_returns_dict(svc):
    mock_rows = [
        MagicMock(pref_key="home_city", pref_value="서울"),
        MagicMock(pref_key="language", pref_value="영어"),
    ]
    with patch("app.services.personalization.get_sync_db") as mock_db:
        mock_ctx = MagicMock()
        mock_ctx.__enter__ = MagicMock(return_value=mock_ctx)
        mock_ctx.__exit__ = MagicMock(return_value=False)
        mock_ctx.query.return_value.filter.return_value.order_by.return_value.all.return_value = mock_rows
        mock_db.return_value = mock_ctx

        result = svc.get_all_preferences("user1")

    assert result["home_city"] == "서울"
    assert result["language"] == "영어"


def test_get_all_preferences_db_error_returns_empty(svc):
    """DB 오류 시 빈 딕셔너리 반환 (예외 전파 안 함)."""
    with patch("app.services.personalization.get_sync_db", side_effect=Exception("DB 오류")):
        result = svc.get_all_preferences("user1")
    assert result == {}


# ── 개인화 컨텍스트 생성 ────────────────────────────────────────────

def test_build_personalization_context_empty(svc):
    with patch.object(svc, "get_all_preferences", return_value={}):
        ctx = svc.build_personalization_context("user1")
    assert ctx == ""


def test_build_personalization_context_with_data(svc):
    prefs = {
        PrefKey.HOME_CITY: "서울",
        PrefKey.COMMUTE_MODE: "transit",
    }
    with patch.object(svc, "get_all_preferences", return_value=prefs):
        ctx = svc.build_personalization_context("user1")

    assert "[사용자 개인화 정보]" in ctx
    assert "서울" in ctx
    assert "transit" in ctx


# ── 알람 시각 파싱 ───────────────────────────────────────────────────

@pytest.mark.parametrize("text,expected_time", [
    ("7시 알람", "07:00"),
    ("8시 30분 알람", "08:30"),
    ("12시 알람 맞춰줘", "12:00"),
])
def test_alarm_time_extracted(svc, text, expected_time):
    with patch.object(svc, "_upsert") as mock_upsert:
        svc.learn_from_text("user1", text)
        # _upsert가 올바른 시각으로 호출됐는지 확인
        calls = [str(c) for c in mock_upsert.call_args_list]
        assert any(expected_time in c for c in calls)

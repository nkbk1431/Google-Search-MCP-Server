"""
ConversationSummarizer 테스트
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from langchain_core.messages import HumanMessage, AIMessage

from app.agent.summarizer import (
    ConversationSummarizer,
    SUMMARIZE_THRESHOLD,
    KEEP_RECENT,
    _format_messages,
    _extract_text,
)


@pytest.fixture
def summarizer():
    return ConversationSummarizer()


# ── 턴 카운터 ──────────────────────────────────────────────────────

def test_increment_turn_starts_at_zero(summarizer):
    assert summarizer.increment_turn("s1") == 1


def test_increment_turn_accumulates(summarizer):
    for i in range(5):
        count = summarizer.increment_turn("s2")
    assert count == 5


def test_should_summarize_false_below_threshold(summarizer):
    for _ in range(SUMMARIZE_THRESHOLD - 1):
        summarizer.increment_turn("s3")
    assert summarizer.should_summarize("s3") is False


def test_should_summarize_true_at_threshold(summarizer):
    for _ in range(SUMMARIZE_THRESHOLD):
        summarizer.increment_turn("s4")
    assert summarizer.should_summarize("s4") is True


def test_should_summarize_true_at_multiples(summarizer):
    for _ in range(SUMMARIZE_THRESHOLD * 2):
        summarizer.increment_turn("s5")
    assert summarizer.should_summarize("s5") is True


# ── 요약 없는 상태 ────────────────────────────────────────────────────

def test_get_summary_none_initially(summarizer):
    assert summarizer.get_summary("unknown") is None


def test_build_summary_context_empty(summarizer):
    assert summarizer.build_summary_context("unknown") == ""


# ── 요약 생성 ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_summarize_if_needed_not_triggered(summarizer):
    """임계값 미만이면 None 반환."""
    messages = [HumanMessage(content="안녕"), AIMessage(content="안녕하세요")]
    summarizer.increment_turn("s6")  # threshold 미만
    result = await summarizer.summarize_if_needed("s6", messages)
    assert result is None


@pytest.mark.asyncio
async def test_summarize_if_needed_creates_summary(summarizer):
    """임계값 도달 시 LLM 호출 후 요약 저장."""
    session = "s7"
    for _ in range(SUMMARIZE_THRESHOLD):
        summarizer.increment_turn(session)

    # 충분한 메시지 (KEEP_RECENT 초과)
    messages = [
        HumanMessage(content=f"질문 {i}") if i % 2 == 0 else AIMessage(content=f"답변 {i}")
        for i in range(KEEP_RECENT + 4)
    ]

    fake_summary = "사용자는 날씨를 여러 번 물었습니다."
    mock_response = MagicMock()
    mock_response.content = fake_summary

    with patch.object(summarizer._llm, "ainvoke", new=AsyncMock(return_value=mock_response)):
        result = await summarizer.summarize_if_needed(session, messages)

    assert result == fake_summary
    assert summarizer.get_summary(session) == fake_summary


@pytest.mark.asyncio
async def test_summarize_merges_with_previous(summarizer):
    """기존 요약이 있으면 새 요약과 합칩니다."""
    session = "s8"
    summarizer._summaries[session] = {
        "summary": "이전 요약",
        "turn_count": 10,
        "updated_at": None,
    }
    for _ in range(SUMMARIZE_THRESHOLD):
        summarizer.increment_turn(session)

    messages = [
        HumanMessage(content=f"메시지 {i}") for i in range(KEEP_RECENT + 2)
    ]

    mock_response = MagicMock()
    mock_response.content = "새 요약"

    with patch.object(summarizer._llm, "ainvoke", new=AsyncMock(return_value=mock_response)):
        result = await summarizer.summarize_if_needed(session, messages)

    assert "이전 요약" in result
    assert "새 요약" in result


@pytest.mark.asyncio
async def test_summarize_handles_llm_error(summarizer):
    """LLM 오류 시 None을 반환하고 예외를 전파하지 않습니다."""
    session = "s9"
    for _ in range(SUMMARIZE_THRESHOLD):
        summarizer.increment_turn(session)
    messages = [HumanMessage(content=f"msg {i}") for i in range(KEEP_RECENT + 2)]

    with patch.object(summarizer._llm, "ainvoke", new=AsyncMock(side_effect=Exception("API 오류"))):
        result = await summarizer.summarize_if_needed(session, messages)

    assert result is None


# ── 헬퍼 함수 ─────────────────────────────────────────────────────────

def test_format_messages():
    msgs = [
        HumanMessage(content="안녕"),
        AIMessage(content="안녕하세요"),
    ]
    text = _format_messages(msgs)
    assert "사용자: 안녕" in text
    assert "루이스: 안녕하세요" in text


def test_extract_text_string():
    msg = HumanMessage(content="텍스트")
    assert _extract_text(msg) == "텍스트"


def test_extract_text_list():
    msg = HumanMessage(content=[{"type": "text", "text": "블록 텍스트"}])
    assert _extract_text(msg) == "블록 텍스트"


def test_clear_removes_session_data(summarizer):
    summarizer._summaries["s10"] = {"summary": "요약", "turn_count": 10, "updated_at": None}
    summarizer._turn_counts["s10"] = 10
    summarizer.clear("s10")
    assert summarizer.get_summary("s10") is None
    assert summarizer._turn_counts.get("s10") is None

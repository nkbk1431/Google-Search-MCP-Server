"""
Agent 오케스트레이터 테스트 (Mock LLM 사용, 실제 API 호출 없음)
실행: pytest tests/test_orchestrator.py -v
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from app.agent.router import classify_intent, Intent


# ── 라우터 레벨 테스트 (orchestrator 의존성 없이) ──────────────────

def test_router_weather():
    result = classify_intent("서울 날씨 어때?")
    assert result.intent == Intent.WEATHER
    assert result.confidence >= 0.6


def test_router_calendar():
    result = classify_intent("다음 주 수요일 미팅 일정 추가해줘")
    assert result.intent == Intent.CALENDAR
    assert result.needs_llm is True


def test_router_timer_direct():
    """타이머 명확 → LLM 불필요."""
    result = classify_intent("10분 타이머")
    assert result.intent == Intent.TIMER
    if result.extracted.get("minutes") == 10:
        assert result.needs_llm is False


def test_router_finance():
    result = classify_intent("50달러 원화로 변환해줘")
    assert result.intent == Intent.FINANCE


def test_router_general_fallback():
    result = classify_intent("오늘 하루 힘들었어")
    assert result.intent == Intent.GENERAL
    assert result.needs_llm is True


# ── 오케스트레이터 Mock 테스트 ─────────────────────────────────────

@pytest.mark.asyncio
async def test_chat_returns_reply():
    """Agent.chat이 reply 키를 포함한 dict를 반환하는지 확인."""
    with patch("app.agent.orchestrator.LouisAgent._invoke_agent") as mock_invoke:
        mock_invoke.return_value = {
            "reply": "서울 현재 18도, 맑아요.",
            "tool_calls": [{"tool": "get_weather", "args": {"city": "Seoul"}}],
            "tokens": {"in": 100, "out": 50},
        }

        from app.agent.orchestrator import LouisAgent
        with patch.object(LouisAgent, "__init__", lambda self: None):
            agent = LouisAgent.__new__(LouisAgent)
            agent._memory = MagicMock()
            agent._haiku = MagicMock()
            agent._sonnet = MagicMock()
            agent._tools = []
            agent._agent = MagicMock()
            agent._agent_sonnet = MagicMock()

            result = await agent.chat("서울 날씨 알려줘", "test-session", "user-1")

        assert "reply" in result
        assert isinstance(result["reply"], str)


@pytest.mark.asyncio
async def test_daily_limit_exceeded():
    """일일 토큰 한도 초과 시 적절한 메시지 반환."""
    from app.agent import orchestrator as orch_module
    from app.agent.prompts import DAILY_LIMIT_REPLY

    # 토큰 한도 초과 상태로 설정
    orch_module._session_tokens["limit-user:9999-01-01"] = {
        "in": 999_999,
        "out": 999_999,
    }

    with patch("app.agent.orchestrator.LouisAgent._invoke_agent") as mock_invoke:
        from app.agent.orchestrator import LouisAgent
        with patch.object(LouisAgent, "__init__", lambda self: None):
            agent = LouisAgent.__new__(LouisAgent)
            agent._memory = MagicMock()
            agent._haiku = MagicMock()
            agent._sonnet = MagicMock()
            agent._tools = []
            agent._agent = MagicMock()
            agent._agent_sonnet = MagicMock()

            # 오늘 날짜 키로 한도 설정
            from datetime import datetime
            today = datetime.now().date().isoformat()
            orch_module._session_tokens[f"limit-user:{today}"] = {
                "in": 999_999,
                "out": 999_999,
            }

            result = await agent.chat("날씨 알려줘", "s1", "limit-user")

        assert result["reply"] == DAILY_LIMIT_REPLY
        mock_invoke.assert_not_called()


@pytest.mark.asyncio
async def test_retry_on_failure():
    """Agent 호출 실패 시 재시도 후 에러 메시지 반환."""
    from app.agent.orchestrator import LouisAgent
    from app.agent.prompts import ERROR_REPLY

    with patch("app.agent.orchestrator.LouisAgent._invoke_agent", side_effect=Exception("API Error")):
        with patch("asyncio.sleep", new_callable=AsyncMock):
            with patch.object(LouisAgent, "__init__", lambda self: None):
                agent = LouisAgent.__new__(LouisAgent)
                agent._memory = MagicMock()
                agent._haiku = MagicMock()
                agent._sonnet = MagicMock()
                agent._tools = []
                agent._agent = MagicMock()
                agent._agent_sonnet = MagicMock()

                result = await agent.chat("테스트", "s1", "user-retry")

            assert result["reply"] == ERROR_REPLY

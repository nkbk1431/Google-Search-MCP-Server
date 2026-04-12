"""
루이스 개인비서 - LangGraph Agent 오케스트레이터
LangGraph의 create_react_agent를 기반으로 멀티스텝 추론 + 도구 호출을 관리합니다.
"""
import asyncio
import logging
from datetime import datetime
from typing import Any

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

from app.config import settings
from app.agent.prompts import (
    get_system_prompt,
    OFFLINE_REPLY,
    DAILY_LIMIT_REPLY,
    ERROR_REPLY,
)
from app.agent.summarizer import ConversationSummarizer
from app.services.personalization import get_personalization_service
from app.agent.router import classify_intent, Intent
from app.agent.tools.weather import get_weather, recommend_outfit
from app.agent.tools.calendar import (
    add_calendar_event, list_calendar_events,
    delete_calendar_event, search_calendar_events,
)
from app.agent.tools.reminder import set_reminder, set_reminder_at
from app.agent.tools.todo import add_todo, list_todos, complete_todo
from app.agent.tools.memo import add_memo, search_memo, list_memos
from app.agent.tools.finance import convert_currency, get_stock_price
from app.agent.tools.translate import translate_text
from app.agent.tools.search import web_search
from app.agent.tools.alarm import set_alarm, cancel_alarm, list_alarms
from app.agent.tools.navigation import get_directions
from app.agent.tools.communication import send_email, get_phone_intent, get_sms_intent
from app.agent.tools.media import search_music, search_youtube
from app.agent.tools.smart_home import control_smart_home

log = logging.getLogger("louis.orchestrator")

# 세션별 토큰 사용량 추적
_session_tokens: dict[str, dict[str, int]] = {}


class LouisAgent:
    """
    루이스 Agent 오케스트레이터.

    사용 예시:
        agent = LouisAgent()
        result = await agent.chat("오늘 날씨 어때?", session_id="user-1")
        print(result["reply"])
    """

    def __init__(self):
        self._memory = MemorySaver()
        self._haiku = self._build_llm(settings.llm_default_model)
        self._sonnet = self._build_llm(settings.llm_complex_model)
        self._tools = self._load_tools()
        self._agent = self._build_agent(self._haiku)
        self._agent_sonnet = self._build_agent(self._sonnet)
        self._summarizer = ConversationSummarizer()
        self._personalization = get_personalization_service()
        log.info(f"LouisAgent 초기화 완료. 기본모델={settings.llm_default_model}")

    def _build_llm(self, model: str) -> ChatAnthropic:
        return ChatAnthropic(
            model=model,
            api_key=settings.anthropic_api_key,
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
        )

    def _load_tools(self) -> list:
        return [
            get_weather, recommend_outfit,
            add_calendar_event, list_calendar_events,
            delete_calendar_event, search_calendar_events,
            set_reminder, set_reminder_at,
            set_alarm, cancel_alarm, list_alarms,
            add_todo, list_todos, complete_todo,
            add_memo, search_memo, list_memos,
            convert_currency, get_stock_price,
            translate_text,
            web_search,
            get_directions,
            send_email, get_phone_intent, get_sms_intent,
            search_music, search_youtube,
            control_smart_home,
        ]

    def _build_agent(self, llm: ChatAnthropic):
        system_prompt = get_system_prompt()
        return create_react_agent(
            llm,
            self._tools,
            prompt=system_prompt,
            checkpointer=self._memory,
        )

    async def chat(
        self,
        user_text: str,
        session_id: str,
        user_id: str = "default",
    ) -> dict[str, Any]:
        """
        사용자 발화를 처리하고 응답을 반환합니다.

        Args:
            user_text: 사용자 발화 텍스트
            session_id: 대화 세션 ID (컨텍스트 유지)
            user_id: 사용자 ID (토큰 한도 관리)

        Returns:
            dict with keys: reply(str), tool_calls(list), tokens(dict)
        """
        # 일일 토큰 한도 확인
        if self._is_over_daily_limit(user_id):
            return {"reply": DAILY_LIMIT_REPLY, "tool_calls": [], "tokens": {}}

        # 1차 의도 분류 (LLM 없이)
        route = classify_intent(user_text)
        log.info(f"[{session_id}] 의도={route.intent.value} 신뢰도={route.confidence:.2f} LLM={route.needs_llm}")

        # LLM 없이 처리 가능한 경우
        if not route.needs_llm:
            reply = self._handle_without_llm(route, user_text)
            if reply:
                return {"reply": reply, "tool_calls": [], "tokens": {"in": 0, "out": 0}}

        # 복잡한 의도는 Sonnet으로 에스컬레이션
        use_sonnet = route.intent in (Intent.GENERAL,) and len(user_text) > 100
        agent = self._agent_sonnet if use_sonnet else self._agent

        # 사용자 발화에서 선호도 학습 (비동기 불필요 — 빠른 regex)
        self._personalization.learn_from_text(user_id, user_text)

        # 턴 카운터 증가 및 요약 컨텍스트 준비
        self._summarizer.increment_turn(session_id)
        summary_ctx = self._summarizer.build_summary_context(session_id)

        # 개인화 컨텍스트 추가
        personal_ctx = self._personalization.build_personalization_context(user_id)
        if personal_ctx:
            summary_ctx = personal_ctx + summary_ctx

        # LangGraph Agent 호출
        for attempt in range(3):
            try:
                result = await self._invoke_agent(agent, user_text, session_id, summary_ctx)
                self._record_tokens(user_id, session_id, result.get("tokens", {}))

                # 요약 필요 여부 확인 후 백그라운드로 요약 수행
                if self._summarizer.should_summarize(session_id):
                    asyncio.create_task(
                        self._run_summarization(session_id, agent)
                    )

                # 긴 응답 요약
                reply = result["reply"]
                if len(reply) > 200:
                    reply = reply[:200].rsplit(" ", 1)[0] + "..."

                return result
            except Exception as exc:
                wait = 2 ** attempt
                log.warning(f"Agent 호출 실패 (시도 {attempt+1}/3): {exc}. {wait}초 후 재시도")
                if attempt < 2:
                    await asyncio.sleep(wait)
                else:
                    log.error(f"Agent 최종 실패: {exc}", exc_info=True)
                    return {"reply": ERROR_REPLY, "tool_calls": [], "tokens": {}}

        return {"reply": ERROR_REPLY, "tool_calls": [], "tokens": {}}

    async def _run_summarization(self, session_id: str, agent) -> None:
        """백그라운드에서 대화 요약을 실행합니다."""
        try:
            # MemorySaver에서 현재 메시지 목록 추출
            state = await agent.aget_state(
                config={"configurable": {"thread_id": session_id}}
            )
            messages = state.values.get("messages", []) if state else []
            if messages:
                await self._summarizer.summarize_if_needed(session_id, messages)
        except Exception as exc:
            log.debug(f"[{session_id}] 백그라운드 요약 실패 (무시): {exc}")

    async def _invoke_agent(
        self, agent, user_text: str, session_id: str, summary_ctx: str = ""
    ) -> dict[str, Any]:
        """Agent를 비동기 호출하고 결과를 파싱합니다."""
        # 요약 컨텍스트가 있으면 메시지에 포함
        input_messages: list = [HumanMessage(content=user_text)]
        if summary_ctx:
            # 요약을 별도 HumanMessage 접두사로 전달 (시스템 프롬프트 수정 없이)
            input_messages = [
                HumanMessage(content=f"[컨텍스트]{summary_ctx}\n\n{user_text}")
            ]

        result = await agent.ainvoke(
            {"messages": input_messages},
            config={"configurable": {"thread_id": session_id}},
        )
        messages = result.get("messages", [])
        last = messages[-1] if messages else None
        reply = last.content if last else ERROR_REPLY
        if isinstance(reply, list):
            reply = " ".join(
                block.get("text", "") for block in reply if isinstance(block, dict)
            )

        tool_calls = [
            {"tool": m.name, "args": m.args if hasattr(m, "args") else {}}
            for m in messages
            if hasattr(m, "type") and m.type == "tool"
        ]

        usage = getattr(last, "usage_metadata", {}) or {}
        tokens = {
            "in": usage.get("input_tokens", 0),
            "out": usage.get("output_tokens", 0),
        }

        return {"reply": reply, "tool_calls": tool_calls, "tokens": tokens}

    def _handle_without_llm(self, route, user_text: str) -> str | None:
        """LLM 없이 직접 처리할 수 있는 단순 의도 처리."""
        from app.agent.tools.reminder import _set_timer_direct

        if route.intent == Intent.TIMER:
            minutes = route.extracted.get("minutes", 0)
            seconds = route.extracted.get("seconds", 0)
            if minutes or seconds:
                total_sec = minutes * 60 + seconds
                label = f"{minutes}분" if minutes else f"{seconds}초"
                _set_timer_direct(total_sec, f"{label} 타이머")
                return f"{label} 타이머 시작했어요."

        return None

    def _is_over_daily_limit(self, user_id: str) -> bool:
        today = datetime.now().date().isoformat()
        key = f"{user_id}:{today}"
        usage = _session_tokens.get(key, {})
        total = usage.get("in", 0) + usage.get("out", 0)
        return total >= settings.daily_token_limit

    def _record_tokens(self, user_id: str, session_id: str, tokens: dict, model: str = ""):
        """토큰 사용량을 메모리 + DB에 기록합니다."""
        in_tok = tokens.get("in", 0)
        out_tok = tokens.get("out", 0)
        if in_tok == 0 and out_tok == 0:
            return

        # 메모리 집계
        today = datetime.now().date().isoformat()
        key = f"{user_id}:{today}"
        existing = _session_tokens.setdefault(key, {"in": 0, "out": 0})
        existing["in"] += in_tok
        existing["out"] += out_tok

        # DB 비동기 저장 (fire-and-forget)
        try:
            from app.utils.token_tracker import record_usage
            record_usage(
                user_id=user_id,
                session_id=session_id,
                model=model or settings.llm_default_model,
                input_tokens=in_tok,
                output_tokens=out_tok,
            )
        except Exception as exc:
            log.debug(f"토큰 DB 기록 실패 (무시): {exc}")

    def get_token_usage(self, user_id: str) -> dict:
        """사용자 오늘 토큰 사용량 조회."""
        today = datetime.now().date().isoformat()
        key = f"{user_id}:{today}"
        return _session_tokens.get(key, {"in": 0, "out": 0})


# 싱글턴 인스턴스 (FastAPI 앱 시작 시 초기화)
_louis_agent: LouisAgent | None = None


def get_agent() -> LouisAgent:
    global _louis_agent
    if _louis_agent is None:
        _louis_agent = LouisAgent()
    return _louis_agent

"""
대화 기록 자동 요약 모듈

- 세션별 메시지가 SUMMARIZE_THRESHOLD를 넘으면 오래된 메시지를 요약합니다.
- 요약은 Claude Haiku로 생성되며 메모리(+ 선택적으로 DB)에 저장됩니다.
- 다음 호출 시 시스템 프롬프트에 요약을 주입하여 컨텍스트를 유지합니다.
"""
import logging
from datetime import datetime
from typing import Any

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage

from app.config import settings

log = logging.getLogger("louis.summarizer")

# 요약 트리거 기준: 세션당 메시지 수
SUMMARIZE_THRESHOLD = 10
# 요약 후 유지할 최근 메시지 수
KEEP_RECENT = 4


_SUMMARY_PROMPT = """\
아래는 사용자와 AI 비서 루이스 사이의 대화 기록입니다.
이 대화의 핵심 정보를 3~5문장으로 간결하게 요약해 주세요.
중요한 사용자 요청, 수행된 작업, 확인된 정보만 포함하세요.
불필요한 인사말이나 반복 내용은 생략하세요.

대화:
{conversation}

요약:"""


class ConversationSummarizer:
    """세션별 대화 기록 요약 관리자."""

    def __init__(self):
        self._llm = ChatAnthropic(
            model=settings.llm_default_model,  # Haiku — 저비용
            api_key=settings.anthropic_api_key,
            temperature=0.3,
            max_tokens=512,
        )
        # session_id → {"summary": str, "turn_count": int, "updated_at": datetime}
        self._summaries: dict[str, dict[str, Any]] = {}
        # session_id → 현재 세션 누적 턴 수
        self._turn_counts: dict[str, int] = {}

    def increment_turn(self, session_id: str) -> int:
        """세션 턴 수를 1 증가하고 현재 값을 반환합니다."""
        count = self._turn_counts.get(session_id, 0) + 1
        self._turn_counts[session_id] = count
        return count

    def should_summarize(self, session_id: str) -> bool:
        """요약이 필요한지 판단합니다."""
        count = self._turn_counts.get(session_id, 0)
        return count > 0 and count % SUMMARIZE_THRESHOLD == 0

    def get_summary(self, session_id: str) -> str | None:
        """저장된 요약 텍스트를 반환합니다."""
        entry = self._summaries.get(session_id)
        return entry["summary"] if entry else None

    async def summarize_if_needed(
        self,
        session_id: str,
        messages: list[BaseMessage],
    ) -> str | None:
        """
        세션 메시지가 임계값을 초과하면 오래된 메시지를 요약합니다.

        Returns:
            새로 생성된 요약 텍스트, 또는 요약이 불필요한 경우 None.
        """
        if not self.should_summarize(session_id):
            return None
        if len(messages) <= KEEP_RECENT:
            return None

        # 요약할 메시지: 최근 KEEP_RECENT 개를 제외한 나머지
        to_summarize = messages[:-KEEP_RECENT]
        conversation_text = _format_messages(to_summarize)

        try:
            prompt = _SUMMARY_PROMPT.format(conversation=conversation_text)
            response = await self._llm.ainvoke([HumanMessage(content=prompt)])
            summary = _extract_text(response)

            # 기존 요약이 있으면 합치기
            existing = self.get_summary(session_id)
            if existing:
                summary = f"[이전 대화 요약]\n{existing}\n\n[최근 대화 요약]\n{summary}"

            self._summaries[session_id] = {
                "summary": summary,
                "turn_count": self._turn_counts[session_id],
                "updated_at": datetime.now(),
            }
            log.info(f"[{session_id}] 대화 요약 생성 완료 ({len(to_summarize)}개 메시지 → {len(summary)}자)")
            return summary

        except Exception as exc:
            log.warning(f"[{session_id}] 요약 생성 실패 (무시): {exc}")
            return None

    def build_summary_context(self, session_id: str) -> str:
        """
        시스템 프롬프트에 삽입할 요약 컨텍스트 문자열을 반환합니다.
        요약이 없으면 빈 문자열을 반환합니다.
        """
        summary = self.get_summary(session_id)
        if not summary:
            return ""
        return f"\n\n[이전 대화 요약]\n{summary}\n"

    def clear(self, session_id: str) -> None:
        """세션 데이터를 초기화합니다."""
        self._summaries.pop(session_id, None)
        self._turn_counts.pop(session_id, None)


def _format_messages(messages: list[BaseMessage]) -> str:
    lines = []
    for m in messages:
        role = "사용자" if isinstance(m, HumanMessage) else "루이스"
        text = _extract_text(m)
        if text:
            lines.append(f"{role}: {text}")
    return "\n".join(lines)


def _extract_text(msg: BaseMessage) -> str:
    content = msg.content
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        return " ".join(
            block.get("text", "") for block in content if isinstance(block, dict)
        ).strip()
    return ""

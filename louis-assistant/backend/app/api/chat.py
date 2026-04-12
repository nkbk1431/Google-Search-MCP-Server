"""
루이스 개인비서 - 채팅 API
/api/v1/chat 엔드포인트: 사용자 발화 → Agent 처리 → 응답.
SSE(Server-Sent Events) 스트리밍도 지원합니다.
"""
import asyncio
import logging
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.agent.orchestrator import get_agent
from app.api.auth import get_current_user
from app.config import settings
from app.services.personalization import get_personalization_service

limiter = Limiter(key_func=get_remote_address)

log = logging.getLogger("louis.api.chat")

router = APIRouter()


class ChatRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=500, description="사용자 발화 텍스트")
    session_id: str = Field(default="default", description="대화 세션 ID")


class ChatResponse(BaseModel):
    reply: str
    tool_calls: list[dict] = []
    tokens: dict[str, int] = {}


@router.post("/chat", response_model=ChatResponse, summary="루이스에게 말하기")
@limiter.limit("30/minute")
async def chat(
    request: Request,
    req: ChatRequest,
    username: str = Depends(get_current_user),
):
    """
    사용자의 발화를 처리하고 루이스의 응답을 반환합니다.

    - **text**: 사용자 발화 (STT 결과 또는 텍스트 입력)
    - **session_id**: 대화 세션 ID (컨텍스트 연속성 유지)
    """
    log.info(f"[{username}|{req.session_id}] {req.text[:50]}")

    agent = get_agent()
    result = await agent.chat(
        user_text=req.text,
        session_id=req.session_id,
        user_id=username,
    )
    return ChatResponse(**result)


@router.post("/chat/stream", summary="루이스 응답 스트리밍")
async def chat_stream(
    req: ChatRequest,
    username: str = Depends(get_current_user),
):
    """SSE로 루이스 응답을 스트리밍합니다."""

    async def event_generator() -> AsyncGenerator[str, None]:
        agent = get_agent()
        try:
            result = await agent.chat(
                user_text=req.text,
                session_id=req.session_id,
                user_id=username,
            )
            reply = result.get("reply", "")
            # 단어 단위로 스트리밍 (실제 LLM 스트리밍은 LangChain astream으로 교체 가능)
            words = reply.split()
            for i, word in enumerate(words):
                chunk = word + (" " if i < len(words) - 1 else "")
                yield f"data: {chunk}\n\n"
                await asyncio.sleep(0.05)
            yield "data: [DONE]\n\n"
        except Exception as exc:
            log.error(f"스트리밍 오류: {exc}", exc_info=True)
            yield "data: 오류가 발생했어요.\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/preferences", summary="사용자 선호도 조회")
async def get_preferences(username: str = Depends(get_current_user)):
    """학습된 사용자 선호도 전체를 반환합니다."""
    svc = get_personalization_service()
    return {"user": username, "preferences": svc.get_all_preferences(username)}


@router.put("/preferences/{key}", summary="사용자 선호도 수동 설정")
async def set_preference(
    key: str,
    value: str,
    username: str = Depends(get_current_user),
):
    """특정 선호도 키-값을 명시적으로 저장합니다."""
    svc = get_personalization_service()
    svc.set_preference(username, key, value)
    return {"user": username, "key": key, "value": value, "status": "saved"}


@router.delete("/preferences/{key}", summary="사용자 선호도 삭제")
async def delete_preference(
    key: str,
    username: str = Depends(get_current_user),
):
    """특정 선호도를 삭제합니다."""
    from app.db.session import get_sync_db
    from app.db.models import UserPreference

    with get_sync_db() as db:
        row = (
            db.query(UserPreference)
            .filter(
                UserPreference.user_id == username,
                UserPreference.pref_key == key,
            )
            .first()
        )
        if row is None:
            raise HTTPException(status_code=404, detail="선호도를 찾을 수 없어요.")
        db.delete(row)
        db.commit()
    return {"status": "deleted", "key": key}


@router.get("/chat/usage", summary="오늘 토큰 사용량 조회")
async def get_usage(username: str = Depends(get_current_user)):
    """오늘 사용한 토큰 수와 월간 예상 비용을 반환합니다."""
    agent = get_agent()
    usage = agent.get_token_usage(username)
    total_today = usage.get("in", 0) + usage.get("out", 0)

    from app.utils.token_tracker import get_monthly_cost_usd
    monthly_cost = get_monthly_cost_usd(username)

    return {
        "user": username,
        "today_tokens": usage,
        "today_total": total_today,
        "daily_limit": settings.daily_token_limit,
        "remaining": max(0, settings.daily_token_limit - total_today),
        "monthly_cost_usd": monthly_cost,
        "monthly_budget_usd": settings.monthly_budget_usd,
    }

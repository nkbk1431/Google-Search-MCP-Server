"""
루이스 개인비서 - 토큰 사용량 DB 기록
LLM 호출마다 TokenUsage 레코드를 SQLite에 저장합니다.
"""
import logging
from datetime import datetime

log = logging.getLogger("louis.utils.token_tracker")


def record_usage(
    user_id: str,
    session_id: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
) -> None:
    """토큰 사용량을 DB에 저장합니다 (동기, fire-and-forget 용도)."""
    try:
        from app.db.models import TokenUsage
        from app.db.session import get_sync_db
        with get_sync_db() as db:
            record = TokenUsage(
                user_id=user_id,
                session_id=session_id,
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                created_at=datetime.now(),
            )
            db.add(record)
            db.commit()
    except Exception as exc:
        log.warning(f"토큰 사용량 DB 저장 실패: {exc}")


def get_daily_usage(user_id: str, date: datetime | None = None) -> dict:
    """사용자의 특정 날짜 토큰 사용량 합계를 반환합니다."""
    if date is None:
        date = datetime.now()
    day_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = date.replace(hour=23, minute=59, second=59, microsecond=999999)

    try:
        from app.db.models import TokenUsage
        from app.db.session import get_sync_db
        from sqlalchemy import func
        with get_sync_db() as db:
            result = db.query(
                func.sum(TokenUsage.input_tokens).label("total_in"),
                func.sum(TokenUsage.output_tokens).label("total_out"),
            ).filter(
                TokenUsage.user_id == user_id,
                TokenUsage.created_at >= day_start,
                TokenUsage.created_at <= day_end,
            ).first()

        return {
            "in": result.total_in or 0,
            "out": result.total_out or 0,
            "date": date.date().isoformat(),
        }
    except Exception as exc:
        log.warning(f"토큰 사용량 조회 실패: {exc}")
        return {"in": 0, "out": 0, "date": date.date().isoformat()}


def get_monthly_cost_usd(user_id: str) -> float:
    """사용자의 이번 달 예상 비용(USD)을 반환합니다."""
    now = datetime.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Claude Haiku 4.5 가격 기준 (2026년)
    # Input: $1/1M tokens, Output: $5/1M tokens
    HAIKU_IN_PER_M = 1.0
    HAIKU_OUT_PER_M = 5.0

    try:
        from app.db.models import TokenUsage
        from app.db.session import get_sync_db
        from sqlalchemy import func
        with get_sync_db() as db:
            result = db.query(
                func.sum(TokenUsage.input_tokens).label("total_in"),
                func.sum(TokenUsage.output_tokens).label("total_out"),
            ).filter(
                TokenUsage.user_id == user_id,
                TokenUsage.created_at >= month_start,
            ).first()

        in_tok = result.total_in or 0
        out_tok = result.total_out or 0
        cost = (in_tok / 1_000_000 * HAIKU_IN_PER_M) + (out_tok / 1_000_000 * HAIKU_OUT_PER_M)
        return round(cost, 4)
    except Exception as exc:
        log.warning(f"월간 비용 계산 실패: {exc}")
        return 0.0

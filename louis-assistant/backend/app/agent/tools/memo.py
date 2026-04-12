"""
루이스 개인비서 - 메모 도구
음성 메모를 로컬 DB에 저장하고 검색합니다.
"""
import logging

from langchain_core.tools import tool

log = logging.getLogger("louis.tools.memo")


@tool
def add_memo(content: str) -> str:
    """메모를 저장합니다.

    Args:
        content: 메모 내용

    Returns:
        저장 결과 메시지
    """
    try:
        from app.db.models import Memo
        from app.db.session import get_sync_db
        from datetime import datetime
        with get_sync_db() as db:
            item = Memo(content=content, created_at=datetime.now())
            db.add(item)
            db.commit()
            db.refresh(item)
        return f"메모 저장했어요. (#{item.id})"
    except Exception as exc:
        log.error(f"메모 저장 실패: {exc}", exc_info=True)
        return "메모 저장에 실패했어요."


@tool
def search_memo(keyword: str) -> str:
    """저장된 메모에서 키워드를 검색합니다.

    Args:
        keyword: 검색 키워드

    Returns:
        검색된 메모 목록
    """
    try:
        from app.db.models import Memo
        from app.db.session import get_sync_db
        with get_sync_db() as db:
            items = (
                db.query(Memo)
                .filter(Memo.content.contains(keyword))
                .order_by(Memo.id.desc())
                .limit(10)
                .all()
            )
        if not items:
            return f"'{keyword}' 검색 결과가 없어요."
        return "\n".join([
            f"- {i.content} ({i.created_at.strftime('%m/%d') if i.created_at else '날짜없음'})"
            for i in items
        ])
    except Exception as exc:
        log.error(f"메모 검색 실패: {exc}", exc_info=True)
        return "메모 검색에 실패했어요."


@tool
def list_memos(limit: int = 5) -> str:
    """최근 메모 목록을 조회합니다.

    Args:
        limit: 조회할 메모 개수. 기본 5개.

    Returns:
        최근 메모 목록
    """
    try:
        from app.db.models import Memo
        from app.db.session import get_sync_db
        with get_sync_db() as db:
            items = db.query(Memo).order_by(Memo.id.desc()).limit(limit).all()
        if not items:
            return "저장된 메모가 없어요."
        return "\n".join([
            f"#{i.id} {i.content}"
            for i in items
        ])
    except Exception as exc:
        log.error(f"메모 조회 실패: {exc}", exc_info=True)
        return "메모 조회에 실패했어요."

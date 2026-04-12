"""
루이스 개인비서 - 할일(Todo) 도구
SQLite 로컬 DB에 할일 목록을 저장하고 관리합니다.
"""
import logging

from langchain_core.tools import tool

from app.db.session import get_sync_db

log = logging.getLogger("louis.tools.todo")


@tool
def add_todo(content: str) -> str:
    """할일 목록에 새 항목을 추가합니다.

    Args:
        content: 할일 내용

    Returns:
        추가 결과 메시지
    """
    try:
        from app.db.models import Todo
        from datetime import datetime
        with get_sync_db() as db:
            item = Todo(content=content, done=False, created_at=datetime.now())
            db.add(item)
            db.commit()
            db.refresh(item)
        return f"할일 추가했어요: '{content}' (#{item.id})"
    except Exception as exc:
        log.error(f"할일 추가 실패: {exc}", exc_info=True)
        return "할일 추가에 실패했어요."


@tool
def list_todos() -> str:
    """미완료 할일 목록을 조회합니다.

    Returns:
        할일 목록 문자열
    """
    try:
        from app.db.models import Todo
        with get_sync_db() as db:
            items = db.query(Todo).filter(Todo.done == False).order_by(Todo.id.desc()).all()
        if not items:
            return "진행 중인 할일이 없어요."
        return "\n".join([f"#{i.id} {i.content}" for i in items])
    except Exception as exc:
        log.error(f"할일 조회 실패: {exc}", exc_info=True)
        return "할일 조회에 실패했어요."


@tool
def complete_todo(todo_id: int) -> str:
    """할일을 완료 처리합니다.

    Args:
        todo_id: 완료할 할일 번호 (list_todos로 확인)

    Returns:
        완료 처리 결과
    """
    try:
        from app.db.models import Todo
        with get_sync_db() as db:
            item = db.query(Todo).filter(Todo.id == todo_id).first()
            if item is None:
                return f"#{todo_id} 항목을 찾을 수 없어요."
            item.done = True
            db.commit()
        return f"#{todo_id} '{item.content}' 완료 처리했어요."
    except Exception as exc:
        log.error(f"할일 완료 실패: {exc}", exc_info=True)
        return "완료 처리에 실패했어요."

"""
메모 · 할일 도구 테스트
add_memo / search_memo / list_memos / add_todo / list_todos / complete_todo
를 검증합니다.
"""
import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock, PropertyMock


# ── 공통 DB 목 헬퍼 ────────────────────────────────────────

def _make_db(query_result=None):
    mock_db = MagicMock()
    mock_db.__enter__ = MagicMock(return_value=mock_db)
    mock_db.__exit__ = MagicMock(return_value=False)
    if query_result is not None:
        mock_db.query.return_value.filter.return_value.order_by.return_value \
               .limit.return_value.all.return_value = query_result
        mock_db.query.return_value.filter.return_value \
               .order_by.return_value.all.return_value = query_result
        mock_db.query.return_value.order_by.return_value \
               .limit.return_value.all.return_value = query_result
    return mock_db


def _make_item(id_: int, content: str, created_at=None):
    item = MagicMock()
    item.id = id_
    item.content = content
    item.created_at = created_at or datetime(2026, 4, 12, 10, 0, 0)
    return item


# ════════════════════════════════════════════════════════════
# 메모 도구
# ════════════════════════════════════════════════════════════

class TestAddMemo:

    def test_add_memo_success(self):
        from app.agent.tools.memo import add_memo

        mock_db = _make_db()
        mock_item = _make_item(1, "오늘 할 일 목록")
        mock_db.refresh.side_effect = lambda obj: setattr(obj, "id", 1)
        mock_db.add.side_effect = lambda obj: None

        with patch("app.agent.tools.memo.get_sync_db", return_value=mock_db):
            result = add_memo.invoke({"content": "오늘 할 일 목록"})

        assert "메모" in result
        assert "저장" in result

    def test_add_memo_db_error(self):
        from app.agent.tools.memo import add_memo

        with patch("app.agent.tools.memo.get_sync_db",
                   side_effect=Exception("DB 오류")):
            result = add_memo.invoke({"content": "테스트 메모"})

        assert "실패" in result


class TestSearchMemo:

    def test_search_memo_found(self):
        from app.agent.tools.memo import search_memo

        items = [_make_item(1, "프로젝트 아이디어")]
        mock_db = _make_db(items)
        with patch("app.agent.tools.memo.get_sync_db", return_value=mock_db):
            result = search_memo.invoke({"keyword": "프로젝트"})

        assert "프로젝트 아이디어" in result

    def test_search_memo_not_found(self):
        from app.agent.tools.memo import search_memo

        mock_db = _make_db([])
        with patch("app.agent.tools.memo.get_sync_db", return_value=mock_db):
            result = search_memo.invoke({"keyword": "없는키워드XYZ"})

        assert "없어요" in result or "결과" in result

    def test_search_memo_db_error(self):
        from app.agent.tools.memo import search_memo

        with patch("app.agent.tools.memo.get_sync_db",
                   side_effect=Exception("DB 오류")):
            result = search_memo.invoke({"keyword": "테스트"})

        assert "실패" in result

    def test_search_memo_multiple_results(self):
        from app.agent.tools.memo import search_memo

        items = [
            _make_item(3, "회의 내용 정리"),
            _make_item(2, "회의 준비사항"),
        ]
        mock_db = _make_db(items)
        with patch("app.agent.tools.memo.get_sync_db", return_value=mock_db):
            result = search_memo.invoke({"keyword": "회의"})

        assert "회의 내용 정리" in result
        assert "회의 준비사항" in result


class TestListMemos:

    def test_list_memos_returns_items(self):
        from app.agent.tools.memo import list_memos

        items = [_make_item(2, "최근 메모"), _make_item(1, "이전 메모")]
        mock_db = _make_db()
        mock_db.query.return_value.order_by.return_value.limit.return_value.all.return_value = items

        with patch("app.agent.tools.memo.get_sync_db", return_value=mock_db):
            result = list_memos.invoke({"limit": 5})

        assert "최근 메모" in result
        assert "#2" in result

    def test_list_memos_empty(self):
        from app.agent.tools.memo import list_memos

        mock_db = _make_db()
        mock_db.query.return_value.order_by.return_value.limit.return_value.all.return_value = []

        with patch("app.agent.tools.memo.get_sync_db", return_value=mock_db):
            result = list_memos.invoke({"limit": 5})

        assert "없어요" in result

    def test_list_memos_db_error(self):
        from app.agent.tools.memo import list_memos

        with patch("app.agent.tools.memo.get_sync_db",
                   side_effect=Exception("DB 오류")):
            result = list_memos.invoke({"limit": 5})

        assert "실패" in result


# ════════════════════════════════════════════════════════════
# 할일 도구
# ════════════════════════════════════════════════════════════

class TestAddTodo:

    def test_add_todo_success(self):
        from app.agent.tools.todo import add_todo

        mock_db = MagicMock()
        mock_db.__enter__ = MagicMock(return_value=mock_db)
        mock_db.__exit__ = MagicMock(return_value=False)
        mock_db.refresh.side_effect = lambda obj: setattr(obj, "id", 5)

        with patch("app.agent.tools.todo.get_sync_db", return_value=mock_db):
            result = add_todo.invoke({"content": "장보기"})

        assert "장보기" in result
        assert "추가" in result

    def test_add_todo_db_error(self):
        from app.agent.tools.todo import add_todo

        with patch("app.agent.tools.todo.get_sync_db",
                   side_effect=Exception("DB 오류")):
            result = add_todo.invoke({"content": "테스트 할일"})

        assert "실패" in result


class TestListTodos:

    def test_list_todos_returns_items(self):
        from app.agent.tools.todo import list_todos

        t1 = MagicMock()
        t1.id = 3
        t1.content = "영어 공부"
        t2 = MagicMock()
        t2.id = 2
        t2.content = "운동하기"

        mock_db = MagicMock()
        mock_db.__enter__ = MagicMock(return_value=mock_db)
        mock_db.__exit__ = MagicMock(return_value=False)
        mock_db.query.return_value.filter.return_value \
               .order_by.return_value.all.return_value = [t1, t2]

        with patch("app.agent.tools.todo.get_sync_db", return_value=mock_db):
            result = list_todos.invoke({})

        assert "영어 공부" in result
        assert "운동하기" in result
        assert "#3" in result

    def test_list_todos_empty(self):
        from app.agent.tools.todo import list_todos

        mock_db = MagicMock()
        mock_db.__enter__ = MagicMock(return_value=mock_db)
        mock_db.__exit__ = MagicMock(return_value=False)
        mock_db.query.return_value.filter.return_value \
               .order_by.return_value.all.return_value = []

        with patch("app.agent.tools.todo.get_sync_db", return_value=mock_db):
            result = list_todos.invoke({})

        assert "없어요" in result

    def test_list_todos_db_error(self):
        from app.agent.tools.todo import list_todos

        with patch("app.agent.tools.todo.get_sync_db",
                   side_effect=Exception("DB 오류")):
            result = list_todos.invoke({})

        assert "실패" in result


class TestCompleteTodo:

    def test_complete_todo_success(self):
        from app.agent.tools.todo import complete_todo

        mock_item = MagicMock()
        mock_item.id = 1
        mock_item.content = "장보기"

        mock_db = MagicMock()
        mock_db.__enter__ = MagicMock(return_value=mock_db)
        mock_db.__exit__ = MagicMock(return_value=False)
        mock_db.query.return_value.filter.return_value.first.return_value = mock_item

        with patch("app.agent.tools.todo.get_sync_db", return_value=mock_db):
            result = complete_todo.invoke({"todo_id": 1})

        assert "완료" in result
        assert "장보기" in result
        assert mock_item.done is True

    def test_complete_todo_not_found(self):
        from app.agent.tools.todo import complete_todo

        mock_db = MagicMock()
        mock_db.__enter__ = MagicMock(return_value=mock_db)
        mock_db.__exit__ = MagicMock(return_value=False)
        mock_db.query.return_value.filter.return_value.first.return_value = None

        with patch("app.agent.tools.todo.get_sync_db", return_value=mock_db):
            result = complete_todo.invoke({"todo_id": 999})

        assert "찾을 수 없어요" in result or "없어요" in result

    def test_complete_todo_db_error(self):
        from app.agent.tools.todo import complete_todo

        with patch("app.agent.tools.todo.get_sync_db",
                   side_effect=Exception("DB 오류")):
            result = complete_todo.invoke({"todo_id": 1})

        assert "실패" in result

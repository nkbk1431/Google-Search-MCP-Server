"""
루이스 개인비서 - 데이터베이스 모델
SQLAlchemy ORM 모델 정의.
"""
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class Todo(Base):
    """할일 목록."""
    __tablename__ = "todos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    content = Column(Text, nullable=False)
    done = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.now, nullable=False)

    def __repr__(self) -> str:
        status = "완료" if self.done else "대기"
        return f"<Todo #{self.id} [{status}] {self.content[:30]}>"


class Memo(Base):
    """음성 메모."""
    __tablename__ = "memos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.now, nullable=False)

    def __repr__(self) -> str:
        return f"<Memo #{self.id} {self.content[:30]}>"


class Reminder(Base):
    """리마인더 이력."""
    __tablename__ = "reminders"

    id = Column(Integer, primary_key=True, autoincrement=True)
    content = Column(Text, nullable=False)
    trigger_at = Column(DateTime, nullable=False)
    fired = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.now, nullable=False)

    def __repr__(self) -> str:
        return f"<Reminder #{self.id} {self.trigger_at} {self.content[:30]}>"


class TokenUsage(Base):
    """LLM 토큰 사용량 이력."""
    __tablename__ = "token_usage"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(128), nullable=False, index=True)
    session_id = Column(String(128), nullable=False)
    model = Column(String(64), nullable=False)
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now, nullable=False)

    def __repr__(self) -> str:
        return f"<TokenUsage user={self.user_id} in={self.input_tokens} out={self.output_tokens}>"

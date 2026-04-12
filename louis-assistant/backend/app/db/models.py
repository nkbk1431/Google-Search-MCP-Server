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


class UserPreference(Base):
    """사용자 개인화 설정 및 학습된 선호도."""
    __tablename__ = "user_preferences"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(128), nullable=False, index=True)
    # 선호도 키 (예: "home_city", "commute_mode", "wake_time", "music_genre")
    pref_key = Column(String(128), nullable=False)
    # 선호도 값 (JSON 직렬화 가능한 문자열)
    pref_value = Column(Text, nullable=False)
    # 업데이트 횟수 (자주 사용할수록 높은 신뢰도)
    update_count = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)

    def __repr__(self) -> str:
        return f"<UserPref user={self.user_id} {self.pref_key}={self.pref_value}>"


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


class FcmToken(Base):
    """사용자별 Firebase Cloud Messaging 토큰 저장."""
    __tablename__ = "fcm_tokens"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(128), nullable=False, unique=True, index=True)
    token = Column(String(512), nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)

    def __repr__(self) -> str:
        return f"<FcmToken user={self.user_id} token={self.token[:20]}...>"

"""
루이스 개인비서 - 데이터베이스 세션 관리
SQLite + SQLAlchemy 세션 팩토리.
"""
import logging
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.db.models import Base

log = logging.getLogger("louis.db")

# 동기 엔진 (SQLite)
_engine = None
_SessionLocal = None


def _get_engine():
    global _engine
    if _engine is None:
        # aiosqlite URL을 동기 URL로 변환
        sync_url = settings.database_url.replace("sqlite+aiosqlite", "sqlite")
        _engine = create_engine(
            sync_url,
            connect_args={"check_same_thread": False},
            echo=settings.app_env == "development",
        )
    return _engine


def _get_session_factory() -> sessionmaker:
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=_get_engine(),
        )
    return _SessionLocal


async def init_db():
    """앱 시작 시 DB 테이블을 생성합니다."""
    engine = _get_engine()
    Base.metadata.create_all(bind=engine)
    log.info("DB 테이블 초기화 완료")


@contextmanager
def get_sync_db():
    """동기 DB 세션 컨텍스트 매니저."""
    factory = _get_session_factory()
    session: Session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db():
    """FastAPI Depends용 DB 세션 제너레이터."""
    factory = _get_session_factory()
    db = factory()
    try:
        yield db
    finally:
        db.close()

"""
루이스 개인비서 - FastAPI 엔트리 포인트
실행: uvicorn app.main:app --reload --port 8000
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.db.session import init_db
from app.api.chat import router as chat_router
from app.api.auth import router as auth_router

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
log = logging.getLogger("louis.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("루이스 서버 시작 중...")
    await init_db()
    log.info(f"DB 초기화 완료: {settings.database_url}")
    log.info(f"환경: {settings.app_env}")
    yield
    log.info("루이스 서버 종료.")


app = FastAPI(
    title="루이스(Louis) 개인비서 API",
    description="AI 기반 한국어 개인비서 백엔드",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if not settings.is_production else None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if not settings.is_production else ["https://yourdomain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(auth_router, prefix="/api/v1/auth", tags=["인증"])
app.include_router(chat_router, prefix="/api/v1", tags=["채팅"])


@app.get("/", tags=["상태"])
async def root():
    return {"message": "루이스 API 정상 동작 중", "version": "1.0.0"}


@app.get("/health", tags=["상태"])
async def health():
    return {
        "status": "ok",
        "env": settings.app_env,
        "llm_model": settings.llm_default_model,
    }


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    log.error(f"처리되지 않은 예외: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "서버 오류가 발생했습니다. 잠시 후 다시 시도해주세요."},
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=not settings.is_production,
    )

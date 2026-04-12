"""
루이스 개인비서 - 인증 API
JWT 기반 액세스/리프레시 토큰 발급.
"""
import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, Field

from app.config import settings

log = logging.getLogger("louis.api.auth")

router = APIRouter()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")

ALGORITHM = "HS256"

# 개발용 임시 사용자 (실 배포 시 DB로 교체)
_FAKE_USERS: dict[str, dict] = {
    "admin": {
        "username": "admin",
        "hashed_password": pwd_context.hash("louis1234"),
    }
}


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    username: str | None = None


class RefreshRequest(BaseModel):
    refresh_token: str


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=32, pattern=r"^[a-zA-Z0-9_]+$")
    password: str = Field(..., min_length=8, max_length=64)


def _create_token(data: dict, expires_delta: timedelta) -> str:
    payload = data.copy()
    payload["exp"] = datetime.utcnow() + expires_delta
    return jwt.encode(payload, settings.app_secret_key, algorithm=ALGORITHM)


def get_current_user(token: str = Depends(oauth2_scheme)) -> str:
    """현재 JWT 토큰에서 사용자명을 추출합니다."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="인증 토큰이 유효하지 않아요.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.app_secret_key, algorithms=[ALGORITHM])
        username: str | None = payload.get("sub")
        if username is None:
            raise credentials_exception
        return username
    except JWTError:
        raise credentials_exception


@router.post("/token", response_model=Token, summary="로그인 및 토큰 발급")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """사용자 이름과 비밀번호로 JWT 토큰을 발급합니다."""
    user = _FAKE_USERS.get(form_data.username)
    if not user or not pwd_context.verify(form_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="아이디 또는 비밀번호가 올바르지 않아요.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = _create_token(
        {"sub": form_data.username},
        timedelta(seconds=settings.jwt_access_token_expire),
    )
    refresh_token = _create_token(
        {"sub": form_data.username, "type": "refresh"},
        timedelta(seconds=settings.jwt_refresh_token_expire),
    )
    return Token(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=Token, summary="액세스 토큰 갱신")
async def refresh_token(req: RefreshRequest):
    """리프레시 토큰으로 새 액세스/리프레시 토큰 쌍을 발급합니다."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="리프레시 토큰이 유효하지 않아요.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(req.refresh_token, settings.app_secret_key, algorithms=[ALGORITHM])
        if payload.get("type") != "refresh":
            raise credentials_exception
        username: str | None = payload.get("sub")
        if username is None or username not in _FAKE_USERS:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    access_token = _create_token(
        {"sub": username},
        timedelta(seconds=settings.jwt_access_token_expire),
    )
    new_refresh = _create_token(
        {"sub": username, "type": "refresh"},
        timedelta(seconds=settings.jwt_refresh_token_expire),
    )
    return Token(access_token=access_token, refresh_token=new_refresh)


@router.post("/register", response_model=Token, summary="신규 사용자 등록", status_code=201)
async def register(req: RegisterRequest):
    """새 사용자를 등록하고 즉시 토큰을 발급합니다."""
    if req.username in _FAKE_USERS:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 사용 중인 아이디예요.",
        )
    _FAKE_USERS[req.username] = {
        "username": req.username,
        "hashed_password": pwd_context.hash(req.password),
    }
    log.info(f"신규 사용자 등록: {req.username}")
    access_token = _create_token(
        {"sub": req.username},
        timedelta(seconds=settings.jwt_access_token_expire),
    )
    refresh_token = _create_token(
        {"sub": req.username, "type": "refresh"},
        timedelta(seconds=settings.jwt_refresh_token_expire),
    )
    return Token(access_token=access_token, refresh_token=refresh_token)


@router.delete("/me", summary="계정 삭제", status_code=204)
async def delete_account(username: str = Depends(get_current_user)):
    """현재 로그인된 사용자 계정을 삭제합니다."""
    _FAKE_USERS.pop(username, None)
    log.info(f"계정 삭제: {username}")


@router.get("/me", summary="현재 사용자 정보")
async def get_me(username: str = Depends(get_current_user)):
    return {"username": username}

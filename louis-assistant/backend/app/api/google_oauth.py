"""
루이스 개인비서 - Google OAuth 웹 플로우 API (Phase 14)

Cloud Run 같은 headless 환경에서 Google Calendar/Gmail 연동을 위한
웹 기반 OAuth 2.0 인증 플로우를 제공합니다.

사용 순서:
  1. GET  /api/v1/auth/google/init     → 인증 URL 반환
  2. 브라우저에서 URL 열어 Google 로그인
  3. GET  /api/v1/auth/google/callback → 토큰 저장 완료
  4. GET  /api/v1/auth/google/status   → 연동 상태 확인
  5. DELETE /api/v1/auth/google/revoke → 연동 해제
"""
import logging
import os

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse

from app.api.auth import get_current_user
from app.config import settings

log = logging.getLogger("louis.api.google_oauth")
router = APIRouter()

# Google OAuth 스코프
_SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
]

# 사용자별 OAuth state 임시 저장 (프로덕션에서는 Redis 사용 권장)
_pending_states: dict[str, str] = {}  # state → username


def _get_redirect_uri(request: Request) -> str:
    """현재 요청 기준 콜백 URI를 생성합니다."""
    base = str(request.base_url).rstrip("/")
    return f"{base}/api/v1/auth/google/callback"


# ── 인증 시작 ───────────────────────────────────────────────

@router.get("/init", summary="Google OAuth 인증 시작")
async def google_oauth_init(
    request: Request,
    username: str = Depends(get_current_user),
):
    """
    Google OAuth 인증 URL을 반환합니다.

    1. 반환된 `auth_url`을 브라우저에서 엽니다.
    2. Google 계정으로 로그인하면 자동으로 콜백이 호출됩니다.
    3. 완료 후 `/api/v1/auth/google/status`로 연동 상태를 확인하세요.
    """
    secret_file = settings.google_client_secret_file
    if not os.path.exists(secret_file):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                f"Google credentials 파일이 없어요: {secret_file}\n"
                "Google Cloud Console에서 OAuth 클라이언트 ID를 발급받아 "
                "backend/ 폴더에 credentials.json으로 저장해주세요."
            ),
        )

    try:
        from google_auth_oauthlib.flow import Flow  # type: ignore
        import secrets

        state = secrets.token_urlsafe(32)
        _pending_states[state] = username

        redirect_uri = _get_redirect_uri(request)
        flow = Flow.from_client_secrets_file(
            secret_file,
            scopes=_SCOPES,
            redirect_uri=redirect_uri,
        )
        auth_url, _ = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
            state=state,
        )

        log.info(f"Google OAuth 시작: {username}")
        return {
            "auth_url": auth_url,
            "message": (
                "위 URL을 브라우저에서 열어 Google 계정으로 로그인해주세요. "
                "완료되면 자동으로 처리됩니다."
            ),
            "user": username,
        }

    except Exception as e:
        log.error(f"OAuth 초기화 실패: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Google OAuth 초기화 실패: {e}",
        )


# ── 콜백 (Google → 서버) ──────────────────────────────────

@router.get("/callback", summary="Google OAuth 콜백 (자동 호출)")
async def google_oauth_callback(
    request: Request,
    code: str = "",
    state: str = "",
    error: str = "",
):
    """
    Google이 인증 완료 후 자동으로 호출하는 콜백 엔드포인트입니다.
    직접 호출하지 마세요.
    """
    if error:
        log.warning(f"Google OAuth 오류: {error}")
        return {"status": "error", "detail": error, "message": "Google 인증이 취소됐거나 오류가 발생했어요."}

    if not code or not state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="잘못된 OAuth 콜백 요청입니다.",
        )

    username = _pending_states.pop(state, None)
    if not username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="만료된 OAuth 상태입니다. /api/v1/auth/google/init부터 다시 시작해주세요.",
        )

    secret_file = settings.google_client_secret_file
    try:
        from google_auth_oauthlib.flow import Flow  # type: ignore

        redirect_uri = _get_redirect_uri(request)
        flow = Flow.from_client_secrets_file(
            secret_file,
            scopes=_SCOPES,
            redirect_uri=redirect_uri,
            state=state,
        )
        # 개발 환경에서만 HTTP 허용 (프로덕션에서는 HTTPS 강제)
        if not settings.is_production:
            os.environ.setdefault("OAUTHLIB_INSECURE_TRANSPORT", "1")
        flow.fetch_token(code=code)
        creds = flow.credentials

        # 사용자별 token 저장
        token_path = _token_path(username)
        os.makedirs(os.path.dirname(token_path), exist_ok=True)
        with open(token_path, "w") as f:
            f.write(creds.to_json())

        log.info(f"Google OAuth 완료: {username} → {token_path}")
        return {
            "status": "ok",
            "user": username,
            "message": "Google 계정 연동이 완료됐어요! 이제 캘린더와 Gmail을 사용할 수 있어요.",
            "scopes": list(creds.scopes or []),
        }

    except Exception as e:
        log.error(f"OAuth 토큰 교환 실패: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Google 인증 처리 실패: {e}",
        )


# ── 연동 상태 확인 ───────────────────────────────────────────

@router.get("/status", summary="Google 연동 상태 확인")
async def google_oauth_status(username: str = Depends(get_current_user)):
    """현재 사용자의 Google 계정 연동 상태를 반환합니다."""
    token_path = _token_path(username)

    if not os.path.exists(token_path):
        return {
            "connected": False,
            "user": username,
            "message": "Google 계정이 연동되지 않았어요. /api/v1/auth/google/init 에서 연동하세요.",
        }

    try:
        from google.oauth2.credentials import Credentials  # type: ignore
        from google.auth.transport.requests import Request  # type: ignore

        creds = Credentials.from_authorized_user_file(token_path, _SCOPES)
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(token_path, "w") as f:
                f.write(creds.to_json())

        return {
            "connected": creds.valid,
            "user": username,
            "scopes": list(creds.scopes or []),
            "expired": creds.expired,
            "message": "Google 계정이 정상적으로 연동돼 있어요." if creds.valid else "토큰이 만료됐어요. 재연동이 필요해요.",
        }
    except Exception as e:
        log.warning(f"Google 상태 확인 실패: {e}")
        return {
            "connected": False,
            "user": username,
            "message": f"Google 연동 상태 확인 실패: {e}",
        }


# ── 연동 해제 ────────────────────────────────────────────────

@router.delete("/revoke", summary="Google 연동 해제", status_code=204)
async def google_oauth_revoke(username: str = Depends(get_current_user)):
    """Google 계정 연동을 해제하고 저장된 토큰을 삭제합니다."""
    token_path = _token_path(username)

    if os.path.exists(token_path):
        try:
            from google.oauth2.credentials import Credentials  # type: ignore
            from google.auth.transport.requests import Request  # type: ignore
            import requests as req

            creds = Credentials.from_authorized_user_file(token_path, _SCOPES)
            # Google에 토큰 취소 요청
            req.post(
                "https://oauth2.googleapis.com/revoke",
                params={"token": creds.token},
                headers={"content-type": "application/x-www-form-urlencoded"},
                timeout=5,
            )
        except Exception as e:
            log.warning(f"Google 토큰 취소 요청 실패 (로컬 파일은 삭제): {e}")
        finally:
            os.remove(token_path)

    log.info(f"Google 연동 해제: {username}")


# ── 헬퍼 ─────────────────────────────────────────────────────

def _token_path(username: str) -> str:
    """사용자별 token.json 경로."""
    safe_name = "".join(c for c in username if c.isalnum() or c in "-_")
    return f"./tokens/{safe_name}_google_token.json"


def get_user_google_credentials(username: str):
    """
    다른 모듈에서 사용자별 Google 자격증명을 가져올 때 사용합니다.

    Args:
        username: 사용자명

    Returns:
        유효한 Credentials 객체 또는 None (미연동 시)
    """
    token_path = _token_path(username)
    if not os.path.exists(token_path):
        return None
    try:
        from google.oauth2.credentials import Credentials  # type: ignore
        from google.auth.transport.requests import Request  # type: ignore

        creds = Credentials.from_authorized_user_file(token_path, _SCOPES)
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open(token_path, "w") as f:
                f.write(creds.to_json())
        return creds if creds.valid else None
    except Exception as e:
        log.warning(f"사용자 {username} Google 자격증명 로드 실패: {e}")
        return None

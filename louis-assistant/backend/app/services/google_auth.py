"""
루이스 개인비서 - Google OAuth 인증 관리
token.json 캐싱 + 자동 갱신 + 서비스 객체 빌더.
"""
import logging
import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from app.config import settings

log = logging.getLogger("louis.services.google_auth")

SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]

TOKEN_PATH = "token.json"

_creds_cache: Credentials | None = None


def get_google_credentials() -> Credentials:
    """
    Google OAuth 자격증명을 가져옵니다.
    token.json이 있으면 로드하고, 만료됐으면 자동 갱신합니다.
    없으면 브라우저 인증 플로우를 시작합니다.

    Returns:
        유효한 Google Credentials 객체

    Raises:
        FileNotFoundError: credentials.json 파일이 없을 때
        RuntimeError: 인증 실패 시
    """
    global _creds_cache

    creds = _creds_cache

    if os.path.exists(TOKEN_PATH):
        try:
            creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
        except Exception as exc:
            log.warning(f"token.json 로드 실패: {exc}")
            creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                _save_token(creds)
                log.info("Google 토큰 자동 갱신 완료")
            except Exception as exc:
                log.error(f"Google 토큰 갱신 실패: {exc}")
                creds = None

        if not creds or not creds.valid:
            secret_file = settings.google_client_secret_file
            if not os.path.exists(secret_file):
                raise FileNotFoundError(
                    f"Google credentials 파일을 찾을 수 없어요: {secret_file}\n"
                    "Google Cloud Console에서 OAuth 클라이언트 ID를 발급받아주세요."
                )
            flow = InstalledAppFlow.from_client_secrets_file(secret_file, SCOPES)
            creds = flow.run_local_server(port=0)
            _save_token(creds)
            log.info("Google OAuth 인증 완료")

    _creds_cache = creds
    return creds


def _save_token(creds: Credentials):
    """자격증명을 token.json에 저장합니다."""
    try:
        with open(TOKEN_PATH, "w") as f:
            f.write(creds.to_json())
    except Exception as exc:
        log.warning(f"token.json 저장 실패: {exc}")


def get_google_service(service_name: str, version: str):
    """
    Google API 서비스 객체를 반환합니다.

    Args:
        service_name: 서비스 이름 (예: 'calendar', 'gmail', 'drive')
        version: API 버전 (예: 'v3', 'v1')

    Returns:
        googleapiclient Resource 객체
    """
    creds = get_google_credentials()
    return build(service_name, version, credentials=creds, cache_discovery=False)

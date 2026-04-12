"""
루이스 개인비서 - 웹훅 API
FCM 토큰 등록 및 서버-to-클라이언트 푸시 발송.
"""
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.auth import get_current_user

log = logging.getLogger("louis.api.webhook")

router = APIRouter()

# FCM 토큰 저장소 (실제 배포 시 DB로 교체)
_fcm_tokens: dict[str, str] = {}


class FcmTokenRequest(BaseModel):
    fcm_token: str


class PushPayload(BaseModel):
    title: str
    body: str
    data: dict = {}


@router.post("/fcm/register", summary="FCM 토큰 등록")
async def register_fcm_token(
    req: FcmTokenRequest,
    username: str = Depends(get_current_user),
):
    """
    앱이 발급받은 FCM 토큰을 서버에 등록합니다.
    서버에서 리마인더/알람 알림을 보낼 때 이 토큰을 사용합니다.
    """
    _fcm_tokens[username] = req.fcm_token
    log.info(f"FCM 토큰 등록: user={username}")
    return {"status": "ok", "user": username}


@router.post("/push/send", summary="푸시 알림 직접 발송 (관리자)")
async def send_push(
    payload: PushPayload,
    username: str = Depends(get_current_user),
):
    """사용자에게 푸시 알림을 발송합니다."""
    token = _fcm_tokens.get(username)
    if not token:
        raise HTTPException(status_code=404, detail="FCM 토큰이 등록되지 않았어요.")

    result = await _send_fcm(token, payload.title, payload.body, payload.data)
    return {"status": "sent", "result": result}


async def push_reminder_to_user(username: str, content: str):
    """서버 내부에서 리마인더 알림을 사용자에게 발송합니다."""
    token = _fcm_tokens.get(username)
    if not token:
        log.info(f"FCM 토큰 없음 (user={username}), 알림 스킵")
        return
    await _send_fcm(token, "루이스 리마인더", content, {})


async def _send_fcm(token: str, title: str, body: str, data: dict) -> dict:
    """
    Firebase Cloud Messaging으로 푸시를 발송합니다.
    실제 배포 시 firebase-admin SDK로 교체하세요.

    pip install firebase-admin
    """
    try:
        import firebase_admin
        from firebase_admin import messaging, credentials

        if not firebase_admin._apps:
            # GOOGLE_APPLICATION_CREDENTIALS 환경변수로 서비스 계정 키 경로 지정
            cred = credentials.ApplicationDefault()
            firebase_admin.initialize_app(cred)

        message = messaging.Message(
            notification=messaging.Notification(title=title, body=body),
            data={k: str(v) for k, v in data.items()},
            token=token,
        )
        response = messaging.send(message)
        log.info(f"FCM 발송 성공: {response}")
        return {"message_id": response}

    except ImportError:
        log.warning("firebase-admin 미설치. 푸시 발송 스킵.")
        return {"status": "skipped", "reason": "firebase-admin not installed"}
    except Exception as exc:
        log.error(f"FCM 발송 실패: {exc}", exc_info=True)
        return {"status": "failed", "error": str(exc)}

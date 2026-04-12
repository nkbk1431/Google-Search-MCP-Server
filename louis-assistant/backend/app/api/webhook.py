"""
루이스 개인비서 - 웹훅 API
FCM 토큰 등록 및 서버-to-클라이언트 푸시 발송.
"""
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.auth import get_current_user

log = logging.getLogger("louis.api.webhook")

router = APIRouter()


def _get_fcm_token(username: str) -> str | None:
    """DB에서 사용자의 FCM 토큰을 조회합니다."""
    try:
        from app.db.models import FcmToken
        from app.db.session import get_sync_db
        with get_sync_db() as db:
            row = db.query(FcmToken).filter(FcmToken.user_id == username).first()
            return row.token if row else None
    except Exception as exc:
        log.warning(f"FCM 토큰 조회 실패: {exc}")
        return None


def _save_fcm_token(username: str, token: str) -> None:
    """FCM 토큰을 DB에 저장합니다 (없으면 INSERT, 있으면 UPDATE)."""
    from datetime import datetime
    try:
        from app.db.models import FcmToken
        from app.db.session import get_sync_db
        with get_sync_db() as db:
            row = db.query(FcmToken).filter(FcmToken.user_id == username).first()
            if row:
                row.token = token
                row.updated_at = datetime.now()
            else:
                db.add(FcmToken(user_id=username, token=token))
            db.commit()
    except Exception as exc:
        log.error(f"FCM 토큰 저장 실패: {exc}", exc_info=True)


class FcmTokenRequest(BaseModel):
    fcm_token: str = Field(..., min_length=1, max_length=512)


class PushPayload(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    body: str = Field(..., min_length=1, max_length=1000)
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
    _save_fcm_token(username, req.fcm_token)
    log.info(f"FCM 토큰 등록: user={username}")
    return {"status": "ok", "user": username}


@router.delete("/fcm/unregister", summary="FCM 토큰 삭제")
async def unregister_fcm_token(username: str = Depends(get_current_user)):
    """로그아웃 시 FCM 토큰을 삭제합니다."""
    try:
        from app.db.models import FcmToken
        from app.db.session import get_sync_db
        with get_sync_db() as db:
            db.query(FcmToken).filter(FcmToken.user_id == username).delete()
            db.commit()
    except Exception as exc:
        log.error(f"FCM 토큰 삭제 실패: {exc}")
    return {"status": "ok"}


@router.post("/push/send", summary="푸시 알림 직접 발송 (관리자)")
async def send_push(
    payload: PushPayload,
    username: str = Depends(get_current_user),
):
    """사용자에게 푸시 알림을 발송합니다."""
    token = _get_fcm_token(username)
    if not token:
        raise HTTPException(status_code=404, detail="FCM 토큰이 등록되지 않았어요.")

    result = await _send_fcm(token, payload.title, payload.body, payload.data)
    return {"status": "sent", "result": result}


async def push_reminder_to_user(username: str, content: str):
    """서버 내부에서 리마인더 알림을 사용자에게 발송합니다."""
    token = _get_fcm_token(username)
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

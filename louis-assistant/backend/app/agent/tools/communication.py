"""
루이스 개인비서 - 커뮤니케이션 도구
Gmail 발송 및 모바일 인텐트(전화/문자) 트리거 신호 반환.
실제 전화/카톡은 Flutter 앱에서 네이티브 인텐트로 처리합니다.
"""
import logging

from langchain_core.tools import tool

from app.services.google_auth import get_google_service
from app.services.quota import google_quota

log = logging.getLogger("louis.tools.communication")


@tool
def send_email(to: str, subject: str, body: str) -> str:
    """Gmail로 이메일을 발송합니다.

    Args:
        to: 수신자 이메일 주소
        subject: 제목
        body: 본문

    Returns:
        발송 결과 메시지
    """
    try:
        google_quota.check()
        import base64
        from email.mime.text import MIMEText

        svc = get_google_service("gmail", "v1")
        msg = MIMEText(body, "plain", "utf-8")
        msg["To"] = to
        msg["Subject"] = subject

        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        svc.users().messages().send(userId="me", body={"raw": raw}).execute()
        return f"'{subject}' 메일을 {to}에게 발송했어요."
    except RuntimeError as exc:
        return str(exc)
    except Exception as exc:
        log.error(f"메일 발송 실패: {exc}", exc_info=True)
        return "메일 발송에 실패했어요."


@tool
def get_phone_intent(contact_name: str) -> str:
    """전화 걸기 신호를 반환합니다 (Flutter 앱이 실제 전화를 겁니다).

    Args:
        contact_name: 연락처 이름 또는 전화번호

    Returns:
        앱에 전달할 인텐트 신호 (JSON 형식)
    """
    import json
    return json.dumps({
        "action": "PHONE_CALL",
        "contact": contact_name,
        "message": f"{contact_name}에게 전화 연결할게요.",
    }, ensure_ascii=False)


@tool
def get_sms_intent(contact_name: str, message: str) -> str:
    """문자 발송 신호를 반환합니다 (Flutter 앱이 실제 문자를 보냅니다).

    Args:
        contact_name: 연락처 이름 또는 전화번호
        message: 문자 내용

    Returns:
        앱에 전달할 인텐트 신호 (JSON 형식)
    """
    import json
    return json.dumps({
        "action": "SEND_SMS",
        "contact": contact_name,
        "message": message,
        "preview": f"{contact_name}에게 문자를 보낼까요? 내용: '{message}'",
    }, ensure_ascii=False)

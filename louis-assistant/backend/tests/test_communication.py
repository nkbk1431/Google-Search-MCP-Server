"""
커뮤니케이션 도구 테스트
전화/문자 인텐트 및 Gmail 발송 기능을 검증합니다.
"""
import json
import pytest
from unittest.mock import patch, MagicMock


# ── get_phone_intent ─────────────────────────────────────

class TestGetPhoneIntent:

    def test_returns_json_string(self):
        from app.agent.tools.communication import get_phone_intent
        result = get_phone_intent.invoke({"contact_name": "엄마"})
        data = json.loads(result)
        assert isinstance(data, dict)

    def test_action_is_phone_call(self):
        from app.agent.tools.communication import get_phone_intent
        result = get_phone_intent.invoke({"contact_name": "아빠"})
        data = json.loads(result)
        assert data["action"] == "PHONE_CALL"

    def test_contact_preserved(self):
        from app.agent.tools.communication import get_phone_intent
        result = get_phone_intent.invoke({"contact_name": "김철수"})
        data = json.loads(result)
        assert data["contact"] == "김철수"

    def test_message_contains_contact(self):
        from app.agent.tools.communication import get_phone_intent
        result = get_phone_intent.invoke({"contact_name": "친구"})
        data = json.loads(result)
        assert "친구" in data["message"]

    def test_phone_number_as_contact(self):
        """전화번호도 연락처로 허용됩니다."""
        from app.agent.tools.communication import get_phone_intent
        result = get_phone_intent.invoke({"contact_name": "010-1234-5678"})
        data = json.loads(result)
        assert data["contact"] == "010-1234-5678"
        assert data["action"] == "PHONE_CALL"


# ── get_sms_intent ───────────────────────────────────────

class TestGetSmsIntent:

    def test_returns_json_string(self):
        from app.agent.tools.communication import get_sms_intent
        result = get_sms_intent.invoke({"contact_name": "엄마", "message": "밥 먹었어요"})
        data = json.loads(result)
        assert isinstance(data, dict)

    def test_action_is_send_sms(self):
        from app.agent.tools.communication import get_sms_intent
        result = get_sms_intent.invoke({"contact_name": "친구", "message": "안녕"})
        data = json.loads(result)
        assert data["action"] == "SEND_SMS"

    def test_contact_and_message_preserved(self):
        from app.agent.tools.communication import get_sms_intent
        result = get_sms_intent.invoke({"contact_name": "팀장님", "message": "오늘 회의 취소입니다"})
        data = json.loads(result)
        assert data["contact"] == "팀장님"
        assert data["message"] == "오늘 회의 취소입니다"

    def test_preview_contains_message(self):
        from app.agent.tools.communication import get_sms_intent
        result = get_sms_intent.invoke({"contact_name": "동생", "message": "집에 언제 와?"})
        data = json.loads(result)
        assert "집에 언제 와?" in data["preview"]

    def test_empty_message_allowed(self):
        from app.agent.tools.communication import get_sms_intent
        result = get_sms_intent.invoke({"contact_name": "누군가", "message": ""})
        data = json.loads(result)
        assert data["action"] == "SEND_SMS"


# ── send_email ───────────────────────────────────────────

class TestSendEmail:

    def test_send_email_success(self):
        from app.agent.tools.communication import send_email

        mock_service = MagicMock()
        mock_service.users.return_value.messages.return_value.send.return_value.execute.return_value = {
            "id": "msg_001"
        }

        with patch("app.agent.tools.communication.get_google_service", return_value=mock_service), \
             patch("app.agent.tools.communication.google_quota") as mock_quota:
            mock_quota.check.return_value = None
            result = send_email.invoke({
                "to": "test@example.com",
                "subject": "테스트 메일",
                "body": "안녕하세요. 테스트입니다.",
            })

        assert "테스트 메일" in result
        assert "test@example.com" in result

    def test_send_email_quota_exceeded(self):
        from app.agent.tools.communication import send_email

        with patch("app.agent.tools.communication.google_quota") as mock_quota:
            mock_quota.check.side_effect = RuntimeError("API 호출 한도를 초과했어요.")
            result = send_email.invoke({
                "to": "test@example.com",
                "subject": "제목",
                "body": "본문",
            })

        assert "한도" in result or "초과" in result

    def test_send_email_api_error(self):
        from app.agent.tools.communication import send_email

        mock_service = MagicMock()
        mock_service.users.return_value.messages.return_value.send.return_value.execute.side_effect = \
            Exception("Google API 오류")

        with patch("app.agent.tools.communication.get_google_service", return_value=mock_service), \
             patch("app.agent.tools.communication.google_quota") as mock_quota:
            mock_quota.check.return_value = None
            result = send_email.invoke({
                "to": "test@example.com",
                "subject": "제목",
                "body": "본문",
            })

        assert "실패" in result

    def test_send_email_google_auth_error(self):
        """Google 인증 실패 시 적절한 메시지 반환."""
        from app.agent.tools.communication import send_email

        with patch("app.agent.tools.communication.get_google_service",
                   side_effect=RuntimeError("Google 인증이 필요해요.")), \
             patch("app.agent.tools.communication.google_quota") as mock_quota:
            mock_quota.check.return_value = None
            result = send_email.invoke({
                "to": "test@example.com",
                "subject": "제목",
                "body": "본문",
            })

        assert "인증" in result or "Google" in result

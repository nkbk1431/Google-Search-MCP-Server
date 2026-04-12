"""
웹훅 API 통합 테스트
FCM 토큰 등록/삭제 및 푸시 발송 엔드포인트를 검증합니다.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from app.main import app

client = TestClient(app)


# ── 인증 헬퍼 ────────────────────────────────────────────

def _token(username: str = "admin", password: str = "louis1234") -> dict:
    resp = client.post(
        "/api/v1/auth/token",
        data={"username": username, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert resp.status_code == 200
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


# ── FCM 토큰 등록 ─────────────────────────────────────────

class TestFcmRegister:

    def test_register_fcm_token_success(self):
        with patch("app.api.webhook._save_fcm_token") as mock_save:
            resp = client.post(
                "/api/v1/webhook/fcm/register",
                json={"fcm_token": "fake-fcm-token-abc123"},
                headers=_token(),
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["user"] == "admin"
        mock_save.assert_called_once_with("admin", "fake-fcm-token-abc123")

    def test_register_fcm_requires_auth(self):
        resp = client.post(
            "/api/v1/webhook/fcm/register",
            json={"fcm_token": "token"},
        )
        assert resp.status_code == 401

    def test_register_fcm_empty_token_rejected(self):
        resp = client.post(
            "/api/v1/webhook/fcm/register",
            json={"fcm_token": ""},
            headers=_token(),
        )
        assert resp.status_code == 422

    def test_register_fcm_overwrites_existing(self):
        """동일 유저의 토큰을 두 번 등록하면 두 번째로 덮어씁니다."""
        with patch("app.api.webhook._save_fcm_token") as mock_save:
            client.post(
                "/api/v1/webhook/fcm/register",
                json={"fcm_token": "token-v1"},
                headers=_token(),
            )
            resp = client.post(
                "/api/v1/webhook/fcm/register",
                json={"fcm_token": "token-v2"},
                headers=_token(),
            )
        assert resp.status_code == 200
        assert mock_save.call_count == 2
        # 두 번째 호출 인자가 token-v2 인지 확인
        assert mock_save.call_args_list[1][0][1] == "token-v2"


# ── FCM 토큰 삭제 ─────────────────────────────────────────

class TestFcmUnregister:

    def test_unregister_fcm_token(self):
        with patch("app.api.webhook.get_sync_db") as mock_db:
            mock_ctx = MagicMock()
            mock_ctx.__enter__ = MagicMock(return_value=mock_ctx)
            mock_ctx.__exit__ = MagicMock(return_value=False)
            mock_db.return_value = mock_ctx

            resp = client.delete(
                "/api/v1/webhook/fcm/unregister",
                headers=_token(),
            )

        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_unregister_requires_auth(self):
        resp = client.delete("/api/v1/webhook/fcm/unregister")
        assert resp.status_code == 401


# ── 푸시 발송 ─────────────────────────────────────────────

class TestSendPush:

    def test_send_push_no_token_returns_404(self):
        with patch("app.api.webhook._get_fcm_token", return_value=None):
            resp = client.post(
                "/api/v1/webhook/push/send",
                json={"title": "테스트", "body": "알림 내용"},
                headers=_token(),
            )
        assert resp.status_code == 404

    def test_send_push_with_token(self):
        with patch("app.api.webhook._get_fcm_token", return_value="some-fcm-token"), \
             patch("app.api.webhook._send_fcm", return_value={"message_id": "msg_001"}) as mock_send:
            resp = client.post(
                "/api/v1/webhook/push/send",
                json={"title": "루이스 알림", "body": "회의 10분 전입니다"},
                headers=_token(),
            )
        assert resp.status_code == 200
        assert resp.json()["status"] == "sent"
        mock_send.assert_called_once()

    def test_send_push_requires_auth(self):
        resp = client.post(
            "/api/v1/webhook/push/send",
            json={"title": "test", "body": "body"},
        )
        assert resp.status_code == 401

    def test_send_push_empty_title_rejected(self):
        resp = client.post(
            "/api/v1/webhook/push/send",
            json={"title": "", "body": "본문"},
            headers=_token(),
        )
        assert resp.status_code == 422


# ── push_reminder_to_user (내부 함수) ────────────────────

class TestPushReminderToUser:

    @pytest.mark.anyio
    async def test_push_reminder_skips_when_no_token(self):
        from app.api.webhook import push_reminder_to_user

        with patch("app.api.webhook._get_fcm_token", return_value=None) as mock_get, \
             patch("app.api.webhook._send_fcm") as mock_send:
            await push_reminder_to_user("alice", "약 먹을 시간이에요")

        mock_send.assert_not_called()

    @pytest.mark.anyio
    async def test_push_reminder_sends_when_token_exists(self):
        from app.api.webhook import push_reminder_to_user

        with patch("app.api.webhook._get_fcm_token", return_value="valid-token"), \
             patch("app.api.webhook._send_fcm", return_value={"status": "ok"}) as mock_send:
            await push_reminder_to_user("alice", "약 먹을 시간이에요")

        mock_send.assert_called_once_with(
            "valid-token",
            "루이스 리마인더",
            "약 먹을 시간이에요",
            {},
        )

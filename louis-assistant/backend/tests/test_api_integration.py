"""
API 통합 테스트
FastAPI TestClient를 사용하여 실제 엔드포인트를 테스트합니다.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, MagicMock

from app.main import app

client = TestClient(app)


# ── 인증 헬퍼 ─────────────────────────────────────────────────────────

def get_test_token(username: str = "admin", password: str = "louis1234") -> str:
    """테스트용 액세스 토큰을 발급합니다."""
    resp = client.post(
        "/api/v1/auth/token",
        data={"username": username, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert resp.status_code == 200
    return resp.json()["access_token"]


def auth_headers(token: str = None) -> dict:
    token = token or get_test_token()
    return {"Authorization": f"Bearer {token}"}


# ── 헬스 체크 ─────────────────────────────────────────────────────────

class TestHealthEndpoints:

    def test_root_returns_ok(self):
        resp = client.get("/")
        assert resp.status_code == 200
        assert "루이스" in resp.json()["message"]

    def test_health_returns_ok(self):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "llm_model" in data


# ── 인증 API ──────────────────────────────────────────────────────────

class TestAuthEndpoints:

    def test_login_success(self):
        resp = client.post(
            "/api/v1/auth/token",
            data={"username": "admin", "password": "louis1234"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self):
        resp = client.post(
            "/api/v1/auth/token",
            data={"username": "admin", "password": "wrongpass"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert resp.status_code == 401

    def test_login_unknown_user(self):
        resp = client.post(
            "/api/v1/auth/token",
            data={"username": "nobody", "password": "pass"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert resp.status_code == 401

    def test_register_new_user(self):
        resp = client.post(
            "/api/v1/auth/register",
            json={"username": "testuser_ci", "password": "testpass123"},
        )
        # 201 또는 409 (이미 존재하는 경우)
        assert resp.status_code in (201, 409)
        if resp.status_code == 201:
            assert "access_token" in resp.json()

    def test_register_short_password(self):
        resp = client.post(
            "/api/v1/auth/register",
            json={"username": "newuser2", "password": "short"},
        )
        assert resp.status_code == 422  # Pydantic 검증 실패

    def test_register_invalid_username(self):
        resp = client.post(
            "/api/v1/auth/register",
            json={"username": "user@name!", "password": "validpass123"},
        )
        assert resp.status_code == 422

    def test_refresh_token(self):
        # 로그인 후 리프레시 토큰 획득
        login = client.post(
            "/api/v1/auth/token",
            data={"username": "admin", "password": "louis1234"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        refresh_token = login.json()["refresh_token"]

        # 리프레시
        resp = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    def test_refresh_invalid_token(self):
        resp = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid.jwt.token"},
        )
        assert resp.status_code == 401

    def test_get_me(self):
        resp = client.get("/api/v1/auth/me", headers=auth_headers())
        assert resp.status_code == 200
        assert resp.json()["username"] == "admin"

    def test_get_me_without_token(self):
        resp = client.get("/api/v1/auth/me")
        assert resp.status_code == 401


# ── 채팅 API ──────────────────────────────────────────────────────────

class TestChatEndpoints:

    def test_chat_requires_auth(self):
        resp = client.post("/api/v1/chat", json={"text": "안녕"})
        assert resp.status_code == 401

    def test_chat_success(self):
        mock_result = {
            "reply": "안녕하세요! 무엇을 도와드릴까요?",
            "tool_calls": [],
            "tokens": {"in": 50, "out": 20},
        }
        with patch("app.api.chat.get_agent") as mock_get_agent:
            mock_agent = MagicMock()
            mock_agent.chat = AsyncMock(return_value=mock_result)
            mock_get_agent.return_value = mock_agent

            resp = client.post(
                "/api/v1/chat",
                json={"text": "안녕하세요", "session_id": "test-session"},
                headers=auth_headers(),
            )
        assert resp.status_code == 200
        data = resp.json()
        assert "reply" in data
        assert data["reply"] == "안녕하세요! 무엇을 도와드릴까요?"

    def test_chat_empty_text_rejected(self):
        resp = client.post(
            "/api/v1/chat",
            json={"text": "", "session_id": "test"},
            headers=auth_headers(),
        )
        assert resp.status_code == 422  # min_length=1

    def test_chat_too_long_text_rejected(self):
        resp = client.post(
            "/api/v1/chat",
            json={"text": "a" * 501, "session_id": "test"},
            headers=auth_headers(),
        )
        assert resp.status_code == 422  # max_length=500

    def test_get_usage(self):
        resp = client.get("/api/v1/chat/usage", headers=auth_headers())
        assert resp.status_code == 200
        data = resp.json()
        assert "today_tokens" in data
        assert "daily_limit" in data
        assert "remaining" in data


# ── 선호도 API ────────────────────────────────────────────────────────

class TestPreferencesEndpoints:

    def test_get_preferences_empty(self):
        with patch("app.services.personalization.get_sync_db") as mock_db:
            mock_ctx = MagicMock()
            mock_ctx.__enter__ = MagicMock(return_value=mock_ctx)
            mock_ctx.__exit__ = MagicMock(return_value=False)
            mock_ctx.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
            mock_db.return_value = mock_ctx

            resp = client.get("/api/v1/preferences", headers=auth_headers())

        assert resp.status_code == 200
        assert resp.json()["preferences"] == {}

    def test_set_preference(self):
        with patch("app.services.personalization.get_sync_db") as mock_db:
            mock_ctx = MagicMock()
            mock_ctx.__enter__ = MagicMock(return_value=mock_ctx)
            mock_ctx.__exit__ = MagicMock(return_value=False)
            mock_ctx.query.return_value.filter.return_value.first.return_value = None
            mock_db.return_value = mock_ctx

            resp = client.put(
                "/api/v1/preferences/home_city",
                params={"value": "서울"},
                headers=auth_headers(),
            )

        assert resp.status_code == 200
        assert resp.json()["value"] == "서울"

"""
미디어 도구 테스트
search_music (Spotify) 및 search_youtube 기능을 검증합니다.
"""
import json
import pytest
from unittest.mock import patch, MagicMock


# ── search_youtube ────────────────────────────────────────

class TestSearchYoutube:

    def test_returns_open_youtube_action(self):
        from app.agent.tools.media import search_youtube

        result = search_youtube.invoke({"query": "강아지 영상"})
        data = json.loads(result)
        assert data["action"] == "OPEN_YOUTUBE"

    def test_query_preserved(self):
        from app.agent.tools.media import search_youtube

        result = search_youtube.invoke({"query": "아이유 Celebrity"})
        data = json.loads(result)
        assert data["query"] == "아이유 Celebrity"

    def test_message_contains_query(self):
        from app.agent.tools.media import search_youtube

        result = search_youtube.invoke({"query": "요리 레시피"})
        data = json.loads(result)
        assert "요리 레시피" in data["message"]

    def test_returns_json_string(self):
        from app.agent.tools.media import search_youtube

        result = search_youtube.invoke({"query": "테스트"})
        assert isinstance(result, str)
        parsed = json.loads(result)
        assert isinstance(parsed, dict)


# ── search_music (Spotify 없을 때) ────────────────────────

class TestSearchMusicNoSpotify:

    def test_no_spotify_key_returns_play_music_intent(self):
        """Spotify 키 없으면 PLAY_MUSIC 인텐트 반환."""
        from app.agent.tools.media import search_music

        with patch("app.agent.tools.media.settings") as mock_settings:
            mock_settings.spotify_client_id = ""
            mock_settings.spotify_client_secret = ""
            result = search_music.invoke({"query": "재즈 음악"})

        data = json.loads(result)
        assert data["action"] == "PLAY_MUSIC"
        assert data["query"] == "재즈 음악"

    def test_no_spotify_message_contains_query(self):
        from app.agent.tools.media import search_music

        with patch("app.agent.tools.media.settings") as mock_settings:
            mock_settings.spotify_client_id = ""
            mock_settings.spotify_client_secret = ""
            result = search_music.invoke({"query": "발라드"})

        data = json.loads(result)
        assert "발라드" in data["message"]


# ── search_music (Spotify 있을 때) ────────────────────────

class TestSearchMusicWithSpotify:

    def _mock_spotify_token(self):
        token_resp = MagicMock()
        token_resp.json.return_value = {"access_token": "test-token"}
        return token_resp

    def _mock_spotify_search(self, track_name: str, artist_name: str, uri: str):
        search_resp = MagicMock()
        search_resp.json.return_value = {
            "tracks": {
                "items": [{
                    "name": track_name,
                    "artists": [{"name": artist_name}],
                    "uri": uri,
                }]
            }
        }
        return search_resp

    def test_spotify_search_success(self):
        from app.agent.tools.media import search_music

        with patch("app.agent.tools.media.settings") as mock_settings, \
             patch("app.agent.tools.media.requests.post",
                   return_value=self._mock_spotify_token()), \
             patch("app.agent.tools.media.requests.get",
                   return_value=self._mock_spotify_search(
                       "Celebrity", "아이유", "spotify:track:abc123")):
            mock_settings.spotify_client_id = "client-id"
            mock_settings.spotify_client_secret = "client-secret"
            result = search_music.invoke({"query": "아이유 Celebrity"})

        data = json.loads(result)
        assert data["action"] == "PLAY_SPOTIFY_URI"
        assert data["uri"] == "spotify:track:abc123"
        assert "Celebrity" in data["message"]
        assert "아이유" in data["message"]

    def test_spotify_search_no_results(self):
        from app.agent.tools.media import search_music

        no_result_resp = MagicMock()
        no_result_resp.json.return_value = {"tracks": {"items": []}}

        with patch("app.agent.tools.media.settings") as mock_settings, \
             patch("app.agent.tools.media.requests.post",
                   return_value=self._mock_spotify_token()), \
             patch("app.agent.tools.media.requests.get", return_value=no_result_resp):
            mock_settings.spotify_client_id = "id"
            mock_settings.spotify_client_secret = "secret"
            result = search_music.invoke({"query": "없는곡XYZ9999"})

        assert "찾지 못했어요" in result or "없는곡" in result

    def test_spotify_token_failure_returns_fallback_intent(self):
        """Spotify 토큰 발급 실패 → PLAY_MUSIC 폴백."""
        from app.agent.tools.media import search_music

        with patch("app.agent.tools.media.settings") as mock_settings, \
             patch("app.agent.tools.media.requests.post",
                   side_effect=Exception("연결 실패")):
            mock_settings.spotify_client_id = "id"
            mock_settings.spotify_client_secret = "secret"
            result = search_music.invoke({"query": "재즈"})

        # 토큰 실패 → _get_spotify_token returns None → PLAY_MUSIC 폴백
        data = json.loads(result)
        assert data["action"] == "PLAY_MUSIC"

    def test_spotify_search_exception_handled(self):
        """Spotify 검색 API 오류 시 에러 메시지 반환."""
        from app.agent.tools.media import search_music

        with patch("app.agent.tools.media.settings") as mock_settings, \
             patch("app.agent.tools.media.requests.post",
                   return_value=self._mock_spotify_token()), \
             patch("app.agent.tools.media.requests.get",
                   side_effect=Exception("API 오류")):
            mock_settings.spotify_client_id = "id"
            mock_settings.spotify_client_secret = "secret"
            result = search_music.invoke({"query": "테스트"})

        assert "실패" in result

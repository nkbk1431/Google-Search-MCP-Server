"""
루이스 개인비서 - 미디어 도구
Spotify 재생 제어 및 YouTube 검색.
실제 재생은 Flutter 앱이 네이티브 SDK로 처리합니다.
"""
import logging

import requests
from langchain_core.tools import tool

from app.config import settings

log = logging.getLogger("louis.tools.media")


def _get_spotify_token() -> str | None:
    """Spotify Client Credentials 토큰 발급."""
    if not settings.spotify_client_id or not settings.spotify_client_secret:
        return None
    try:
        import base64
        creds = base64.b64encode(
            f"{settings.spotify_client_id}:{settings.spotify_client_secret}".encode()
        ).decode()
        r = requests.post(
            "https://accounts.spotify.com/api/token",
            headers={"Authorization": f"Basic {creds}"},
            data={"grant_type": "client_credentials"},
            timeout=5,
        )
        return r.json().get("access_token")
    except Exception as exc:
        log.error(f"Spotify 토큰 발급 실패: {exc}")
        return None


@tool
def search_music(query: str) -> str:
    """Spotify에서 음악을 검색합니다.

    Args:
        query: 검색어 (곡 이름, 아티스트, 장르 등)

    Returns:
        검색 결과 및 재생 신호
    """
    token = _get_spotify_token()
    if not token:
        import json
        return json.dumps({
            "action": "PLAY_MUSIC",
            "query": query,
            "message": f"'{query}' 음악을 재생할게요.",
        }, ensure_ascii=False)

    try:
        r = requests.get(
            "https://api.spotify.com/v1/search",
            headers={"Authorization": f"Bearer {token}"},
            params={"q": query, "type": "track", "market": "KR", "limit": 1},
            timeout=5,
        )
        tracks = r.json().get("tracks", {}).get("items", [])
        if not tracks:
            return f"'{query}' 음악을 찾지 못했어요."

        track = tracks[0]
        name = track["name"]
        artist = track["artists"][0]["name"]
        uri = track["uri"]

        import json
        return json.dumps({
            "action": "PLAY_SPOTIFY_URI",
            "uri": uri,
            "message": f"{artist}의 '{name}' 재생할게요.",
        }, ensure_ascii=False)

    except Exception as exc:
        log.error(f"음악 검색 실패: {exc}", exc_info=True)
        return "음악 검색에 실패했어요."


@tool
def search_youtube(query: str) -> str:
    """YouTube에서 동영상을 검색합니다.

    Args:
        query: 검색어

    Returns:
        검색 결과 및 재생 신호
    """
    import json
    return json.dumps({
        "action": "OPEN_YOUTUBE",
        "query": query,
        "message": f"유튜브에서 '{query}' 검색할게요.",
    }, ensure_ascii=False)

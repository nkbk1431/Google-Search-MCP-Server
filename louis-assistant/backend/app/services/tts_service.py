"""
루이스 개인비서 - TTS 서비스
ElevenLabs API 기반 고품질 한국어 TTS. API 키 없으면 텍스트만 반환.

엔드포인트: POST /api/v1/tts
"""
import logging
from io import BytesIO

import requests

from app.config import settings

log = logging.getLogger("louis.tts")

# ElevenLabs 한국어 추천 보이스 ID
# Rachel(21m00Tcm4TlvDq8ikWAM), Domi(AZnzlk1XvdvUeBnXmlld) — 영어
# 한국어는 멀티링구얼 V2 모델 사용
_DEFAULT_VOICE_ID = "21m00Tcm4TlvDq8ikWAM"
_ELEVEN_API_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
_ELEVEN_STREAM_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream"


class TTSService:
    """텍스트를 오디오로 변환합니다."""

    def synthesize(
        self,
        text: str,
        voice_id: str = _DEFAULT_VOICE_ID,
        stream: bool = False,
    ) -> bytes | None:
        """
        텍스트를 MP3 오디오로 변환합니다.

        Args:
            text: 읽을 텍스트
            voice_id: ElevenLabs 보이스 ID
            stream: True면 스트리밍 응답 사용

        Returns:
            MP3 오디오 bytes, 실패 시 None
        """
        if not settings.elevenlabs_api_key:
            log.debug("ElevenLabs API 키 없음 — TTS 비활성화")
            return None

        # 텍스트 전처리: 너무 길면 잘라냄
        clean_text = _preprocess(text)
        if not clean_text:
            return None

        url_template = _ELEVEN_STREAM_URL if stream else _ELEVEN_API_URL
        url = url_template.format(voice_id=voice_id)

        try:
            resp = requests.post(
                url,
                headers={
                    "xi-api-key": settings.elevenlabs_api_key,
                    "Content-Type": "application/json",
                    "Accept": "audio/mpeg",
                },
                json={
                    "text": clean_text,
                    "model_id": "eleven_multilingual_v2",
                    "voice_settings": {
                        "stability": 0.5,
                        "similarity_boost": 0.75,
                        "style": 0.0,
                        "use_speaker_boost": True,
                    },
                },
                stream=stream,
                timeout=15,
            )
            resp.raise_for_status()

            if stream:
                buf = BytesIO()
                for chunk in resp.iter_content(chunk_size=4096):
                    if chunk:
                        buf.write(chunk)
                return buf.getvalue()
            else:
                return resp.content

        except requests.Timeout:
            log.warning("ElevenLabs TTS 타임아웃")
            return None
        except requests.HTTPError as e:
            log.warning(f"ElevenLabs TTS HTTP 오류: {e.response.status_code}")
            return None
        except Exception as exc:
            log.error(f"ElevenLabs TTS 실패: {exc}", exc_info=True)
            return None

    def list_voices(self) -> list[dict]:
        """사용 가능한 보이스 목록을 반환합니다."""
        if not settings.elevenlabs_api_key:
            return []
        try:
            resp = requests.get(
                "https://api.elevenlabs.io/v1/voices",
                headers={"xi-api-key": settings.elevenlabs_api_key},
                timeout=5,
            )
            resp.raise_for_status()
            return resp.json().get("voices", [])
        except Exception as exc:
            log.warning(f"보이스 목록 조회 실패: {exc}")
            return []


def _preprocess(text: str, max_chars: int = 500) -> str:
    """TTS용 텍스트 전처리."""
    # JSON, URL, 이모지 등 제거
    import re
    # URL 제거
    text = re.sub(r"https?://\S+", "링크", text)
    # JSON 블록 제거
    text = re.sub(r"\{.*?\}", "", text, flags=re.DOTALL)
    # 마크다운 기호 제거
    text = re.sub(r"[*_`#|]", "", text)
    # 연속 공백/줄바꿈 정리
    text = re.sub(r"\s+", " ", text).strip()
    # 길이 제한
    if len(text) > max_chars:
        # 문장 경계에서 자르기
        cut = text[:max_chars].rsplit(". ", 1)
        text = cut[0] + "." if len(cut) > 1 else text[:max_chars]
    return text


# 싱글턴
_tts_service: TTSService | None = None


def get_tts_service() -> TTSService:
    global _tts_service
    if _tts_service is None:
        _tts_service = TTSService()
    return _tts_service

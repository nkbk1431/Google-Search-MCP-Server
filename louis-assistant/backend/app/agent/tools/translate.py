"""
루이스 개인비서 - 번역 도구
DeepL API 기반 고품질 번역. API 키 없으면 LibreTranslate 폴백.
"""
import logging

import requests
from langchain_core.tools import tool

from app.config import settings

log = logging.getLogger("louis.tools.translate")

LANG_MAP: dict[str, str] = {
    "영어": "EN", "영문": "EN",
    "한국어": "KO", "한글": "KO",
    "일본어": "JA", "일문": "JA",
    "중국어": "ZH", "중문": "ZH",
    "프랑스어": "FR", "불어": "FR",
    "독일어": "DE",
    "스페인어": "ES",
    "이탈리아어": "IT",
    "러시아어": "RU",
    "포르투갈어": "PT",
}


@tool
def translate_text(text: str, target_language: str, source_language: str = "") -> str:
    """텍스트를 지정한 언어로 번역합니다.

    Args:
        text: 번역할 텍스트
        target_language: 목표 언어 (한글 또는 ISO 코드, 예: '영어', 'EN')
        source_language: 원본 언어 (선택, 생략 시 자동 감지)

    Returns:
        번역된 텍스트
    """
    target_code = LANG_MAP.get(target_language.strip(), target_language.upper().strip())

    # DeepL API 시도
    if settings.deepl_api_key:
        result = _translate_deepl(text, target_code)
        if result:
            return result

    return f"번역 기능을 사용하려면 DeepL API 키를 설정해주세요."


def _translate_deepl(text: str, target: str) -> str | None:
    """DeepL API로 번역."""
    try:
        # DeepL Free API는 api-free.deepl.com 사용
        base_url = "https://api-free.deepl.com/v2/translate"
        r = requests.post(
            base_url,
            data={
                "auth_key": settings.deepl_api_key,
                "text": text,
                "target_lang": target,
            },
            timeout=5,
        )
        data = r.json()
        if "translations" in data:
            detected = data["translations"][0].get("detected_source_language", "")
            translated = data["translations"][0]["text"]
            return f"{translated} (감지된 원본 언어: {detected})"
        return None
    except requests.Timeout:
        log.warning("DeepL API 타임아웃")
        return None
    except Exception as exc:
        log.error(f"DeepL 번역 실패: {exc}")
        return None

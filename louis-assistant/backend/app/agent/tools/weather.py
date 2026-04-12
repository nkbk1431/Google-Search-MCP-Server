"""
루이스 개인비서 - 날씨 도구
OpenWeatherMap API로 현재 날씨 + 오늘 최고/최저 조회 및 옷차림 추천.
"""
import json
import logging
import time
from functools import wraps
from typing import Any

import requests
from langchain_core.tools import tool

from app.config import settings

log = logging.getLogger("louis.tools.weather")

# 한국 도시명 → 영문 변환 테이블
CITY_MAP: dict[str, str] = {
    "서울": "Seoul", "부산": "Busan", "대구": "Daegu", "인천": "Incheon",
    "광주": "Gwangju", "대전": "Daejeon", "울산": "Ulsan", "수원": "Suwon",
    "고양": "Goyang", "용인": "Yongin", "창원": "Changwon", "성남": "Seongnam",
    "청주": "Cheongju", "제주": "Jeju", "전주": "Jeonju", "안산": "Ansan",
    "평택": "Pyeongtaek", "천안": "Cheonan", "김해": "Gimhae", "포항": "Pohang",
}

# 간단한 TTL 캐시 구현
_cache: dict[str, tuple[float, Any]] = {}
_CACHE_TTL = 600  # 10분


def _ttl_cache(key: str, ttl: int = _CACHE_TTL):
    """TTL 캐시 데코레이터용 헬퍼."""
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            cache_key = f"{key}:{args}:{kwargs}"
            now = time.time()
            if cache_key in _cache:
                ts, val = _cache[cache_key]
                if now - ts < ttl:
                    log.debug(f"캐시 히트: {cache_key}")
                    return val
            result = fn(*args, **kwargs)
            _cache[cache_key] = (now, result)
            return result
        return wrapper
    return decorator


def _fetch_weather_raw(city_en: str) -> tuple[dict, dict]:
    """OpenWeatherMap에서 현재 날씨 + 예보 데이터를 가져옵니다."""
    key = settings.openweather_api_key
    base_params = {"q": city_en, "appid": key, "units": "metric", "lang": "kr"}

    current = requests.get(
        "https://api.openweathermap.org/data/2.5/weather",
        params=base_params, timeout=5
    ).json()

    forecast = requests.get(
        "https://api.openweathermap.org/data/2.5/forecast",
        params=base_params, timeout=5
    ).json()

    return current, forecast


@tool
def get_weather(city: str = "Seoul") -> str:
    """현재 날씨와 오늘 최고/최저 기온, 바람, 습도를 조회합니다.

    Args:
        city: 도시 이름 (한글 또는 영문). 기본값 서울.

    Returns:
        JSON 문자열 (city, temp_now, temp_max, temp_min, condition, wind_speed, humidity)
    """
    city_en = CITY_MAP.get(city, city)

    try:
        current, forecast = _fetch_weather_raw(city_en)

        if current.get("cod") != 200:
            return json.dumps({"error": f"도시를 찾을 수 없어요: {city}"}, ensure_ascii=False)

        from datetime import datetime
        today = datetime.now().date()
        day_temps = [
            item["main"]["temp"]
            for item in forecast.get("list", [])
            if datetime.fromtimestamp(item["dt"]).date() == today
        ]
        if not day_temps:
            day_temps = [current["main"]["temp"]]

        result = {
            "city": current["name"],
            "temp_now": round(current["main"]["temp"], 1),
            "temp_max": round(max(day_temps), 1),
            "temp_min": round(min(day_temps), 1),
            "condition": current["weather"][0]["description"],
            "wind_speed": current["wind"]["speed"],
            "humidity": current["main"]["humidity"],
        }
        return json.dumps(result, ensure_ascii=False)

    except requests.Timeout:
        log.warning(f"날씨 API 타임아웃: {city_en}")
        return json.dumps({"error": "날씨 서버 응답이 늦어요. 잠시 후 다시 시도해주세요."}, ensure_ascii=False)
    except Exception as exc:
        log.error(f"날씨 조회 실패: {exc}", exc_info=True)
        return json.dumps({"error": "날씨 조회에 실패했어요."}, ensure_ascii=False)


@tool
def recommend_outfit(weather_json: str) -> str:
    """날씨 정보(JSON)를 바탕으로 오늘 옷차림을 추천합니다.

    Args:
        weather_json: get_weather 도구가 반환한 JSON 문자열

    Returns:
        자연스러운 한국어 옷차림 추천 문장
    """
    try:
        w = json.loads(weather_json)
    except (json.JSONDecodeError, TypeError):
        return "날씨 정보를 불러올 수 없어서 옷차림을 추천하기 어려워요."

    if "error" in w:
        return "날씨 조회에 실패해서 옷차림을 추천하기 어려워요."

    t_max = w.get("temp_max", 20)
    t_min = w.get("temp_min", 10)
    diff = t_max - t_min
    condition = w.get("condition", "")
    wind = w.get("wind_speed", 0)

    # 기온 구간별 상의
    if t_max >= 28:
        top = "반팔이나 민소매"
    elif t_max >= 23:
        top = "반팔"
    elif t_max >= 20:
        top = "긴팔 티셔츠나 얇은 셔츠"
    elif t_max >= 17:
        top = "얇은 가디건이나 맨투맨"
    elif t_max >= 12:
        top = "자켓이나 후드티"
    elif t_max >= 9:
        top = "트렌치코트나 야상"
    elif t_max >= 5:
        top = "코트"
    else:
        top = "두꺼운 패딩"

    extras = []
    if diff >= 10 and t_max >= 15:
        extras.append("일교차가 크니 바람막이나 얇은 겉옷을 챙기세요")
    if wind >= 5:
        extras.append("바람이 강하니 방풍 외투가 좋아요")
    if "비" in condition or "rain" in condition.lower():
        extras.append("우산을 챙기세요")
    if "눈" in condition or "snow" in condition.lower():
        extras.append("미끄러우니 조심하세요")

    reply = f"{top} 추천드려요."
    if extras:
        reply += " " + " ".join(extras) + "."
    return reply

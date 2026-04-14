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


def _build_outfit_advice(w: dict) -> str:
    """날씨 dict에서 옷차림 추천 문장을 생성합니다 (내부 헬퍼).

    기온 구간별 상·하의 조합으로 안내하며, 비/바람/일교차 부가 정보를 추가합니다.
    """
    t_max = w.get("temp_max", 20)
    t_min = w.get("temp_min", 10)
    condition = w.get("condition", "")
    wind = w.get("wind_speed", 0)

    # ── 기온 구간별 코디 조합 ────────────────────────────────
    # t_max 기준으로 낮 최고 기온에 맞는 코디를 먼저 잡고,
    # t_min이 낮으면 아침저녁 레이어링 조언을 추가합니다.

    if t_max >= 28:
        # 한여름
        base = "반팔이나 민소매에 얇은 면 하의를 입으세요."
    elif t_max >= 23:
        # 초여름·늦여름
        base = "반팔을 입으세요."
    elif t_max >= 20:
        # 봄·가을 초입, 낮엔 따뜻함
        base = "반팔에 얇은 가디건이나 셔츠를 걸치면 좋아요."
    elif t_max >= 13:
        # 봄·가을 대표 구간 — 반팔 + 아우터
        base = "반팔에 자켓이나 바람막이 같은 아우터를 입으세요."
    elif t_max >= 9:
        # 초봄·늦가을
        base = "긴팔에 두꺼운 자켓이나 야상을 입으세요."
    elif t_max >= 5:
        # 초겨울
        base = "니트나 후드티에 트렌치코트나 코트를 입으세요."
    elif t_max >= 0:
        # 겨울
        base = "두꺼운 니트에 패딩이나 두꺼운 코트를 입으세요."
    else:
        # 혹한
        base = "두꺼운 패딩을 입으시고, 목도리와 장갑도 꼭 챙기세요."

    # ── 부가 조언 ────────────────────────────────────────────
    extras = []

    # 일교차 또는 아침 추위 경고
    if t_min <= 10 and t_max >= 20:
        extras.append("아침저녁이 많이 쌀쌀하니 겉옷을 꼭 챙기세요")
    elif t_max - t_min >= 10:
        extras.append("일교차가 크니 레이어링을 추천드려요")

    if wind >= 7:
        extras.append("바람이 강하니 방풍 기능이 있는 외투가 좋아요")

    is_rainy = "비" in condition or "rain" in condition.lower() or "drizzle" in condition.lower()
    is_snowy = "눈" in condition or "snow" in condition.lower()
    if is_rainy:
        extras.append("비가 오니 우산을 꼭 챙기세요")
    if is_snowy:
        extras.append("눈이 오니 미끄럼 조심하시고 방수 신발을 신으세요")

    advice = base
    if extras:
        advice += " " + " ".join(extras) + "."
    return advice


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

    return _build_outfit_advice(w)


@tool
def get_weather_and_outfit(city: str = "서울") -> str:
    """현재 날씨와 옷차림 추천을 한 번에 알려줍니다.

    날씨를 묻거나 뭘 입을지 물어볼 때 이 도구를 사용하세요.
    get_weather → recommend_outfit을 순서대로 직접 호출하지 말고 이 도구 하나만 사용하세요.

    Args:
        city: 도시 이름 (한글 또는 영문). 기본값 서울.

    Returns:
        날씨 요약 + 옷차림 추천이 포함된 자연스러운 한국어 문장
    """
    city_en = CITY_MAP.get(city, city)

    try:
        current, forecast = _fetch_weather_raw(city_en)

        if current.get("cod") != 200:
            return f"'{city}' 날씨를 찾을 수 없어요."

        from datetime import datetime as _dt
        today = _dt.now().date()
        day_temps = [
            item["main"]["temp"]
            for item in forecast.get("list", [])
            if _dt.fromtimestamp(item["dt"]).date() == today
        ]
        if not day_temps:
            day_temps = [current["main"]["temp"]]

        t_now = round(current["main"]["temp"], 1)
        t_max = round(max(day_temps), 1)
        t_min = round(min(day_temps), 1)
        condition = current["weather"][0]["description"]
        humidity = current["main"]["humidity"]
        wind = current["wind"]["speed"]

        w = {
            "temp_now": t_now,
            "temp_max": t_max,
            "temp_min": t_min,
            "condition": condition,
            "wind_speed": wind,
            "humidity": humidity,
        }
        outfit = _build_outfit_advice(w)

        # 자연스러운 문장으로 조합
        rain_note = ""
        if "비" in condition or "rain" in condition.lower() or "drizzle" in condition.lower():
            rain_note = " 비가 오고 있어요."
        elif "눈" in condition or "snow" in condition.lower():
            rain_note = " 눈이 오고 있어요."
        elif "맑" in condition or "clear" in condition.lower():
            rain_note = " 맑은 날씨예요."
        elif "흐" in condition or "cloud" in condition.lower():
            rain_note = " 흐린 날씨예요."

        return (
            f"{city} 현재 기온은 {t_now}°C이고, "
            f"오늘 최고 {t_max}°C / 최저 {t_min}°C 예상돼요.{rain_note} "
            f"습도 {humidity}%, 바람 {wind}m/s예요. "
            f"옷차림은 {outfit}"
        )

    except requests.Timeout:
        log.warning(f"날씨 API 타임아웃: {city_en}")
        return "날씨 서버 응답이 늦어요. 잠시 후 다시 시도해주세요."
    except Exception as exc:
        log.error(f"날씨+옷차림 조회 실패: {exc}", exc_info=True)
        return "날씨 조회에 실패했어요."

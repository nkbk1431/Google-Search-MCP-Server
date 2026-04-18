"""
루이스 개인비서 - 날씨 도구
Open-Meteo API (완전 무료, API 키 불필요)로 현재 날씨 + 오늘 최고/최저 조회 및 옷차림 추천.
"""
import json
import logging
import time
from functools import wraps
from typing import Any

import requests
from langchain_core.tools import tool

log = logging.getLogger("louis.tools.weather")

# 한국 도시명 → (위도, 경도, 영문명)
CITY_COORDS: dict[str, tuple[float, float, str]] = {
    "서울":     (37.5665, 126.9780, "Seoul"),
    "부산":     (35.1796, 129.0756, "Busan"),
    "대구":     (35.8714, 128.6014, "Daegu"),
    "인천":     (37.4563, 126.7052, "Incheon"),
    "광주":     (35.1595, 126.8526, "Gwangju"),
    "대전":     (36.3504, 127.3845, "Daejeon"),
    "울산":     (35.5384, 129.3114, "Ulsan"),
    "수원":     (37.2636, 127.0286, "Suwon"),
    "고양":     (37.6584, 126.8320, "Goyang"),
    "용인":     (37.2411, 127.1776, "Yongin"),
    "창원":     (35.2280, 128.6811, "Changwon"),
    "성남":     (37.4449, 127.1388, "Seongnam"),
    "청주":     (36.6424, 127.4890, "Cheongju"),
    "제주":     (33.4996, 126.5312, "Jeju"),
    "전주":     (35.8242, 127.1479, "Jeonju"),
    "안산":     (37.3219, 126.8309, "Ansan"),
    "평택":     (36.9921, 127.1121, "Pyeongtaek"),
    "천안":     (36.8151, 127.1139, "Cheonan"),
    "김해":     (35.2342, 128.8811, "Gimhae"),
    "포항":     (36.0190, 129.3435, "Pohang"),
}

# WMO 날씨 코드 → 한국어 설명
WMO_CODE_KO: dict[int, str] = {
    0: "맑음", 1: "대체로 맑음", 2: "부분적으로 흐림", 3: "흐림",
    45: "안개", 48: "안개",
    51: "이슬비", 53: "이슬비", 55: "짙은 이슬비",
    61: "비", 63: "비", 65: "강한 비",
    71: "눈", 73: "눈", 75: "강한 눈",
    77: "눈알",
    80: "소나기", 81: "소나기", 82: "강한 소나기",
    85: "눈 소나기", 86: "눈 소나기",
    95: "뇌우", 96: "뇌우(우박)", 99: "뇌우(우박)",
}

_cache: dict[str, tuple[float, Any]] = {}
_CACHE_TTL = 600  # 10분


def _ttl_cache(key: str, ttl: int = _CACHE_TTL):
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


def _get_coords(city: str) -> tuple[float, float, str]:
    """도시 이름 → (위도, 경도, 영문명). 미등록 도시는 Open-Meteo 지오코딩으로 조회."""
    if city in CITY_COORDS:
        return CITY_COORDS[city]

    resp = requests.get(
        "https://geocoding-api.open-meteo.com/v1/search",
        params={"name": city, "count": 1, "language": "en", "format": "json"},
        timeout=5,
    ).json()

    results = resp.get("results")
    if not results:
        raise ValueError(f"도시를 찾을 수 없어요: {city}")

    r = results[0]
    return r["latitude"], r["longitude"], r.get("name", city)


def _fetch_weather_raw(city: str) -> tuple[dict, str]:
    """Open-Meteo에서 현재 날씨 + 오늘 최고/최저를 가져옵니다."""
    lat, lon, city_en = _get_coords(city)

    data = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code",
            "daily": "temperature_2m_max,temperature_2m_min",
            "timezone": "Asia/Seoul",
            "forecast_days": 1,
        },
        timeout=5,
    ).json()

    return data, city_en


@tool
def get_weather(city: str = "서울") -> str:
    """현재 날씨와 오늘 최고/최저 기온, 바람, 습도를 조회합니다.

    Args:
        city: 도시 이름 (한글 또는 영문). 기본값 서울.

    Returns:
        JSON 문자열 (city, temp_now, temp_max, temp_min, condition, wind_speed, humidity)
    """
    try:
        data, city_en = _fetch_weather_raw(city)

        current = data.get("current", {})
        daily = data.get("daily", {})
        wmo = current.get("weather_code", 0)

        result = {
            "city": city_en,
            "temp_now": round(current.get("temperature_2m", 0), 1),
            "temp_max": round((daily.get("temperature_2m_max") or [0])[0], 1),
            "temp_min": round((daily.get("temperature_2m_min") or [0])[0], 1),
            "condition": WMO_CODE_KO.get(wmo, "알 수 없음"),
            "wind_speed": current.get("wind_speed_10m", 0),
            "humidity": current.get("relative_humidity_2m", 0),
        }
        return json.dumps(result, ensure_ascii=False)

    except requests.Timeout:
        log.warning(f"날씨 API 타임아웃: {city}")
        return json.dumps({"error": "날씨 서버 응답이 늦어요. 잠시 후 다시 시도해주세요."}, ensure_ascii=False)
    except ValueError as exc:
        return json.dumps({"error": str(exc)}, ensure_ascii=False)
    except Exception as exc:
        log.error(f"날씨 조회 실패: {exc}", exc_info=True)
        return json.dumps({"error": "날씨 조회에 실패했어요."}, ensure_ascii=False)


def _build_outfit_advice(w: dict) -> str:
    """날씨 dict에서 옷차림 추천 문장을 생성합니다."""
    t_max = w.get("temp_max", 20)
    t_min = w.get("temp_min", 10)
    condition = w.get("condition", "")
    wind = w.get("wind_speed", 0)

    if t_max >= 28:
        base = "반팔이나 민소매에 얇은 면 하의를 입으세요."
    elif t_max >= 23:
        base = "반팔을 입으세요."
    elif t_max >= 20:
        base = "반팔에 얇은 가디건이나 셔츠를 걸치면 좋아요."
    elif t_max >= 13:
        base = "반팔에 자켓이나 바람막이 같은 아우터를 입으세요."
    elif t_max >= 9:
        base = "긴팔에 두꺼운 자켓이나 야상을 입으세요."
    elif t_max >= 5:
        base = "니트나 후드티에 트렌치코트나 코트를 입으세요."
    elif t_max >= 0:
        base = "두꺼운 니트에 패딩이나 두꺼운 코트를 입으세요."
    else:
        base = "두꺼운 패딩을 입으시고, 목도리와 장갑도 꼭 챙기세요."

    extras = []
    if t_min <= 10 and t_max >= 20:
        extras.append("아침저녁이 많이 쌀쌀하니 겉옷을 꼭 챙기세요")
    elif t_max - t_min >= 10:
        extras.append("일교차가 크니 레이어링을 추천드려요")

    if wind >= 7:
        extras.append("바람이 강하니 방풍 기능이 있는 외투가 좋아요")

    is_rainy = any(k in condition for k in ("비", "이슬비", "소나기"))
    is_snowy = "눈" in condition
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
    try:
        data, city_en = _fetch_weather_raw(city)

        current = data.get("current", {})
        daily = data.get("daily", {})
        wmo = current.get("weather_code", 0)
        condition = WMO_CODE_KO.get(wmo, "알 수 없음")

        t_now = round(current.get("temperature_2m", 0), 1)
        t_max = round((daily.get("temperature_2m_max") or [0])[0], 1)
        t_min = round((daily.get("temperature_2m_min") or [0])[0], 1)
        humidity = current.get("relative_humidity_2m", 0)
        wind = current.get("wind_speed_10m", 0)

        w = {
            "temp_now": t_now,
            "temp_max": t_max,
            "temp_min": t_min,
            "condition": condition,
            "wind_speed": wind,
            "humidity": humidity,
        }
        outfit = _build_outfit_advice(w)

        if any(k in condition for k in ("비", "이슬비", "소나기")):
            sky_note = " 비가 오고 있어요."
        elif "눈" in condition:
            sky_note = " 눈이 오고 있어요."
        elif "맑음" in condition:
            sky_note = " 맑은 날씨예요."
        elif "흐림" in condition:
            sky_note = " 흐린 날씨예요."
        else:
            sky_note = ""

        return (
            f"{city} 현재 기온은 {t_now}°C이고, "
            f"오늘 최고 {t_max}°C / 최저 {t_min}°C 예상돼요.{sky_note} "
            f"습도 {humidity}%, 바람 {wind}km/h예요. "
            f"옷차림은 {outfit}"
        )

    except requests.Timeout:
        log.warning(f"날씨 API 타임아웃: {city}")
        return "날씨 서버 응답이 늦어요. 잠시 후 다시 시도해주세요."
    except ValueError as exc:
        return str(exc)
    except Exception as exc:
        log.error(f"날씨+옷차림 조회 실패: {exc}", exc_info=True)
        return "날씨 조회에 실패했어요."

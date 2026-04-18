"""
루이스 개인비서 - 날씨 도구
기상청 단기예보 API (무료, data.go.kr 발급)를 우선 사용.
KMA_SERVICE_KEY 미설정 시 Open-Meteo(무료, API 키 불필요)로 자동 전환.
"""
import json
import logging
import math
import time
from datetime import datetime, timedelta
from typing import Any

import requests
from langchain_core.tools import tool

from app.config import settings

log = logging.getLogger("louis.tools.weather")

# ── 도시별 위도/경도/표시명 ──────────────────────────────────────
CITY_INFO: dict[str, tuple[float, float, str]] = {
    "서울":     (37.5665, 126.9780, "서울"),
    "부산":     (35.1796, 129.0756, "부산"),
    "대구":     (35.8714, 128.6014, "대구"),
    "인천":     (37.4563, 126.7052, "인천"),
    "광주":     (35.1595, 126.8526, "광주"),
    "대전":     (36.3504, 127.3845, "대전"),
    "울산":     (35.5384, 129.3114, "울산"),
    "수원":     (37.2636, 127.0286, "수원"),
    "고양":     (37.6584, 126.8320, "고양"),
    "용인":     (37.2411, 127.1776, "용인"),
    "창원":     (35.2280, 128.6811, "창원"),
    "성남":     (37.4449, 127.1388, "성남"),
    "청주":     (36.6424, 127.4890, "청주"),
    "제주":     (33.4996, 126.5312, "제주"),
    "전주":     (35.8242, 127.1479, "전주"),
    "안산":     (37.3219, 126.8309, "안산"),
    "평택":     (36.9921, 127.1121, "평택"),
    "천안":     (36.8151, 127.1139, "천안"),
    "김해":     (35.2342, 128.8811, "김해"),
    "포항":     (36.0190, 129.3435, "포항"),
}

# ── WMO 코드 → 한국어 (Open-Meteo 폴백용) ───────────────────────
WMO_CODE_KO: dict[int, str] = {
    0: "맑음", 1: "대체로 맑음", 2: "부분적으로 흐림", 3: "흐림",
    45: "안개", 48: "안개",
    51: "이슬비", 53: "이슬비", 55: "짙은 이슬비",
    61: "비", 63: "비", 65: "강한 비",
    71: "눈", 73: "눈", 75: "강한 눈",
    80: "소나기", 81: "소나기", 82: "강한 소나기",
    95: "뇌우", 96: "뇌우(우박)", 99: "뇌우(우박)",
}

# ── 기상청 강수형태(PTY) 코드 ────────────────────────────────────
PTY_KO: dict[int, str] = {
    0: "", 1: "비", 2: "비/눈", 3: "눈",
    4: "소나기", 5: "빗방울", 6: "빗방울/눈날림", 7: "눈날림",
}

# ── 기상청 하늘상태(SKY) 코드 ────────────────────────────────────
SKY_KO: dict[int, str] = {1: "맑음", 3: "구름 많음", 4: "흐림"}

# ── TTL 캐시 ────────────────────────────────────────────────────
_cache: dict[str, tuple[float, Any]] = {}
_CACHE_TTL = 600  # 10분


def _get_cached(key: str, fn, *args) -> Any:
    now = time.time()
    if key in _cache:
        ts, val = _cache[key]
        if now - ts < _CACHE_TTL:
            return val
    val = fn(*args)
    _cache[key] = (now, val)
    return val


# ── Lambert 격자 변환 ────────────────────────────────────────────
def _latlon_to_grid(lat: float, lon: float) -> tuple[int, int]:
    """위도/경도 → 기상청 격자 좌표(nx, ny) 변환."""
    DEGRAD = math.pi / 180.0
    re = 6371.00877 / 5.0   # 지구반경 / 격자간격(km)
    slat1 = 30.0 * DEGRAD
    slat2 = 60.0 * DEGRAD
    olon  = 126.0 * DEGRAD
    olat  = 38.0 * DEGRAD
    XO, YO = 43.0, 136.0

    sn = math.log(math.cos(slat1) / math.cos(slat2)) / math.log(
        math.tan(math.pi * 0.25 + slat2 * 0.5) / math.tan(math.pi * 0.25 + slat1 * 0.5)
    )
    sf = math.pow(math.tan(math.pi * 0.25 + slat1 * 0.5), sn) * math.cos(slat1) / sn
    ro = re * sf / math.pow(math.tan(math.pi * 0.25 + olat * 0.5), sn)
    ra = re * sf / math.pow(math.tan(math.pi * 0.25 + lat * DEGRAD * 0.5), sn)

    theta = lon * DEGRAD - olon
    if theta > math.pi:  theta -= 2 * math.pi
    if theta < -math.pi: theta += 2 * math.pi
    theta *= sn

    return int(ra * math.sin(theta) + XO + 0.5), int(ro - ra * math.cos(theta) + YO + 0.5)


# ── 기상청 API 기준 시각 계산 ───────────────────────────────────
def _ncst_base() -> tuple[str, str]:
    """초단기실황: 매시 40분 이후 발표 → 현재 시각 기준 가장 최근 정시."""
    now = datetime.now()
    if now.minute < 40:
        now -= timedelta(hours=1)
    return now.strftime("%Y%m%d"), now.strftime("%H00")


def _fcst_base() -> tuple[str, str]:
    """단기예보: 0200/0500/0800/1100/1400/1700/2000/2300 발표 (+10분 가용)."""
    now = datetime.now()
    for h in reversed([2, 5, 8, 11, 14, 17, 20, 23]):
        pub = now.replace(hour=h, minute=10, second=0, microsecond=0)
        if now >= pub:
            return now.strftime("%Y%m%d"), f"{h:02d}00"
    yesterday = now - timedelta(days=1)
    return yesterday.strftime("%Y%m%d"), "2300"


# ── 도시 위경도 조회 ─────────────────────────────────────────────
def _resolve_city(city: str) -> tuple[float, float, str]:
    if city in CITY_INFO:
        return CITY_INFO[city]
    resp = requests.get(
        "https://geocoding-api.open-meteo.com/v1/search",
        params={"name": city, "count": 1, "language": "ko", "format": "json"},
        timeout=5,
    ).json()
    results = resp.get("results")
    if not results:
        raise ValueError(f"도시를 찾을 수 없어요: {city}")
    r = results[0]
    return r["latitude"], r["longitude"], r.get("name", city)


# ── 기상청 날씨 조회 ─────────────────────────────────────────────
def _fetch_kma(city: str) -> dict:
    """기상청 초단기실황 + 단기예보로 현재 날씨·최고/최저기온 조회."""
    lat, lon, display = _resolve_city(city)
    nx, ny = _latlon_to_grid(lat, lon)
    key = settings.kma_service_key
    BASE = "https://apis.data.go.kr/1360000/VilageFcstInfoService_2.0"
    common = {"serviceKey": key, "numOfRows": 200, "pageNo": 1,
              "dataType": "JSON", "nx": nx, "ny": ny}

    # 초단기실황 (현재 기온·습도·풍속·강수형태)
    bd, bt = _ncst_base()
    ncst = requests.get(f"{BASE}/getUltraSrtNcst",
                        params={**common, "base_date": bd, "base_time": bt},
                        timeout=8).json()
    obs = {i["category"]: i["obsrValue"]
           for i in ncst["response"]["body"]["items"]["item"]}

    # 단기예보 (오늘 최고/최저기온, 하늘상태)
    bd2, bt2 = _fcst_base()
    today = datetime.now().strftime("%Y%m%d")
    fcst = requests.get(f"{BASE}/getVilageFcst",
                        params={**common, "base_date": bd2, "base_time": bt2},
                        timeout=8).json()
    tmx = tmn = sky_code = None
    for item in fcst["response"]["body"]["items"]["item"]:
        if item["fcstDate"] != today:
            continue
        cat, val = item["category"], item["fcstValue"]
        if cat == "TMX" and tmx is None:
            try: tmx = float(val)
            except: pass
        if cat == "TMN" and tmn is None:
            try: tmn = float(val)
            except: pass
        if cat == "SKY" and sky_code is None:
            try: sky_code = int(val)
            except: pass

    t_now = float(obs.get("T1H", 0))
    pty = int(float(obs.get("PTY", 0)))
    pty_str = PTY_KO.get(pty, "")
    condition = pty_str if pty_str else SKY_KO.get(sky_code, "맑음")

    return {
        "city": display,
        "temp_now": round(t_now, 1),
        "temp_max": round(tmx, 1) if tmx is not None else round(t_now, 1),
        "temp_min": round(tmn, 1) if tmn is not None else round(t_now, 1),
        "condition": condition,
        "wind_speed": float(obs.get("WSD", 0)),
        "humidity": int(float(obs.get("REH", 0))),
        "source": "기상청",
    }


# ── Open-Meteo 폴백 ──────────────────────────────────────────────
def _fetch_open_meteo(city: str) -> dict:
    """KMA 키 없을 때 Open-Meteo로 조회."""
    lat, lon, display = _resolve_city(city)
    data = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": lat, "longitude": lon,
            "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code",
            "daily": "temperature_2m_max,temperature_2m_min",
            "timezone": "Asia/Seoul", "forecast_days": 1,
        },
        timeout=5,
    ).json()

    cur = data.get("current", {})
    daily = data.get("daily", {})
    return {
        "city": display,
        "temp_now": round(cur.get("temperature_2m", 0), 1),
        "temp_max": round((daily.get("temperature_2m_max") or [0])[0], 1),
        "temp_min": round((daily.get("temperature_2m_min") or [0])[0], 1),
        "condition": WMO_CODE_KO.get(cur.get("weather_code", 0), "알 수 없음"),
        "wind_speed": cur.get("wind_speed_10m", 0),
        "humidity": cur.get("relative_humidity_2m", 0),
        "source": "Open-Meteo",
    }


def _fetch_weather(city: str) -> dict:
    """기상청 우선, KMA_SERVICE_KEY 없으면 Open-Meteo."""
    if settings.kma_service_key:
        return _get_cached(f"kma:{city}", _fetch_kma, city)
    return _get_cached(f"om:{city}", _fetch_open_meteo, city)


# ── 옷차림 추천 (내부 헬퍼) ─────────────────────────────────────
def _build_outfit_advice(w: dict) -> str:
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

    is_rainy = any(k in condition for k in ("비", "이슬비", "소나기", "빗방울"))
    is_snowy = any(k in condition for k in ("눈", "눈날림"))
    if is_rainy:
        extras.append("비가 오니 우산을 꼭 챙기세요")
    if is_snowy:
        extras.append("눈이 오니 미끄럼 조심하시고 방수 신발을 신으세요")

    advice = base
    if extras:
        advice += " " + " ".join(extras) + "."
    return advice


# ── LangChain 도구들 ─────────────────────────────────────────────

@tool
def get_weather(city: str = "서울") -> str:
    """현재 날씨와 오늘 최고/최저 기온, 바람, 습도를 조회합니다.

    Args:
        city: 도시 이름 (한글 또는 영문). 기본값 서울.

    Returns:
        JSON 문자열 (city, temp_now, temp_max, temp_min, condition, wind_speed, humidity)
    """
    try:
        return json.dumps(_fetch_weather(city), ensure_ascii=False)
    except requests.Timeout:
        log.warning(f"날씨 API 타임아웃: {city}")
        return json.dumps({"error": "날씨 서버 응답이 늦어요. 잠시 후 다시 시도해주세요."}, ensure_ascii=False)
    except ValueError as exc:
        return json.dumps({"error": str(exc)}, ensure_ascii=False)
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
        w = _fetch_weather(city)
        outfit = _build_outfit_advice(w)

        condition = w["condition"]
        if any(k in condition for k in ("비", "이슬비", "소나기", "빗방울")):
            sky_note = " 비가 오고 있어요."
        elif any(k in condition for k in ("눈", "눈날림")):
            sky_note = " 눈이 오고 있어요."
        elif "맑음" in condition:
            sky_note = " 맑은 날씨예요."
        elif any(k in condition for k in ("흐림", "구름")):
            sky_note = " 흐린 날씨예요."
        else:
            sky_note = ""

        source_note = " (기상청)" if w.get("source") == "기상청" else ""
        return (
            f"{w['city']} 현재 기온은 {w['temp_now']}°C이고, "
            f"오늘 최고 {w['temp_max']}°C / 최저 {w['temp_min']}°C 예상돼요.{sky_note} "
            f"습도 {w['humidity']}%, 바람 {w['wind_speed']}m/s예요{source_note}. "
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

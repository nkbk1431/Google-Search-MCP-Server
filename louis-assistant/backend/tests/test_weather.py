"""
날씨 도구 테스트 (requests-mock 사용, 실제 API 호출 없음)
실행: pytest tests/test_weather.py -v
"""
import json

import pytest
import requests_mock as req_mock

from app.agent.tools.weather import get_weather, recommend_outfit, get_weather_and_outfit, CITY_MAP


# ── get_weather 테스트 ──────────────────────────────────────────────

MOCK_CURRENT = {
    "cod": 200,
    "name": "Seoul",
    "main": {"temp": 18.5, "humidity": 60},
    "weather": [{"description": "맑음"}],
    "wind": {"speed": 3.2},
}

MOCK_FORECAST = {
    "list": [
        {"dt": 9999999999, "main": {"temp": 22.0}},
        {"dt": 9999999999, "main": {"temp": 14.0}},
    ]
}


def test_get_weather_seoul(requests_mock):
    """서울 날씨를 정상 조회하는지 확인."""
    requests_mock.get(
        "https://api.openweathermap.org/data/2.5/weather",
        json=MOCK_CURRENT,
    )
    requests_mock.get(
        "https://api.openweathermap.org/data/2.5/forecast",
        json=MOCK_FORECAST,
    )

    result = get_weather.invoke({"city": "Seoul"})
    data = json.loads(result)

    assert data["city"] == "Seoul"
    assert data["temp_now"] == 18.5
    assert data["humidity"] == 60
    assert "condition" in data


def test_get_weather_korean_city(requests_mock):
    """한글 도시명이 영문으로 변환되는지 확인."""
    requests_mock.get(
        "https://api.openweathermap.org/data/2.5/weather",
        json={**MOCK_CURRENT, "name": "Busan"},
    )
    requests_mock.get(
        "https://api.openweathermap.org/data/2.5/forecast",
        json=MOCK_FORECAST,
    )

    result = get_weather.invoke({"city": "부산"})
    data = json.loads(result)
    assert data["city"] == "Busan"


def test_get_weather_timeout(requests_mock):
    """타임아웃 시 에러 메시지를 반환하는지 확인."""
    import requests
    requests_mock.get(
        "https://api.openweathermap.org/data/2.5/weather",
        exc=requests.Timeout,
    )
    result = get_weather.invoke({"city": "Seoul"})
    data = json.loads(result)
    assert "error" in data


def test_get_weather_invalid_city(requests_mock):
    """존재하지 않는 도시 처리."""
    requests_mock.get(
        "https://api.openweathermap.org/data/2.5/weather",
        json={"cod": "404", "message": "city not found"},
    )
    requests_mock.get(
        "https://api.openweathermap.org/data/2.5/forecast",
        json={"list": []},
    )
    result = get_weather.invoke({"city": "NoSuchCity"})
    data = json.loads(result)
    assert "error" in data


def test_city_map_completeness():
    """주요 한국 도시가 매핑 테이블에 존재하는지 확인."""
    major_cities = ["서울", "부산", "대구", "인천", "광주", "대전", "제주"]
    for city in major_cities:
        assert city in CITY_MAP, f"{city}이 CITY_MAP에 없어요"


# ── recommend_outfit 테스트 ──────────────────────────────────────────

def _make_weather(temp_max: float, temp_min: float, condition: str = "맑음", wind: float = 2.0) -> str:
    return json.dumps({
        "city": "Seoul",
        "temp_now": (temp_max + temp_min) / 2,
        "temp_max": temp_max,
        "temp_min": temp_min,
        "condition": condition,
        "wind_speed": wind,
        "humidity": 50,
    }, ensure_ascii=False)


def test_outfit_hot_weather():
    """더운 날씨 (30도) 반팔 추천 확인."""
    result = recommend_outfit.invoke({"weather_json": _make_weather(30, 22)})
    assert "반팔" in result or "민소매" in result


def test_outfit_cold_weather():
    """추운 날씨 (4도) 패딩 추천 확인."""
    result = recommend_outfit.invoke({"weather_json": _make_weather(4, -2)})
    assert "패딩" in result


def test_outfit_rainy_day():
    """비 오는 날 우산 언급 확인."""
    result = recommend_outfit.invoke({"weather_json": _make_weather(18, 12, "비")})
    assert "우산" in result


def test_outfit_windy_day():
    """바람 강한 날 방풍 언급 확인."""
    result = recommend_outfit.invoke({"weather_json": _make_weather(20, 14, "맑음", wind=7.0)})
    assert "방풍" in result


def test_outfit_large_temp_diff():
    """일교차 큰 날 겉옷 언급 확인."""
    result = recommend_outfit.invoke({"weather_json": _make_weather(22, 10)})
    assert "겉옷" in result or "바람막이" in result


def test_outfit_cold_morning_warm_day():
    """아침 춥고 낮 따뜻한 날 (t_min<=10, t_max>=18) 겉옷 안내 확인."""
    result = recommend_outfit.invoke({"weather_json": _make_weather(20, 8)})
    assert "겉옷" in result or "쌀쌀" in result


def test_outfit_invalid_json():
    """잘못된 JSON 입력 처리."""
    result = recommend_outfit.invoke({"weather_json": "not-json"})
    assert "불러올 수 없" in result


# ── get_weather_and_outfit 테스트 ──────────────────────────────────────

def test_get_weather_and_outfit_returns_combined(requests_mock):
    """날씨+옷차림 통합 도구가 기온과 옷차림을 모두 포함하는지 확인."""
    requests_mock.get(
        "https://api.openweathermap.org/data/2.5/weather",
        json=MOCK_CURRENT,
    )
    requests_mock.get(
        "https://api.openweathermap.org/data/2.5/forecast",
        json=MOCK_FORECAST,
    )

    result = get_weather_and_outfit.invoke({"city": "서울"})

    assert "18.5" in result or "°C" in result
    # 옷차림 키워드 포함 여부
    outfit_keywords = ["추천", "반팔", "긴팔", "자켓", "코트", "패딩", "가디건", "맨투맨"]
    assert any(kw in result for kw in outfit_keywords)


def test_get_weather_and_outfit_rainy(requests_mock):
    """비 오는 날 우산 언급 확인."""
    mock = {**MOCK_CURRENT, "weather": [{"description": "비"}]}
    requests_mock.get("https://api.openweathermap.org/data/2.5/weather", json=mock)
    requests_mock.get("https://api.openweathermap.org/data/2.5/forecast", json=MOCK_FORECAST)

    result = get_weather_and_outfit.invoke({"city": "서울"})
    assert "우산" in result


def test_get_weather_and_outfit_timeout(requests_mock):
    """타임아웃 시 에러 메시지 반환 확인."""
    import requests
    requests_mock.get("https://api.openweathermap.org/data/2.5/weather", exc=requests.Timeout)

    result = get_weather_and_outfit.invoke({"city": "서울"})
    assert "늦어요" in result or "실패" in result

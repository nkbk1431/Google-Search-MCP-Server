"""
루이스 개인비서 - 길찾기 도구
Google Maps Directions API로 경로 및 소요 시간을 조회합니다.
Flutter 앱이 실제 지도를 열 수 있도록 인텐트 신호도 반환합니다.
"""
import json
import logging

import requests
from langchain_core.tools import tool

from app.config import settings

log = logging.getLogger("louis.tools.navigation")

TRAVEL_MODE_MAP = {
    "자동차": "driving", "드라이브": "driving", "차": "driving",
    "대중교통": "transit", "지하철": "transit", "버스": "transit",
    "도보": "walking", "걷기": "walking",
    "자전거": "bicycling",
}


@tool
def get_directions(origin: str, destination: str, mode: str = "transit") -> str:
    """출발지에서 목적지까지의 경로와 소요 시간을 조회합니다.

    Args:
        origin: 출발지 (주소 또는 장소명)
        destination: 목적지 (주소 또는 장소명)
        mode: 이동 수단. 'transit'(대중교통), 'driving'(자동차), 'walking'(도보)

    Returns:
        소요 시간, 거리 정보 및 앱 실행 신호
    """
    travel_mode = TRAVEL_MODE_MAP.get(mode.lower(), mode.lower())
    if travel_mode not in ("transit", "driving", "walking", "bicycling"):
        travel_mode = "transit"

    # Google Maps API 키가 없으면 앱 인텐트만 반환
    maps_key = getattr(settings, "google_maps_api_key", "")
    if not maps_key:
        return json.dumps({
            "action": "OPEN_MAPS",
            "origin": origin,
            "destination": destination,
            "mode": travel_mode,
            "message": f"{destination}까지 지도를 열게요.",
        }, ensure_ascii=False)

    try:
        r = requests.get(
            "https://maps.googleapis.com/maps/api/directions/json",
            params={
                "origin": origin,
                "destination": destination,
                "mode": travel_mode,
                "language": "ko",
                "key": maps_key,
            },
            timeout=5,
        )
        data = r.json()
        if data.get("status") != "OK":
            return json.dumps({
                "action": "OPEN_MAPS",
                "origin": origin,
                "destination": destination,
                "mode": travel_mode,
                "message": f"{destination}까지 지도를 열게요.",
            }, ensure_ascii=False)

        route = data["routes"][0]["legs"][0]
        duration = route["duration"]["text"]
        distance = route["distance"]["text"]
        steps_count = len(route["steps"])

        mode_kr = {"transit": "대중교통", "driving": "자동차",
                   "walking": "도보", "bicycling": "자전거"}.get(travel_mode, travel_mode)

        return json.dumps({
            "action": "OPEN_MAPS",
            "origin": origin,
            "destination": destination,
            "mode": travel_mode,
            "message": (
                f"{mode_kr}으로 {destination}까지 약 {duration}, {distance} 거리예요."
            ),
        }, ensure_ascii=False)

    except requests.Timeout:
        return f"{destination}까지 길찾기 서버 응답이 늦어요."
    except Exception as exc:
        log.error(f"길찾기 실패: {exc}", exc_info=True)
        return f"{destination}까지 길찾기에 실패했어요."

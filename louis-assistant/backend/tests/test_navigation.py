"""
길찾기 도구 테스트
get_directions 기능을 검증합니다.
"""
import json
import pytest
from unittest.mock import patch, MagicMock


class TestGetDirections:

    def test_no_maps_key_returns_open_maps_intent(self):
        """API 키 없으면 OPEN_MAPS 인텐트를 즉시 반환합니다."""
        from app.agent.tools.navigation import get_directions

        with patch("app.agent.tools.navigation.settings") as mock_settings:
            mock_settings.google_maps_api_key = ""
            result = get_directions.invoke({
                "origin": "강남역",
                "destination": "홍대입구역",
                "mode": "transit",
            })

        data = json.loads(result)
        assert data["action"] == "OPEN_MAPS"
        assert data["origin"] == "강남역"
        assert data["destination"] == "홍대입구역"
        assert data["mode"] == "transit"
        assert "홍대입구역" in data["message"]

    def test_travel_mode_mapping_korean(self):
        """한국어 이동 수단이 영어 코드로 매핑됩니다."""
        from app.agent.tools.navigation import get_directions

        with patch("app.agent.tools.navigation.settings") as mock_settings:
            mock_settings.google_maps_api_key = ""
            result = get_directions.invoke({
                "origin": "서울역",
                "destination": "부산역",
                "mode": "자동차",
            })

        data = json.loads(result)
        assert data["mode"] == "driving"

    def test_travel_mode_walking(self):
        from app.agent.tools.navigation import get_directions

        with patch("app.agent.tools.navigation.settings") as mock_settings:
            mock_settings.google_maps_api_key = ""
            result = get_directions.invoke({
                "origin": "A",
                "destination": "B",
                "mode": "도보",
            })

        data = json.loads(result)
        assert data["mode"] == "walking"

    def test_invalid_mode_defaults_to_transit(self):
        """알 수 없는 이동 수단은 transit으로 대체합니다."""
        from app.agent.tools.navigation import get_directions

        with patch("app.agent.tools.navigation.settings") as mock_settings:
            mock_settings.google_maps_api_key = ""
            result = get_directions.invoke({
                "origin": "A",
                "destination": "B",
                "mode": "날아서",
            })

        data = json.loads(result)
        assert data["mode"] == "transit"

    def test_with_maps_api_success(self):
        """Google Maps API 성공 시 소요 시간·거리 포함 응답."""
        from app.agent.tools.navigation import get_directions

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "status": "OK",
            "routes": [{
                "legs": [{
                    "duration": {"text": "약 45분"},
                    "distance": {"text": "22 km"},
                    "steps": [{}, {}, {}],
                }]
            }],
        }

        with patch("app.agent.tools.navigation.settings") as mock_settings, \
             patch("app.agent.tools.navigation.requests.get", return_value=mock_response):
            mock_settings.google_maps_api_key = "fake-key"
            result = get_directions.invoke({
                "origin": "강남역",
                "destination": "홍대입구역",
                "mode": "transit",
            })

        data = json.loads(result)
        assert data["action"] == "OPEN_MAPS"
        assert "45분" in data["message"]
        assert "22 km" in data["message"]

    def test_with_maps_api_not_ok_status(self):
        """Google Maps API 비정상 응답 시 OPEN_MAPS 폴백."""
        from app.agent.tools.navigation import get_directions

        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "ZERO_RESULTS"}

        with patch("app.agent.tools.navigation.settings") as mock_settings, \
             patch("app.agent.tools.navigation.requests.get", return_value=mock_response):
            mock_settings.google_maps_api_key = "fake-key"
            result = get_directions.invoke({
                "origin": "없는곳",
                "destination": "없는목적지",
            })

        data = json.loads(result)
        assert data["action"] == "OPEN_MAPS"

    def test_with_maps_api_timeout(self):
        """요청 타임아웃 시 에러 메시지 반환."""
        from app.agent.tools.navigation import get_directions
        import requests as req_lib

        with patch("app.agent.tools.navigation.settings") as mock_settings, \
             patch("app.agent.tools.navigation.requests.get",
                   side_effect=req_lib.Timeout()):
            mock_settings.google_maps_api_key = "fake-key"
            result = get_directions.invoke({
                "origin": "A",
                "destination": "목적지",
            })

        assert "늦어요" in result or "타임아웃" in result.lower() or "길찾기" in result

    def test_travel_mode_map_completeness(self):
        """TRAVEL_MODE_MAP이 주요 한국어 교통 수단을 커버합니다."""
        from app.agent.tools.navigation import TRAVEL_MODE_MAP

        assert "자동차" in TRAVEL_MODE_MAP
        assert "대중교통" in TRAVEL_MODE_MAP
        assert "도보" in TRAVEL_MODE_MAP
        assert "자전거" in TRAVEL_MODE_MAP
        assert TRAVEL_MODE_MAP["자동차"] == "driving"
        assert TRAVEL_MODE_MAP["도보"] == "walking"

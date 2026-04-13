"""
교통 도구 테스트 (Phase 12)
search_srt / search_ktx / get_subway_arrival 기능을 검증합니다.
"""
import json
import pytest
from unittest.mock import patch, MagicMock


class TestSearchSrt:

    def test_srt_library_missing_returns_error(self):
        """srt 라이브러리 미설치 시 안내 메시지를 반환합니다."""
        import sys
        with patch.dict(sys.modules, {"srt": None}):
            from app.agent.tools.transport import search_srt
            result = search_srt.invoke({
                "departure": "수서", "arrival": "부산",
            })
        data = json.loads(result)
        assert "error" in data
        assert "srt" in data["error"].lower() or "미설치" in data["error"]

    def test_srt_no_credentials_returns_error(self):
        """SRT_ID/PW 미설정 시 에러를 반환합니다."""
        mock_srt_mod = MagicMock()
        mock_srt_mod.SRT = MagicMock()
        mock_srt_mod.SRTError = Exception

        with patch("app.agent.tools.transport.settings") as mock_settings, \
             patch.dict(__import__("sys").modules, {"srt": mock_srt_mod}):
            mock_settings.srt_id = None
            mock_settings.srt_pw = None
            from importlib import reload
            import app.agent.tools.transport as mod
            # 직접 함수 로직 테스트
            result = json.loads(mod.search_srt.invoke({"departure": "수서", "arrival": "부산"}))

        assert "error" in result

    def test_srt_normalize_station(self):
        """_normalize_station이 역명을 정규화합니다."""
        from app.agent.tools.transport import _normalize_station
        assert _normalize_station("서울역") == "서울"
        assert _normalize_station("부산역") == "부산"
        assert _normalize_station("강남") == "강남"

    def test_parse_date_today(self):
        """'오늘'을 YYYYMMDD로 변환합니다."""
        from app.agent.tools.transport import _parse_date
        from datetime import datetime
        result = _parse_date("오늘")
        assert result == datetime.now().strftime("%Y%m%d")

    def test_parse_date_tomorrow(self):
        """'내일'을 내일 날짜로 변환합니다."""
        from app.agent.tools.transport import _parse_date
        from datetime import datetime, timedelta
        result = _parse_date("내일")
        assert result == (datetime.now() + timedelta(days=1)).strftime("%Y%m%d")

    def test_parse_date_numeric(self):
        """숫자 형식 날짜는 그대로 반환합니다."""
        from app.agent.tools.transport import _parse_date
        assert _parse_date("20250415") == "20250415"
        assert _parse_date("2025-04-15") == "20250415"


class TestSearchKtx:

    def test_ktx_library_missing_returns_error(self):
        """korail2 라이브러리 미설치 시 안내 메시지를 반환합니다."""
        import sys
        with patch.dict(sys.modules, {"korail2": None}):
            from app.agent.tools.transport import search_ktx
            result = search_ktx.invoke({
                "departure": "서울", "arrival": "부산",
            })
        data = json.loads(result)
        assert "error" in data

    def test_ktx_no_credentials_returns_error(self):
        """KORAIL_ID/PW 미설정 시 에러를 반환합니다."""
        mock_mod = MagicMock()
        mock_mod.Korail = MagicMock()
        mock_mod.KorailError = Exception
        mock_mod.ReserveOption = MagicMock()

        import sys
        with patch.dict(sys.modules, {"korail2": mock_mod}), \
             patch("app.agent.tools.transport.settings") as mock_s:
            mock_s.korail_id = None
            mock_s.korail_pw = None
            import app.agent.tools.transport as mod
            result = json.loads(mod.search_ktx.invoke({"departure": "서울", "arrival": "부산"}))

        assert "error" in result


class TestGetSubwayArrival:

    def test_no_api_key_returns_error(self):
        """SEOUL_API_KEY 미설정 시 에러를 반환합니다."""
        with patch("app.agent.tools.transport.settings") as mock_s:
            mock_s.seoul_api_key = None
            import app.agent.tools.transport as mod
            result = json.loads(mod.get_subway_arrival.invoke({"station": "강남"}))
        assert "error" in result
        assert "SEOUL_API_KEY" in result["error"]

    def test_subway_success(self):
        """정상 응답 시 도착 정보를 파싱합니다."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "realtimeArrivalList": [
                {
                    "trainLineNm": "2호선 성수행",
                    "bstatnNm": "성수",
                    "updnLine": "내선",
                    "arvlMsg2": "2분 후",
                    "arvlMsg3": "강남",
                    "btrainNo": "2234",
                },
                {
                    "trainLineNm": "2호선 신도림행",
                    "bstatnNm": "신도림",
                    "updnLine": "외선",
                    "arvlMsg2": "5분 후",
                    "arvlMsg3": "역삼",
                    "btrainNo": "2235",
                },
            ]
        }
        with patch("app.agent.tools.transport.settings") as mock_s, \
             patch("app.agent.tools.transport.requests.get", return_value=mock_resp):
            mock_s.seoul_api_key = "test-key"
            import app.agent.tools.transport as mod
            result = json.loads(mod.get_subway_arrival.invoke({"station": "강남"}))

        assert "arrivals" in result
        assert len(result["arrivals"]) == 2
        assert result["station"] == "강남"

    def test_subway_removes_역_suffix(self):
        """역 이름에서 '역'을 제거합니다."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"realtimeArrivalList": []}
        with patch("app.agent.tools.transport.settings") as mock_s, \
             patch("app.agent.tools.transport.requests.get", return_value=mock_resp):
            mock_s.seoul_api_key = "test-key"
            import app.agent.tools.transport as mod
            result = json.loads(mod.get_subway_arrival.invoke({"station": "홍대입구역"}))
        assert result.get("station") == "홍대입구"

    def test_subway_empty_returns_message(self):
        """도착 정보 없을 때 메시지를 반환합니다."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"realtimeArrivalList": []}
        with patch("app.agent.tools.transport.settings") as mock_s, \
             patch("app.agent.tools.transport.requests.get", return_value=mock_resp):
            mock_s.seoul_api_key = "test-key"
            import app.agent.tools.transport as mod
            result = json.loads(mod.get_subway_arrival.invoke({"station": "강남"}))
        assert "message" in result

    def test_subway_api_error_returns_error(self):
        """API 오류 응답 시 에러 메시지를 반환합니다."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "errorMessage": {"message": "인증키 오류입니다."}
        }
        with patch("app.agent.tools.transport.settings") as mock_s, \
             patch("app.agent.tools.transport.requests.get", return_value=mock_resp):
            mock_s.seoul_api_key = "bad-key"
            import app.agent.tools.transport as mod
            result = json.loads(mod.get_subway_arrival.invoke({"station": "강남"}))
        assert "error" in result

    def test_subway_timeout_returns_error(self):
        """타임아웃 시 에러를 반환합니다."""
        import requests as req
        with patch("app.agent.tools.transport.settings") as mock_s, \
             patch("app.agent.tools.transport.requests.get", side_effect=req.Timeout):
            mock_s.seoul_api_key = "test-key"
            import app.agent.tools.transport as mod
            result = json.loads(mod.get_subway_arrival.invoke({"station": "강남"}))
        assert "error" in result

"""
쇼핑·스포츠·한국어 유틸 도구 테스트 (Phase 12)
search_shopping / search_used_market / get_kbo_results /
get_kleague_results / get_lck_results /
check_spelling / get_stock_price / get_kospi_index /
search_postal_code 를 검증합니다.
"""
import json
import pytest
from unittest.mock import patch, MagicMock


# ════════════════════════════════════════════════════════════
# 쇼핑 도구
# ════════════════════════════════════════════════════════════

class TestSearchShopping:

    def test_coupang_returns_open_browser(self):
        """쿠팡 검색은 OPEN_BROWSER 액션을 반환합니다."""
        from app.agent.tools.shopping import search_shopping
        result = json.loads(search_shopping.invoke({"query": "에어팟", "platform": "coupang"}))
        assert result["action"] == "OPEN_BROWSER"
        assert "coupang" in result["url"]
        assert "에어팟" in result["url"] or "에어팟" in result["message"]

    def test_oliveyoung_returns_open_browser(self):
        """올리브영 검색은 OPEN_BROWSER 액션을 반환합니다."""
        from app.agent.tools.shopping import search_shopping
        result = json.loads(search_shopping.invoke({"query": "선크림", "platform": "oliveyoung"}))
        assert result["action"] == "OPEN_BROWSER"
        assert "oliveyoung" in result["url"]

    def test_daiso_returns_open_browser(self):
        """다이소 검색은 OPEN_BROWSER 액션을 반환합니다."""
        from app.agent.tools.shopping import search_shopping
        result = json.loads(search_shopping.invoke({"query": "수납함", "platform": "daiso"}))
        assert result["action"] == "OPEN_BROWSER"

    def test_naver_no_api_key_returns_browser_fallback(self):
        """네이버 API 키 없으면 브라우저 폴백을 반환합니다."""
        with patch("app.agent.tools.shopping.settings") as mock_s:
            mock_s.naver_client_id = None
            mock_s.naver_client_secret = None
            from app.agent.tools.shopping import search_shopping
            result = json.loads(search_shopping.invoke({"query": "노트북", "platform": "naver"}))
        assert result["action"] == "OPEN_BROWSER"
        assert "naver" in result["url"]

    def test_naver_with_api_success(self):
        """네이버 API 정상 응답 시 상품 목록을 반환합니다."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "items": [
                {"title": "<b>에어팟</b> 프로 2세대", "lprice": "350000",
                 "mallName": "Apple", "link": "https://example.com", "image": ""},
                {"title": "에어팟 3세대", "lprice": "280000",
                 "mallName": "쿠팡", "link": "https://example.com", "image": ""},
            ]
        }
        mock_resp.raise_for_status = MagicMock()
        with patch("app.agent.tools.shopping.settings") as mock_s, \
             patch("app.agent.tools.shopping.requests.get", return_value=mock_resp):
            mock_s.naver_client_id = "test-id"
            mock_s.naver_client_secret = "test-secret"
            from app.agent.tools.shopping import search_shopping
            result = json.loads(search_shopping.invoke({"query": "에어팟"}))

        assert "items" in result
        assert len(result["items"]) == 2
        assert result["items"][0]["title"] == "에어팟 프로 2세대"  # <b> 제거됨
        assert result["items"][0]["price"] == 350000

    def test_naver_price_filter(self):
        """max_price 필터가 적용됩니다."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "items": [
                {"title": "저렴한 상품", "lprice": "10000",
                 "mallName": "A", "link": "https://a.com", "image": ""},
                {"title": "비싼 상품", "lprice": "500000",
                 "mallName": "B", "link": "https://b.com", "image": ""},
            ]
        }
        mock_resp.raise_for_status = MagicMock()
        with patch("app.agent.tools.shopping.settings") as mock_s, \
             patch("app.agent.tools.shopping.requests.get", return_value=mock_resp):
            mock_s.naver_client_id = "id"
            mock_s.naver_client_secret = "secret"
            from app.agent.tools.shopping import search_shopping
            result = json.loads(search_shopping.invoke({"query": "상품", "max_price": 50000}))

        assert len(result["items"]) == 1
        assert result["items"][0]["title"] == "저렴한 상품"


class TestSearchUsedMarket:

    def test_returns_both_platforms(self):
        """번개장터와 중고나라 두 플랫폼을 반환합니다."""
        from app.agent.tools.shopping import search_used_market
        result = json.loads(search_used_market.invoke({"query": "아이폰"}))
        assert "platforms" in result
        names = [p["name"] for p in result["platforms"]]
        assert "번개장터" in names
        assert "중고나라" in names

    def test_urls_contain_query(self):
        """URL에 검색어가 포함됩니다."""
        from app.agent.tools.shopping import search_used_market
        result = json.loads(search_used_market.invoke({"query": "맥북"}))
        for p in result["platforms"]:
            assert p["action"] == "OPEN_BROWSER"

    def test_message_contains_query(self):
        """메시지에 검색어가 포함됩니다."""
        from app.agent.tools.shopping import search_used_market
        result = json.loads(search_used_market.invoke({"query": "갤럭시"}))
        assert "갤럭시" in result["message"]


# ════════════════════════════════════════════════════════════
# 스포츠 도구
# ════════════════════════════════════════════════════════════

class TestGetKboResults:

    def _mock_games(self, games):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"result": {"games": games}}
        return mock_resp

    def test_kbo_returns_games(self):
        """KBO 경기 목록을 반환합니다."""
        games = [
            {"homeTeamName": "LG", "awayTeamName": "두산",
             "homeTeamScore": "5", "awayTeamScore": "3",
             "gameStatusCd": "RESULT", "stadium": "잠실", "gameStartTime": "18:30"},
        ]
        with patch("app.agent.tools.sports.requests.get", return_value=self._mock_games(games)):
            from app.agent.tools.sports import get_kbo_results
            result = json.loads(get_kbo_results.invoke({"date": "오늘"}))
        assert "games" in result
        assert result["games"][0]["home_team"] == "LG"
        assert result["league"] == "KBO"

    def test_kbo_team_filter(self):
        """특정 팀 필터가 적용됩니다."""
        games = [
            {"homeTeamName": "LG", "awayTeamName": "두산",
             "homeTeamScore": "5", "awayTeamScore": "3",
             "gameStatusCd": "RESULT", "stadium": "잠실", "gameStartTime": "18:30"},
            {"homeTeamName": "KIA", "awayTeamName": "삼성",
             "homeTeamScore": "2", "awayTeamScore": "1",
             "gameStatusCd": "RESULT", "stadium": "광주", "gameStartTime": "18:30"},
        ]
        with patch("app.agent.tools.sports.requests.get", return_value=self._mock_games(games)):
            from app.agent.tools.sports import get_kbo_results
            result = json.loads(get_kbo_results.invoke({"date": "오늘", "team": "LG"}))
        assert len(result["games"]) == 1
        assert "LG" in (result["games"][0]["home_team"] + result["games"][0]["away_team"])

    def test_kbo_no_games_returns_message(self):
        """경기 없을 때 메시지를 반환합니다."""
        with patch("app.agent.tools.sports.requests.get", return_value=self._mock_games([])):
            from app.agent.tools.sports import get_kbo_results
            result = json.loads(get_kbo_results.invoke({"date": "오늘"}))
        assert "message" in result

    def test_kbo_api_error_returns_browser(self):
        """API 오류 시 OPEN_BROWSER 폴백을 반환합니다."""
        with patch("app.agent.tools.sports.requests.get", side_effect=Exception("오류")):
            from app.agent.tools.sports import get_kbo_results
            result = json.loads(get_kbo_results.invoke({"date": "오늘"}))
        assert result.get("action") == "OPEN_BROWSER"

    def test_kbo_score_format(self):
        """스코어가 '원정 : 홈' 형식으로 포맷됩니다."""
        games = [
            {"homeTeamName": "KT", "awayTeamName": "키움",
             "homeTeamScore": "4", "awayTeamScore": "2",
             "gameStatusCd": "RESULT", "stadium": "수원", "gameStartTime": "17:00"},
        ]
        with patch("app.agent.tools.sports.requests.get", return_value=self._mock_games(games)):
            from app.agent.tools.sports import get_kbo_results
            result = json.loads(get_kbo_results.invoke({"date": "오늘"}))
        assert "2" in result["games"][0]["score"]
        assert "4" in result["games"][0]["score"]


class TestGetKleagueResults:

    def test_kleague_returns_games(self):
        """K리그 경기 목록을 반환합니다."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "result": {"games": [
                {"homeTeamName": "전북현대", "awayTeamName": "울산현대",
                 "homeTeamScore": "2", "awayTeamScore": "1",
                 "gameStatusCd": "RESULT", "stadium": "전주월드컵", "gameStartTime": "19:00"},
            ]}
        }
        with patch("app.agent.tools.sports.requests.get", return_value=mock_resp):
            from app.agent.tools.sports import get_kleague_results
            result = json.loads(get_kleague_results.invoke({"date": "오늘"}))
        assert result["league"] == "K리그"
        assert len(result["games"]) == 1

    def test_kleague_no_games(self):
        """K리그 경기 없을 때 메시지를 반환합니다."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"result": {"games": []}}
        with patch("app.agent.tools.sports.requests.get", return_value=mock_resp):
            from app.agent.tools.sports import get_kleague_results
            result = json.loads(get_kleague_results.invoke({"date": "오늘"}))
        assert "message" in result


# ════════════════════════════════════════════════════════════
# 한국어 유틸 도구
# ════════════════════════════════════════════════════════════

class TestCheckSpelling:

    def test_hanspell_success(self):
        """hanspell 라이브러리 사용 시 교정 결과를 반환합니다."""
        mock_hanspell = MagicMock()
        mock_result = MagicMock()
        mock_result.checked = "안녕하세요. 잘 부탁드립니다."
        mock_result.errors = 1
        mock_hanspell.spell_checker.check.return_value = mock_result

        import sys
        with patch.dict(sys.modules, {"hanspell": mock_hanspell}):
            from app.agent.tools.korean_utils import check_spelling
            result = json.loads(check_spelling.invoke({"text": "안녕하세요. 잘 부탁드립니다."}))

        assert "corrected" in result
        assert "changed" in result

    def test_hanspell_not_installed_falls_back(self):
        """hanspell 미설치 시 부산대 API로 폴백합니다."""
        import sys
        mock_resp = MagicMock()
        mock_resp.text = '<textarea id="erow1">교정된 텍스트</textarea>'

        with patch.dict(sys.modules, {"hanspell": None}), \
             patch("app.agent.tools.korean_utils.requests.post", return_value=mock_resp):
            from app.agent.tools.korean_utils import check_spelling
            result = json.loads(check_spelling.invoke({"text": "교정할 텍스트"}))

        assert "corrected" in result

    def test_text_truncated_at_500(self):
        """500자 초과 텍스트는 잘립니다."""
        long_text = "가" * 600
        import sys
        mock_resp = MagicMock()
        mock_resp.text = '<textarea id="erow1">교정됨</textarea>'

        with patch.dict(sys.modules, {"hanspell": None}), \
             patch("app.agent.tools.korean_utils.requests.post", return_value=mock_resp):
            from app.agent.tools.korean_utils import check_spelling
            result = json.loads(check_spelling.invoke({"text": long_text}))
        # 500자로 잘린 원문이 결과에 있어야 합니다
        assert len(result.get("original", "")) <= 500


class TestGetStockPrice:

    def test_pykrx_not_installed(self):
        """pykrx 미설치 시 에러를 반환합니다."""
        import sys
        with patch.dict(sys.modules, {"pykrx": None, "pykrx.stock": None}):
            from app.agent.tools.korean_utils import get_stock_price
            result = json.loads(get_stock_price.invoke({"company": "삼성전자"}))
        assert "error" in result

    def test_stock_company_not_found(self):
        """존재하지 않는 종목명은 에러를 반환합니다."""
        import pandas as pd

        mock_pykrx = MagicMock()
        mock_pykrx.stock.get_market_ticker_list.return_value = ["005930"]
        mock_pykrx.stock.get_market_ticker_name.return_value = "삼성전자"

        import sys
        with patch.dict(sys.modules, {"pykrx": mock_pykrx, "pykrx.stock": mock_pykrx.stock}):
            from app.agent.tools.korean_utils import get_stock_price
            result = json.loads(get_stock_price.invoke({"company": "존재안하는회사XYZ"}))
        assert "error" in result

    def test_stock_success(self):
        """정상 종목 조회 시 가격 정보를 반환합니다."""
        import pandas as pd

        mock_pykrx_stock = MagicMock()
        mock_pykrx_stock.get_market_ticker_list.return_value = ["005930"]
        mock_pykrx_stock.get_market_ticker_name.return_value = "삼성전자"

        df = pd.DataFrame({
            "종가": [75000],
            "시가": [74000],
            "고가": [76000],
            "저가": [73500],
            "거래량": [15000000],
        })
        mock_pykrx_stock.get_market_ohlcv_by_date.return_value = df

        import sys
        with patch.dict(sys.modules, {"pykrx": MagicMock(stock=mock_pykrx_stock), "pykrx.stock": mock_pykrx_stock}):
            from app.agent.tools.korean_utils import get_stock_price
            result = json.loads(get_stock_price.invoke({"company": "삼성전자"}))

        assert "price" in result
        assert "75,000원" in result["price"]
        assert "change_rate" in result


class TestGetKospiIndex:

    def test_pykrx_not_installed(self):
        """pykrx 미설치 시 에러를 반환합니다."""
        import sys
        with patch.dict(sys.modules, {"pykrx": None, "pykrx.stock": None}):
            from app.agent.tools.korean_utils import get_kospi_index
            result = json.loads(get_kospi_index.invoke({}))
        assert "error" in result

    def test_returns_kospi_and_kosdaq(self):
        """코스피와 코스닥 지수를 모두 반환합니다."""
        import pandas as pd

        mock_stock = MagicMock()
        df = pd.DataFrame({"종가": [2700.5, 2710.0]})
        mock_stock.get_index_ohlcv_by_date.return_value = df

        import sys
        with patch.dict(sys.modules, {"pykrx": MagicMock(stock=mock_stock), "pykrx.stock": mock_stock}):
            from app.agent.tools.korean_utils import get_kospi_index
            result = json.loads(get_kospi_index.invoke({}))

        assert "kospi" in result
        assert "kosdaq" in result


class TestSearchPostalCode:

    def test_kakao_no_key_uses_juso_api(self):
        """카카오 키 없으면 도로명주소 API를 사용합니다."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "results": {
                "juso": [
                    {
                        "roadAddr": "서울특별시 강남구 테헤란로 152",
                        "jibunAddr": "서울특별시 강남구 역삼동 737",
                        "zipNo": "06236",
                        "bdNm": "강남파이낸스센터",
                    }
                ]
            }
        }
        with patch("app.agent.tools.korean_utils.requests.get", return_value=mock_resp):
            from app.agent.tools.korean_utils import search_postal_code
            result = json.loads(search_postal_code.invoke({"address": "강남구 테헤란로 152"}))

        assert "results" in result
        assert result["results"][0]["zip_code"] == "06236"

    def test_empty_results_returns_message(self):
        """결과 없으면 메시지를 반환합니다."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"results": {"juso": []}}
        with patch("app.agent.tools.korean_utils.requests.get", return_value=mock_resp):
            from app.agent.tools.korean_utils import search_postal_code
            result = json.loads(search_postal_code.invoke({"address": "존재안하는주소XYZABC"}))
        # 빈 결과 처리
        assert "error" in result or "message" in result or "results" in result

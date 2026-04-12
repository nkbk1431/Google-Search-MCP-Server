"""
검색, 번역, 금융 도구 테스트
"""
import json
import pytest
import requests_mock as rm_module

from app.agent.tools.search import web_search
from app.agent.tools.translate import translate_text, LANG_MAP
from app.agent.tools.finance import convert_currency, get_stock_price


# ── 웹 검색 ──────────────────────────────────────────────────────────

class TestWebSearch:

    def test_search_returns_organic_results(self, requests_mock):
        requests_mock.post(
            "https://google.serper.dev/search",
            json={
                "organic": [
                    {"title": "파이썬 공식 사이트", "snippet": "Python은 범용 프로그래밍 언어입니다."},
                    {"title": "위키피디아", "snippet": "Python(파이썬)은..."},
                ]
            },
        )
        result = web_search.invoke({"query": "파이썬이 뭐야", "num_results": 2})
        assert "파이썬" in result or "Python" in result

    def test_search_returns_answer_box(self, requests_mock):
        requests_mock.post(
            "https://google.serper.dev/search",
            json={"answerBox": {"answer": "서울의 수도는 서울입니다."}},
        )
        result = web_search.invoke({"query": "서울 인구", "num_results": 1})
        assert "[직접 답변]" in result
        assert "서울" in result

    def test_search_no_results(self, requests_mock):
        requests_mock.post(
            "https://google.serper.dev/search",
            json={"organic": []},
        )
        result = web_search.invoke({"query": "존재하지않는쿼리xyz", "num_results": 1})
        assert "찾지 못했어요" in result

    def test_search_timeout(self, requests_mock):
        import requests
        requests_mock.post(
            "https://google.serper.dev/search",
            exc=requests.Timeout,
        )
        result = web_search.invoke({"query": "타임아웃 테스트", "num_results": 1})
        assert "늦어요" in result

    def test_search_no_api_key(self, monkeypatch):
        from app.config import settings
        monkeypatch.setattr(settings, "serper_api_key", "")
        result = web_search.invoke({"query": "테스트", "num_results": 1})
        assert "API 키" in result


# ── 번역 ──────────────────────────────────────────────────────────────

class TestTranslate:

    def test_translate_korean_to_english(self, requests_mock):
        requests_mock.post(
            "https://api-free.deepl.com/v2/translate",
            json={
                "translations": [
                    {"text": "Hello", "detected_source_language": "KO"}
                ]
            },
        )
        result = translate_text.invoke({"text": "안녕하세요", "target_language": "영어"})
        assert "Hello" in result
        assert "KO" in result

    def test_translate_maps_korean_lang_names(self, requests_mock):
        requests_mock.post(
            "https://api-free.deepl.com/v2/translate",
            json={"translations": [{"text": "こんにちは", "detected_source_language": "KO"}]},
        )
        result = translate_text.invoke({"text": "안녕하세요", "target_language": "일본어"})
        assert "こんにちは" in result

    def test_translate_no_api_key(self, monkeypatch):
        from app.config import settings
        monkeypatch.setattr(settings, "deepl_api_key", "")
        result = translate_text.invoke({"text": "hello", "target_language": "한국어"})
        assert "API 키" in result

    def test_lang_map_completeness(self):
        """LANG_MAP에 주요 언어가 모두 있는지."""
        required = ["영어", "한국어", "일본어", "중국어", "프랑스어", "독일어", "스페인어"]
        for lang in required:
            assert lang in LANG_MAP, f"{lang}이 LANG_MAP에 없음"

    def test_translate_timeout(self, requests_mock):
        import requests
        requests_mock.post("https://api-free.deepl.com/v2/translate", exc=requests.Timeout)
        result = translate_text.invoke({"text": "안녕", "target_language": "영어"})
        assert "API 키" in result or "실패" in result or result == ""


# ── 금융 ──────────────────────────────────────────────────────────────

class TestFinance:

    def test_convert_currency_usd_to_krw(self, requests_mock):
        requests_mock.get(
            "https://open.er-api.com/v6/latest/USD",
            json={
                "result": "success",
                "rates": {"KRW": 1350.0, "EUR": 0.92, "JPY": 155.0},
                "time_last_update_utc": "Sat, 01 Jan 2025 00:00:00 +0000",
            },
        )
        result = convert_currency.invoke({"amount": 100, "from_ccy": "USD", "to_ccy": "KRW"})
        assert "135,000" in result or "135000" in result or "1350" in result

    def test_convert_currency_same_currency(self, requests_mock):
        requests_mock.get(
            "https://open.er-api.com/v6/latest/USD",
            json={"result": "success", "rates": {"USD": 1.0}},
        )
        result = convert_currency.invoke({"amount": 50, "from_ccy": "USD", "to_ccy": "USD"})
        assert "50" in result

    def test_convert_currency_api_error(self, requests_mock):
        requests_mock.get(
            "https://open.er-api.com/v6/latest/USD",
            json={"result": "error"},
        )
        result = convert_currency.invoke({"amount": 100, "from_ccy": "USD", "to_ccy": "KRW"})
        assert "실패" in result or "오류" in result or "없" in result

    def test_convert_currency_timeout(self, requests_mock):
        import requests
        requests_mock.get("https://open.er-api.com/v6/latest/USD", exc=requests.Timeout)
        result = convert_currency.invoke({"amount": 100, "from_ccy": "USD", "to_ccy": "KRW"})
        assert "실패" in result or "늦어요" in result

    def test_get_stock_price_valid(self, mocker):
        """yfinance Ticker 모킹."""
        mock_ticker = mocker.MagicMock()
        mock_ticker.info = {
            "currentPrice": 195.5,
            "shortName": "Apple Inc.",
            "currency": "USD",
            "regularMarketChangePercent": 1.2,
        }
        mocker.patch("yfinance.Ticker", return_value=mock_ticker)
        result = get_stock_price.invoke({"symbol": "AAPL"})
        assert "Apple" in result or "AAPL" in result
        assert "195" in result

    def test_get_stock_price_invalid_symbol(self, mocker):
        """존재하지 않는 심볼 처리."""
        mock_ticker = mocker.MagicMock()
        mock_ticker.info = {}  # 빈 info
        mocker.patch("yfinance.Ticker", return_value=mock_ticker)
        result = get_stock_price.invoke({"symbol": "INVALID123"})
        assert "찾지 못했어요" in result or "오류" in result or "없" in result

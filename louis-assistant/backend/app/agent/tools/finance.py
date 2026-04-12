"""
루이스 개인비서 - 금융 도구
실시간 환율 변환 및 주가 조회.
"""
import logging

import requests
from langchain_core.tools import tool

log = logging.getLogger("louis.tools.finance")

# 통화 한글→코드 매핑
CCY_MAP: dict[str, str] = {
    "달러": "USD", "미국달러": "USD",
    "유로": "EUR",
    "엔": "JPY", "일본엔": "JPY",
    "위안": "CNY", "중국위안": "CNY",
    "파운드": "GBP",
    "홍콩달러": "HKD",
    "캐나다달러": "CAD",
    "호주달러": "AUD",
    "스위스프랑": "CHF",
    "원": "KRW",
}


@tool
def convert_currency(amount: float, from_ccy: str, to_ccy: str = "KRW") -> str:
    """환율을 변환합니다.

    Args:
        amount: 변환할 금액
        from_ccy: 원래 통화 (한글 또는 ISO 코드, 예: '달러', 'USD')
        to_ccy: 변환할 통화 (한글 또는 ISO 코드, 예: '원', 'KRW')

    Returns:
        변환 결과 문자열
    """
    try:
        from_code = CCY_MAP.get(from_ccy.strip(), from_ccy.upper().strip())
        to_code = CCY_MAP.get(to_ccy.strip(), to_ccy.upper().strip())

        r = requests.get(
            f"https://open.er-api.com/v6/latest/{from_code}",
            timeout=5
        ).json()

        if r.get("result") != "success":
            return f"{from_ccy} 환율 정보를 가져오지 못했어요."

        rate = r["rates"].get(to_code)
        if rate is None:
            return f"{to_ccy} 통화 정보를 찾을 수 없어요."

        converted = amount * rate
        updated = r.get("time_last_update_utc", "")[:10]

        if to_code == "KRW":
            return f"{amount:,.0f} {from_code} = {converted:,.0f}원 (기준일: {updated})"
        else:
            return f"{amount:,.2f} {from_code} = {converted:,.2f} {to_code} (기준일: {updated})"

    except requests.Timeout:
        return "환율 서버 응답이 늦어요."
    except Exception as exc:
        log.error(f"환율 조회 실패: {exc}", exc_info=True)
        return "환율 조회에 실패했어요."


@tool
def get_stock_price(symbol: str) -> str:
    """주식/코인 가격을 조회합니다.

    Args:
        symbol: 종목 코드 또는 이름 (예: 'AAPL', '삼성전자', 'BTC')

    Returns:
        주가 정보 문자열
    """
    try:
        # yfinance 사용 (설치 필요: pip install yfinance)
        import yfinance as yf

        # 한국 주식 접미사 처리
        korean_map = {
            "삼성전자": "005930.KS",
            "카카오": "035720.KS",
            "네이버": "035420.KS",
            "현대차": "005380.KS",
            "lg에너지솔루션": "373220.KS",
        }
        ticker_sym = korean_map.get(symbol.lower(), symbol.upper())

        ticker = yf.Ticker(ticker_sym)
        hist = ticker.history(period="1d")
        if hist.empty:
            return f"'{symbol}' 종목 정보를 찾을 수 없어요."

        price = hist["Close"].iloc[-1]
        prev = hist["Open"].iloc[-1]
        change = price - prev
        pct = (change / prev * 100) if prev else 0
        direction = "상승" if change >= 0 else "하락"

        return f"{symbol} 현재가: {price:,.2f} ({direction} {abs(pct):.1f}%)"

    except ImportError:
        return "주가 조회 기능을 사용하려면 yfinance를 설치해주세요: pip install yfinance"
    except Exception as exc:
        log.error(f"주가 조회 실패: {exc}", exc_info=True)
        return f"'{symbol}' 주가 조회에 실패했어요."

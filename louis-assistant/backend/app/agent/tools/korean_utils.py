"""
루이스 개인비서 - 한국어 유틸리티 도구 (Phase 12)
맞춤법 검사 · 주식/코스피 조회 · 우편번호 검색.

의존성:
  pip install pykrx          ← KRX 주식 조회 (무료, 키 불필요)
  pip install py-hanspell    ← 네이버 맞춤법 검사 (무료, 키 불필요)
"""
import json
import logging
from datetime import datetime, timedelta

import requests
from langchain_core.tools import tool

log = logging.getLogger("louis.tools.korean_utils")


# ── 한국어 맞춤법 검사 ────────────────────────────────────

@tool
def check_spelling(text: str) -> str:
    """한국어 문장의 맞춤법을 검사합니다.

    부산대학교 맞춤법 검사기(무료, API 키 불필요)를 사용합니다.

    Args:
        text: 검사할 한국어 텍스트 (최대 500자)

    Returns:
        JSON 문자열 — corrected(교정 결과), errors(오류 목록), changed(수정 여부)
    """
    if len(text) > 500:
        text = text[:500]

    # 방법 1: py-hanspell (네이버)
    try:
        from hanspell import spell_checker  # type: ignore
        result = spell_checker.check(text)
        return json.dumps({
            "original": text,
            "corrected": result.checked,
            "errors": result.errors,
            "changed": result.checked != text,
        }, ensure_ascii=False)
    except ImportError:
        pass  # 미설치 시 부산대 API로 폴백
    except Exception as e:
        log.warning(f"hanspell 실패: {e}")

    # 방법 2: 부산대학교 맞춤법 검사기 (무료 공개 API)
    try:
        url = "https://speller.cs.pusan.ac.kr/results"
        resp = requests.post(
            url,
            data={"text1": text},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=6,
        )
        # HTML 응답에서 교정 결과 추출
        import re
        corrected_match = re.search(r'<textarea[^>]*id="erow1"[^>]*>(.*?)</textarea>', resp.text, re.DOTALL)
        if corrected_match:
            corrected = corrected_match.group(1).strip()
            return json.dumps({
                "original": text,
                "corrected": corrected,
                "changed": corrected != text,
                "source": "pusan.ac.kr",
            }, ensure_ascii=False)
    except Exception as e:
        log.warning(f"부산대 맞춤법 검사 실패: {e}")

    # 폴백: 검사 불가 안내
    return json.dumps({
        "original": text,
        "corrected": text,
        "changed": False,
        "error": "맞춤법 검사 서비스에 연결할 수 없어요. py-hanspell 설치를 권장합니다.",
    }, ensure_ascii=False)


# ── KRX 주식 / 코스피 조회 ────────────────────────────────

def _get_trading_date(offset: int = 0) -> str:
    """영업일 기준 날짜를 YYYYMMDD로 반환 (주말 보정)."""
    dt = datetime.now() + timedelta(days=offset)
    # 장 마감 전(15:30 이전)이면 전일 데이터 사용
    if dt.date() == datetime.now().date() and datetime.now().hour < 15:
        dt -= timedelta(days=1)
    # 주말이면 금요일로 이동
    while dt.weekday() >= 5:
        dt -= timedelta(days=1)
    return dt.strftime("%Y%m%d")


@tool
def get_stock_price(company: str) -> str:
    """한국 주식(KRX 상장 종목) 현재가 및 등락률을 조회합니다.

    Args:
        company: 종목명 또는 종목코드 (예: 삼성전자, 035420, LG에너지솔루션)

    Returns:
        JSON 문자열 — ticker, company, price, change, change_rate,
        volume, market_cap, 52w_high, 52w_low
    """
    try:
        from pykrx import stock  # type: ignore
    except ImportError:
        return json.dumps({"error": "pykrx 미설치. pip install pykrx"}, ensure_ascii=False)

    try:
        date_str = _get_trading_date()

        # 종목코드 조회 (종목명으로 검색)
        ticker = company
        if not company.isdigit():
            tickers = stock.get_market_ticker_list(market="ALL")
            for t in tickers:
                name = stock.get_market_ticker_name(t)
                if company in name:
                    ticker = t
                    company = name
                    break
            else:
                return json.dumps({
                    "error": f"'{company}' 종목을 찾을 수 없어요.",
                    "hint": "종목코드(6자리 숫자)로 검색해보세요.",
                }, ensure_ascii=False)

        # 현재가 조회
        df = stock.get_market_ohlcv_by_date(date_str, date_str, ticker)
        if df.empty:
            # 더 오래된 날짜로 재시도
            date_str = _get_trading_date(-1)
            df = stock.get_market_ohlcv_by_date(date_str, date_str, ticker)
            if df.empty:
                return json.dumps({"error": "주가 데이터를 가져올 수 없어요."}, ensure_ascii=False)

        row = df.iloc[-1]
        close_price = int(row.get("종가", row.get("Close", 0)))
        open_price = int(row.get("시가", row.get("Open", 0)))
        high_price = int(row.get("고가", row.get("High", 0)))
        low_price = int(row.get("저가", row.get("Low", 0)))
        volume = int(row.get("거래량", row.get("Volume", 0)))

        # 등락 계산
        change = close_price - open_price
        change_rate = (change / open_price * 100) if open_price > 0 else 0

        result = {
            "ticker": ticker,
            "company": company,
            "date": date_str,
            "price": f"{close_price:,}원",
            "open": f"{open_price:,}원",
            "high": f"{high_price:,}원",
            "low": f"{low_price:,}원",
            "change": f"{'▲' if change >= 0 else '▼'} {abs(change):,}원",
            "change_rate": f"{change_rate:+.2f}%",
            "volume": f"{volume:,}주",
        }
        return json.dumps(result, ensure_ascii=False)

    except Exception as e:
        log.error(f"주가 조회 실패: {e}", exc_info=True)
        return json.dumps({"error": "주가 조회 중 오류가 발생했어요."}, ensure_ascii=False)


@tool
def get_kospi_index() -> str:
    """코스피/코스닥 지수 현황을 조회합니다.

    Returns:
        JSON 문자열 — kospi(지수, 등락률), kosdaq(지수, 등락률)
    """
    try:
        from pykrx import stock  # type: ignore
    except ImportError:
        return json.dumps({"error": "pykrx 미설치. pip install pykrx"}, ensure_ascii=False)

    try:
        date_str = _get_trading_date()
        prev_date = _get_trading_date(-1)

        indices = {}
        for name, ticker in [("kospi", "1001"), ("kosdaq", "2001")]:
            df = stock.get_index_ohlcv_by_date(prev_date, date_str, ticker)
            if df.empty:
                indices[name] = {"error": "데이터 없음"}
                continue
            latest = df.iloc[-1]
            prev = df.iloc[-2] if len(df) >= 2 else df.iloc[-1]

            close = float(latest.get("종가", latest.get("Close", 0)))
            prev_close = float(prev.get("종가", prev.get("Close", close)))
            change = close - prev_close
            change_rate = (change / prev_close * 100) if prev_close > 0 else 0

            indices[name] = {
                "index": f"{close:,.2f}",
                "change": f"{'▲' if change >= 0 else '▼'} {abs(change):.2f}",
                "change_rate": f"{change_rate:+.2f}%",
            }

        indices["date"] = date_str
        return json.dumps(indices, ensure_ascii=False)

    except Exception as e:
        log.error(f"지수 조회 실패: {e}", exc_info=True)
        return json.dumps({"error": "지수 조회 중 오류가 발생했어요."}, ensure_ascii=False)


# ── 우편번호 검색 ─────────────────────────────────────────

@tool
def search_postal_code(address: str) -> str:
    """주소로 우편번호를 검색합니다 (카카오 주소 API 사용).

    Args:
        address: 검색할 주소 (예: 강남구 테헤란로 152, 판교역로 235)

    Returns:
        JSON 문자열 — 주소 목록 (road_address, jibun_address, zip_code)
    """
    kakao_key = getattr(__import__("app.config", fromlist=["settings"]), "settings").kakao_api_key \
        if hasattr(__import__("app.config", fromlist=["settings"]).settings, "kakao_api_key") else None

    if not kakao_key:
        # 도로명주소 개발자센터 무료 API 폴백
        try:
            url = "https://business.juso.go.kr/addrlink/addrLinkApi.do"
            params = {
                "confmKey": "devU01TX0FVVEgyMDI1MDQxMzE2NTkxOTExNTI2ODk=",  # 테스트 키
                "currentPage": 1,
                "countPerPage": 5,
                "keyword": address,
                "resultType": "json",
            }
            resp = requests.get(url, params=params, timeout=6)
            data = resp.json().get("results", {})
            juso_list = data.get("juso", [])
            if juso_list:
                result = [
                    {
                        "road_address": j.get("roadAddr", ""),
                        "jibun_address": j.get("jibunAddr", ""),
                        "zip_code": j.get("zipNo", ""),
                        "building_name": j.get("bdNm", ""),
                    }
                    for j in juso_list[:5]
                ]
                return json.dumps({"query": address, "results": result}, ensure_ascii=False)
        except Exception as e:
            log.warning(f"도로명주소 API 실패: {e}")

        return json.dumps({"error": "우편번호 검색 서비스를 이용할 수 없어요."}, ensure_ascii=False)

    # 카카오 주소 API
    try:
        url = "https://dapi.kakao.com/v2/local/search/address.json"
        headers = {"Authorization": f"KakaoAK {kakao_key}"}
        resp = requests.get(url, params={"query": address, "size": 5},
                            headers=headers, timeout=6)
        documents = resp.json().get("documents", [])

        result = []
        for d in documents:
            road = d.get("road_address")
            result.append({
                "road_address": road["address_name"] if road else "",
                "jibun_address": d.get("address", {}).get("address_name", ""),
                "zip_code": road["zone_no"] if road else "",
                "building_name": road.get("building_name", "") if road else "",
            })

        if not result:
            return json.dumps({"message": f"'{address}' 주소를 찾을 수 없어요."}, ensure_ascii=False)

        return json.dumps({"query": address, "results": result}, ensure_ascii=False)

    except Exception as e:
        log.error(f"우편번호 검색 실패: {e}", exc_info=True)
        return json.dumps({"error": "우편번호 검색 중 오류가 발생했어요."}, ensure_ascii=False)

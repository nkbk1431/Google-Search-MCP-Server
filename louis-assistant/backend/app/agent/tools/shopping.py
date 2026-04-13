"""
루이스 개인비서 - 쇼핑 검색 도구 (Phase 12)
네이버 쇼핑 API + 쿠팡/올리브영/다이소 상품 검색.

필요 환경변수:
  NAVER_CLIENT_ID      ← 네이버 개발자센터 앱 클라이언트 ID
  NAVER_CLIENT_SECRET  ← 네이버 개발자센터 앱 클라이언트 시크릿
"""
import json
import logging
import urllib.parse

import requests
from langchain_core.tools import tool

from app.config import settings

log = logging.getLogger("louis.tools.shopping")


def _naver_shopping_search(query: str, display: int = 5) -> list[dict]:
    """네이버 쇼핑 API로 상품을 검색합니다."""
    client_id = getattr(settings, "naver_client_id", None)
    client_secret = getattr(settings, "naver_client_secret", None)
    if not client_id or not client_secret:
        raise ValueError("NAVER_CLIENT_ID / NAVER_CLIENT_SECRET 환경변수 없음")

    url = "https://openapi.naver.com/v1/search/shop.json"
    params = {
        "query": query,
        "display": display,
        "sort": "asc",  # 가격순
    }
    headers = {
        "X-Naver-Client-Id": client_id,
        "X-Naver-Client-Secret": client_secret,
    }
    resp = requests.get(url, params=params, headers=headers, timeout=6)
    resp.raise_for_status()
    items = resp.json().get("items", [])
    return [
        {
            "title": i["title"].replace("<b>", "").replace("</b>", ""),
            "price": int(i["lprice"]),
            "mall": i["mallName"],
            "link": i["link"],
            "image": i.get("image", ""),
        }
        for i in items
    ]


def _coupang_search(query: str) -> list[dict]:
    """쿠팡 로켓배송 상품 웹 크롤링 (공개 API 없음)."""
    q = urllib.parse.quote(query)
    url = f"https://www.coupang.com/np/search?component=&q={q}&channel=user"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "ko-KR,ko;q=0.9",
    }
    try:
        resp = requests.get(url, headers=headers, timeout=8)
        # 쿠팡은 JS 렌더링이 필요해서 실제 상품 목록 파싱이 어려움
        # Flutter 앱에서 OPEN_BROWSER 인텐트로 처리
        if resp.status_code == 200:
            return [{
                "action": "OPEN_BROWSER",
                "url": url,
                "message": f"쿠팡에서 '{query}' 검색 결과를 브라우저로 열게요.",
            }]
    except Exception:
        pass
    return []


@tool
def search_shopping(
    query: str,
    platform: str = "naver",
    max_price: int = 0,
) -> str:
    """쇼핑 상품을 검색합니다.

    Args:
        query:     검색어 (예: 에어팟 프로, 나이키 운동화)
        platform:  플랫폼 (naver, coupang, oliveyoung, daiso). 기본값 naver.
        max_price: 최대 가격 필터 (원). 0이면 필터 없음.

    Returns:
        JSON 문자열 — 상품 목록 (title, price, mall, link) 또는
        OPEN_BROWSER 액션 (쿠팡 등 직접 크롤링 불가 플랫폼)
    """
    platform = platform.lower()

    # 쿠팡/올리브영/다이소는 브라우저 열기로 처리
    browser_platforms = {
        "coupang": f"https://www.coupang.com/np/search?q={urllib.parse.quote(query)}",
        "oliveyoung": f"https://www.oliveyoung.co.kr/store/search/getSearchMain.do?query={urllib.parse.quote(query)}",
        "daiso": f"https://www.daisomall.co.kr/shop/search?q={urllib.parse.quote(query)}",
    }
    if platform in browser_platforms:
        url = browser_platforms[platform]
        return json.dumps({
            "action": "OPEN_BROWSER",
            "platform": platform,
            "url": url,
            "message": f"{platform}에서 '{query}' 검색 결과를 브라우저로 열게요.",
            "query": query,
        }, ensure_ascii=False)

    # 네이버 쇼핑 API
    try:
        items = _naver_shopping_search(query, display=8)
    except ValueError as e:
        # API 키 없으면 네이버 검색 페이지로 폴백
        url = f"https://search.naver.com/search.naver?query={urllib.parse.quote(query)}&where=shopping"
        return json.dumps({
            "action": "OPEN_BROWSER",
            "url": url,
            "message": f"네이버 쇼핑에서 '{query}' 검색 결과를 브라우저로 열게요.",
            "hint": str(e),
        }, ensure_ascii=False)
    except Exception as e:
        log.error(f"네이버 쇼핑 검색 실패: {e}", exc_info=True)
        return json.dumps({"error": "쇼핑 검색 중 오류가 발생했어요."}, ensure_ascii=False)

    # 가격 필터
    if max_price > 0:
        items = [i for i in items if i["price"] <= max_price]

    if not items:
        return json.dumps({"message": f"'{query}' 검색 결과가 없어요.", "query": query}, ensure_ascii=False)

    return json.dumps({
        "query": query,
        "platform": "naver",
        "total": len(items),
        "items": items,
    }, ensure_ascii=False)


@tool
def search_used_market(query: str) -> str:
    """중고나라/번개장터 중고 상품을 검색합니다.

    Args:
        query: 검색어 (예: 아이폰 15, 맥북 M3)

    Returns:
        JSON 문자열 — OPEN_BROWSER 액션 (Flutter 앱이 처리)
    """
    bunjang_url = f"https://m.bunjang.co.kr/search/products?q={urllib.parse.quote(query)}"
    joonggonara_url = f"https://search.naver.com/search.naver?where=cafeblog&q={urllib.parse.quote(query)}&um=cafe_id:10050146"

    return json.dumps({
        "query": query,
        "platforms": [
            {
                "name": "번개장터",
                "action": "OPEN_BROWSER",
                "url": bunjang_url,
            },
            {
                "name": "중고나라",
                "action": "OPEN_BROWSER",
                "url": joonggonara_url,
            },
        ],
        "message": f"'{query}' 중고 검색을 시작할게요. 번개장터와 중고나라 중 어디로 갈까요?",
    }, ensure_ascii=False)

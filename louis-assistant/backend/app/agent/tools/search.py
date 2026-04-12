"""
루이스 개인비서 - 웹 검색 도구
Serper.dev API로 Google 검색 결과를 가져옵니다.
"""
import logging

import requests
from langchain_core.tools import tool

from app.config import settings

log = logging.getLogger("louis.tools.search")


@tool
def web_search(query: str, num_results: int = 3) -> str:
    """인터넷에서 최신 정보를 검색합니다.

    Args:
        query: 검색 쿼리
        num_results: 가져올 결과 수. 기본 3개.

    Returns:
        검색 결과 요약 문자열
    """
    if not settings.serper_api_key:
        return f"웹 검색 기능을 사용하려면 Serper API 키를 설정해주세요."

    try:
        r = requests.post(
            "https://google.serper.dev/search",
            headers={
                "X-API-KEY": settings.serper_api_key,
                "Content-Type": "application/json",
            },
            json={"q": query, "hl": "ko", "gl": "kr", "num": num_results},
            timeout=5,
        )
        data = r.json()

        results = []

        # Answer Box (직접 답변)
        if "answerBox" in data:
            ab = data["answerBox"]
            answer = ab.get("answer") or ab.get("snippet", "")
            if answer:
                results.append(f"[직접 답변] {answer}")

        # Knowledge Graph
        if "knowledgeGraph" in data:
            kg = data["knowledgeGraph"]
            desc = kg.get("description", "")
            if desc:
                results.append(f"[정보] {desc[:200]}")

        # 일반 검색 결과
        for item in data.get("organic", [])[:num_results]:
            title = item.get("title", "")
            snippet = item.get("snippet", "")
            if snippet:
                results.append(f"- {title}: {snippet[:150]}")

        if not results:
            return f"'{query}' 검색 결과를 찾지 못했어요."

        return "\n".join(results)

    except requests.Timeout:
        return "검색 서버 응답이 늦어요."
    except Exception as exc:
        log.error(f"웹 검색 실패: {exc}", exc_info=True)
        return "웹 검색에 실패했어요."

"""
루이스 개인비서 - 스포츠 경기 결과 도구 (Phase 12)
KBO 야구 · K리그 축구 · LCK e스포츠 경기 결과/일정 조회.

네이버 스포츠 공개 API를 활용합니다 (별도 키 불필요).
"""
import json
import logging
from datetime import datetime, timedelta

import requests
from langchain_core.tools import tool

log = logging.getLogger("louis.tools.sports")

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Referer": "https://sports.naver.com/",
}

# KBO 팀 별칭 정규화
_KBO_TEAM_ALIAS: dict[str, str] = {
    "엘지": "LG", "엘지트윈스": "LG", "lg": "LG",
    "두산": "두산", "베어스": "두산",
    "기아": "KIA", "기아타이거즈": "KIA", "kia": "KIA",
    "삼성": "삼성", "삼성라이온즈": "삼성",
    "한화": "한화", "한화이글스": "한화",
    "롯데": "롯데", "롯데자이언츠": "롯데",
    "kt": "KT", "kt위즈": "KT",
    "ssg": "SSG", "ssg랜더스": "SSG",
    "nc": "NC", "nc다이노스": "NC",
    "키움": "키움", "키움히어로즈": "키움",
}

# K리그 팀 별칭 정규화
_KLEAGUE_TEAM_ALIAS: dict[str, str] = {
    "전북": "전북현대", "전북현대": "전북현대",
    "수원삼성": "수원삼성", "수원": "수원삼성",
    "울산": "울산현대", "울산현대": "울산현대",
    "서울": "FC서울", "fc서울": "FC서울",
    "포항": "포항스틸러스", "포항스틸러스": "포항스틸러스",
    "인천": "인천유나이티드", "인천유나이티드": "인천유나이티드",
    "제주": "제주유나이티드", "제주유나이티드": "제주유나이티드",
    "성남": "성남FC", "성남fc": "성남FC",
}


def _date_str(offset: int = 0) -> str:
    """오늘 기준 offset일 날짜를 YYYYMMDD 형식으로 반환."""
    return (datetime.now() + timedelta(days=offset)).strftime("%Y%m%d")


def _parse_date_input(date_str: str) -> str:
    mapping = {"오늘": 0, "어제": -1, "내일": 1, "그제": -2}
    if date_str in mapping:
        return _date_str(mapping[date_str])
    cleaned = date_str.replace("-", "").replace("/", "").replace(".", "")
    if len(cleaned) == 8 and cleaned.isdigit():
        return cleaned
    return _date_str(0)


# ── KBO 야구 ──────────────────────────────────────────────

@tool
def get_kbo_results(date: str = "오늘", team: str = "") -> str:
    """KBO 프로야구 경기 결과 또는 일정을 조회합니다.

    Args:
        date: '오늘', '어제', '내일' 또는 날짜(20250415). 기본값 오늘.
        team: 특정 팀만 필터 (예: LG, 기아, 두산). 비워두면 전체.

    Returns:
        JSON 문자열 — 경기 목록 (home_team, away_team, score, status, stadium)
    """
    date_str = _parse_date_input(date)
    url = f"https://sports.news.naver.com/kbaseball/schedule/index?date={date_str}"

    try:
        resp = requests.get(
            f"https://api-gw.sports.naver.com/schedule/games"
            f"?fields=basic&upperCategoryId=kbaseball&categoryId=kbo"
            f"&fromDate={date_str}&toDate={date_str}&round=&home=",
            headers=_HEADERS,
            timeout=8,
        )
        data = resp.json()
        games_raw = data.get("result", {}).get("games", [])

        if not games_raw:
            return json.dumps({
                "date": date_str,
                "message": f"{date_str} KBO 경기 일정이 없어요.",
                "url": url,
            }, ensure_ascii=False)

        games = []
        for g in games_raw:
            home = g.get("homeTeamName", "")
            away = g.get("awayTeamName", "")
            home_score = g.get("homeTeamScore", "")
            away_score = g.get("awayTeamScore", "")
            status = g.get("gameStatusCd", "")

            # 팀 필터
            if team:
                norm = _KBO_TEAM_ALIAS.get(team.lower(), team)
                if norm not in (home, away):
                    continue

            games.append({
                "home_team": home,
                "away_team": away,
                "score": f"{away_score} : {home_score}" if home_score != "" else "예정",
                "status": status,
                "stadium": g.get("stadium", ""),
                "start_time": g.get("gameStartTime", ""),
            })

        if not games:
            return json.dumps({
                "date": date_str,
                "message": f"{team} 경기가 없어요.",
            }, ensure_ascii=False)

        return json.dumps({
            "league": "KBO",
            "date": date_str,
            "games": games,
        }, ensure_ascii=False)

    except Exception as e:
        log.error(f"KBO 조회 실패: {e}", exc_info=True)
        # 폴백: 네이버 스포츠 링크 반환
        return json.dumps({
            "action": "OPEN_BROWSER",
            "url": url,
            "message": f"KBO 경기 일정을 브라우저에서 확인해드릴게요.",
        }, ensure_ascii=False)


# ── K리그 축구 ────────────────────────────────────────────

@tool
def get_kleague_results(date: str = "오늘", team: str = "") -> str:
    """K리그1/K리그2 축구 경기 결과 또는 일정을 조회합니다.

    Args:
        date: '오늘', '어제', '내일' 또는 날짜(20250415). 기본값 오늘.
        team: 특정 팀 필터 (예: 전북, 울산, FC서울). 비워두면 전체.

    Returns:
        JSON 문자열 — 경기 목록 (home_team, away_team, score, status, stadium)
    """
    date_str = _parse_date_input(date)
    url = f"https://sports.news.naver.com/soccer/schedule/index?date={date_str}&category=kleague1"

    try:
        resp = requests.get(
            f"https://api-gw.sports.naver.com/schedule/games"
            f"?fields=basic&upperCategoryId=soccer&categoryId=kleague1"
            f"&fromDate={date_str}&toDate={date_str}&round=&home=",
            headers=_HEADERS,
            timeout=8,
        )
        data = resp.json()
        games_raw = data.get("result", {}).get("games", [])

        if not games_raw:
            return json.dumps({
                "date": date_str,
                "message": f"{date_str} K리그 경기 일정이 없어요.",
                "url": url,
            }, ensure_ascii=False)

        games = []
        for g in games_raw:
            home = g.get("homeTeamName", "")
            away = g.get("awayTeamName", "")

            if team:
                norm = _KLEAGUE_TEAM_ALIAS.get(team.lower(), team)
                if norm not in (home, away):
                    continue

            games.append({
                "home_team": home,
                "away_team": away,
                "score": f"{g.get('awayTeamScore', '')} : {g.get('homeTeamScore', '')}"
                         if g.get("homeTeamScore", "") != "" else "예정",
                "status": g.get("gameStatusCd", ""),
                "stadium": g.get("stadium", ""),
                "start_time": g.get("gameStartTime", ""),
            })

        if not games:
            return json.dumps({
                "date": date_str,
                "message": f"{team} 경기가 없어요.",
            }, ensure_ascii=False)

        return json.dumps({
            "league": "K리그",
            "date": date_str,
            "games": games,
        }, ensure_ascii=False)

    except Exception as e:
        log.error(f"K리그 조회 실패: {e}", exc_info=True)
        return json.dumps({
            "action": "OPEN_BROWSER",
            "url": url,
            "message": "K리그 경기 일정을 브라우저에서 확인해드릴게요.",
        }, ensure_ascii=False)


# ── LCK e스포츠 ───────────────────────────────────────────

@tool
def get_lck_results(date: str = "오늘") -> str:
    """LCK 리그 오브 레전드 챔피언스 코리아 경기 결과를 조회합니다.

    Args:
        date: '오늘', '어제', '내일' 또는 날짜(20250415). 기본값 오늘.

    Returns:
        JSON 문자열 — 경기 목록 또는 브라우저 오픈 액션
    """
    date_str = _parse_date_input(date)
    url = f"https://sports.news.naver.com/esports/schedule/index?category=lck&date={date_str}"

    try:
        resp = requests.get(
            f"https://api-gw.sports.naver.com/schedule/games"
            f"?fields=basic&upperCategoryId=esports&categoryId=lck"
            f"&fromDate={date_str}&toDate={date_str}",
            headers=_HEADERS,
            timeout=8,
        )
        data = resp.json()
        games_raw = data.get("result", {}).get("games", [])

        if not games_raw:
            return json.dumps({
                "date": date_str,
                "message": f"{date_str} LCK 경기 일정이 없어요.",
                "url": url,
            }, ensure_ascii=False)

        games = []
        for g in games_raw:
            games.append({
                "home_team": g.get("homeTeamName", ""),
                "away_team": g.get("awayTeamName", ""),
                "score": f"{g.get('awayTeamScore', '')} : {g.get('homeTeamScore', '')}"
                         if g.get("homeTeamScore", "") != "" else "예정",
                "status": g.get("gameStatusCd", ""),
                "start_time": g.get("gameStartTime", ""),
            })

        return json.dumps({
            "league": "LCK",
            "date": date_str,
            "games": games,
        }, ensure_ascii=False)

    except Exception as e:
        log.error(f"LCK 조회 실패: {e}", exc_info=True)
        return json.dumps({
            "action": "OPEN_BROWSER",
            "url": url,
            "message": "LCK 경기 일정을 브라우저에서 확인해드릴게요.",
        }, ensure_ascii=False)

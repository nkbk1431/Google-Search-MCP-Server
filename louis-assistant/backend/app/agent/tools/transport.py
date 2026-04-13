"""
루이스 개인비서 - 교통 도구 (Phase 12)
SRT/KTX 열차 조회 + 서울 지하철 실시간 도착 정보.

필요 패키지:
  pip install srt-py korail2
필요 환경변수:
  SRT_ID, SRT_PW          ← SRT 회원 아이디/비밀번호
  KORAIL_ID, KORAIL_PW    ← 코레일 멤버십 아이디/비밀번호
  SEOUL_API_KEY           ← 서울 열린데이터광장 API 키 (subway)
"""
import json
import logging
from datetime import datetime, timedelta

import requests
from langchain_core.tools import tool

from app.config import settings

log = logging.getLogger("louis.tools.transport")

# 역명 정규화 (SRT·KTX 공통)
_STATION_ALIAS: dict[str, str] = {
    "서울역": "서울", "수서역": "수서", "부산역": "부산",
    "동대구역": "동대구", "대전역": "대전", "광주송정역": "광주송정",
    "행신역": "행신", "천안아산역": "천안아산", "오송역": "오송",
    "익산역": "익산", "전주역": "전주", "여수엑스포역": "여수엑스포",
    "목포역": "목포", "포항역": "포항", "울산역": "울산(통도사)",
    "진주역": "진주", "창원중앙역": "창원중앙", "마산역": "마산",
}

# 지하철 노선 코드 매핑 (서울 열린데이터광장)
_LINE_CODE: dict[str, str] = {
    "1호선": "1001", "2호선": "1002", "3호선": "1003",
    "4호선": "1004", "5호선": "1005", "6호선": "1006",
    "7호선": "1007", "8호선": "1008", "9호선": "1009",
    "경의중앙선": "1063", "공항철도": "1065", "경춘선": "1067",
    "수인분당선": "1075", "신분당선": "1077", "우이신설선": "1092",
    "경강선": "1079",
}


def _normalize_station(name: str) -> str:
    return _STATION_ALIAS.get(name, name.replace("역", "").strip())


def _today_str() -> str:
    return datetime.now().strftime("%Y%m%d")


def _parse_date(date_str: str) -> str:
    """'오늘', '내일', '모레' 또는 날짜 문자열을 YYYYMMDD로 변환."""
    today = datetime.now()
    mapping = {"오늘": 0, "내일": 1, "모레": 2, "글피": 3}
    if date_str in mapping:
        return (today + timedelta(days=mapping[date_str])).strftime("%Y%m%d")
    # 이미 8자리 숫자면 그대로
    cleaned = date_str.replace("-", "").replace("/", "").replace(".", "")
    if len(cleaned) == 8 and cleaned.isdigit():
        return cleaned
    return today.strftime("%Y%m%d")


# ── SRT 열차 조회 ─────────────────────────────────────────

@tool
def search_srt(
    departure: str,
    arrival: str,
    date: str = "오늘",
    time: str = "0600",
    passengers: int = 1,
) -> str:
    """SRT 열차 시간표와 잔여석을 조회합니다.

    Args:
        departure: 출발역 (예: 수서, 동탄, 지제)
        arrival:   도착역 (예: 부산, 대전, 광주송정)
        date:      날짜 (오늘/내일/모레 또는 20250415). 기본값 오늘.
        time:      최소 출발 시각 (HHMM). 기본값 0600.
        passengers: 승객 수. 기본값 1.

    Returns:
        JSON 문자열 — 열차 목록 (srt_no, departure_time, arrival_time,
        travel_time, general_seat, special_seat, price)
    """
    try:
        from srt import SRT, SRTError  # type: ignore
    except ImportError:
        return json.dumps({"error": "SRT 라이브러리 미설치. pip install srt-py"}, ensure_ascii=False)

    srt_id = getattr(settings, "srt_id", None)
    srt_pw = getattr(settings, "srt_pw", None)
    if not srt_id or not srt_pw:
        return json.dumps({"error": "SRT_ID / SRT_PW 환경변수를 설정해주세요."}, ensure_ascii=False)

    dep = _normalize_station(departure)
    arr = _normalize_station(arrival)
    date_str = _parse_date(date)

    try:
        srt = SRT(srt_id, srt_pw)
        trains = srt.search_train(
            dep, arr,
            date=date_str,
            time=time,
            passengers=[passengers],
        )
        if not trains:
            return json.dumps({"message": f"{dep} → {arr} ({date_str}) 조건에 맞는 열차가 없어요."}, ensure_ascii=False)

        result = []
        for t in trains[:5]:  # 최대 5편
            result.append({
                "srt_no": t.train_name,
                "departure_time": t.dep_time,
                "arrival_time": t.arr_time,
                "travel_time": t.run_time,
                "general_seat": t.seat_available(),
                "price": t.general_price if hasattr(t, "general_price") else "-",
            })
        return json.dumps({"trains": result, "route": f"{dep} → {arr}", "date": date_str}, ensure_ascii=False)

    except SRTError as e:
        log.warning(f"SRT 조회 오류: {e}")
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    except Exception as e:
        log.error(f"SRT 예외: {e}", exc_info=True)
        return json.dumps({"error": "SRT 조회 중 오류가 발생했어요."}, ensure_ascii=False)


# ── KTX 열차 조회 ─────────────────────────────────────────

@tool
def search_ktx(
    departure: str,
    arrival: str,
    date: str = "오늘",
    time: str = "0600",
    passengers: int = 1,
) -> str:
    """KTX/무궁화/새마을 열차 시간표와 잔여석을 조회합니다.

    Args:
        departure: 출발역 (예: 서울, 용산, 행신)
        arrival:   도착역 (예: 부산, 경주, 여수엑스포)
        date:      날짜 (오늘/내일/모레 또는 20250415). 기본값 오늘.
        time:      최소 출발 시각 (HHMM). 기본값 0600.
        passengers: 승객 수. 기본값 1.

    Returns:
        JSON 문자열 — 열차 목록 (train_type, train_no, departure_time,
        arrival_time, travel_time, special_seat, general_seat, price)
    """
    try:
        from korail2 import Korail, KorailError, ReserveOption  # type: ignore
    except ImportError:
        return json.dumps({"error": "korail2 라이브러리 미설치. pip install korail2"}, ensure_ascii=False)

    korail_id = getattr(settings, "korail_id", None)
    korail_pw = getattr(settings, "korail_pw", None)
    if not korail_id or not korail_pw:
        return json.dumps({"error": "KORAIL_ID / KORAIL_PW 환경변수를 설정해주세요."}, ensure_ascii=False)

    dep = _normalize_station(departure)
    arr = _normalize_station(arrival)
    date_str = _parse_date(date)

    try:
        korail = Korail(korail_id, korail_pw, auto_login=True)
        trains = korail.search_train(
            dep, arr,
            date=date_str,
            time=time,
            train_type=ReserveOption.TRAIN_TYPE_ALL,
        )
        if not trains:
            return json.dumps({"message": f"{dep} → {arr} ({date_str}) 조건에 맞는 열차가 없어요."}, ensure_ascii=False)

        result = []
        for t in trains[:5]:
            result.append({
                "train_type": t.train_type_name,
                "train_no": t.train_no,
                "departure_time": t.dep_time,
                "arrival_time": t.arr_time,
                "travel_time": t.run_time,
                "general_seat": t.general_seat_state,
                "special_seat": t.special_seat_state,
            })
        return json.dumps({"trains": result, "route": f"{dep} → {arr}", "date": date_str}, ensure_ascii=False)

    except KorailError as e:
        log.warning(f"KTX 조회 오류: {e}")
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    except Exception as e:
        log.error(f"KTX 예외: {e}", exc_info=True)
        return json.dumps({"error": "KTX 조회 중 오류가 발생했어요."}, ensure_ascii=False)


# ── 서울 지하철 실시간 도착 ────────────────────────────────

@tool
def get_subway_arrival(station: str, line: str = "") -> str:
    """서울 지하철 실시간 도착 정보를 조회합니다.

    Args:
        station: 역 이름 (예: 강남, 홍대입구, 서울역)
        line:    노선 필터 (예: 2호선, 신분당선). 비워두면 전체 노선.

    Returns:
        JSON 문자열 — 도착 예정 열차 목록
        (line_name, destination, arrival_msg, btrainNo)
    """
    api_key = getattr(settings, "seoul_api_key", None)
    if not api_key:
        return json.dumps({"error": "SEOUL_API_KEY 환경변수를 설정해주세요. (서울 열린데이터광장)"}, ensure_ascii=False)

    station_name = station.replace("역", "").strip()
    url = (
        f"http://swopenapi.seoul.go.kr/api/subway/"
        f"{api_key}/json/realtimeStationArrival/0/20/{station_name}"
    )

    try:
        resp = requests.get(url, timeout=5)
        data = resp.json()

        if "realtimeArrivalList" not in data:
            msg = data.get("errorMessage", {}).get("message", "역 정보를 찾을 수 없어요.")
            return json.dumps({"error": msg}, ensure_ascii=False)

        arrivals = data["realtimeArrivalList"]

        # 노선 필터링
        if line:
            line_key = line if "호선" in line or "선" in line else f"{line}호선"
            arrivals = [a for a in arrivals if line_key in a.get("subwayId", "")
                        or line_key in a.get("trainLineNm", "")]

        if not arrivals:
            return json.dumps({
                "message": f"{station_name}역 실시간 도착 정보가 없어요.",
                "station": station_name,
            }, ensure_ascii=False)

        result = []
        for a in arrivals[:6]:
            result.append({
                "line_name": a.get("trainLineNm", ""),
                "destination": a.get("bstatnNm", ""),
                "direction": a.get("updnLine", ""),
                "arrival_msg": a.get("arvlMsg2", ""),
                "arrival_msg2": a.get("arvlMsg3", ""),
                "train_no": a.get("btrainNo", ""),
            })

        return json.dumps({
            "station": station_name,
            "arrivals": result,
            "updated_at": datetime.now().strftime("%H:%M:%S"),
        }, ensure_ascii=False)

    except requests.Timeout:
        return json.dumps({"error": "지하철 API 응답이 늦어요."}, ensure_ascii=False)
    except Exception as e:
        log.error(f"지하철 실시간 조회 실패: {e}", exc_info=True)
        return json.dumps({"error": "지하철 정보 조회 중 오류가 발생했어요."}, ensure_ascii=False)

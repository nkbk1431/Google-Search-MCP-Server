"""
루이스 개인비서 - 의도 분류 라우터
LLM 호출 없이 키워드 기반으로 1차 분류하여 비용 절감.
"""
import re
from dataclasses import dataclass
from enum import Enum


class Intent(str, Enum):
    WEATHER = "weather"
    CALENDAR = "calendar"
    REMINDER = "reminder"
    TODO = "todo"
    MEMO = "memo"
    FINANCE = "finance"
    TRANSLATE = "translate"
    SEARCH = "search"
    TIMER = "timer"
    ALARM = "alarm"
    COMMUNICATION = "communication"
    MEDIA = "media"
    NAVIGATION = "navigation"
    SMART_HOME = "smart_home"
    # Phase 12 추가
    TRAIN = "train"          # SRT/KTX 열차 조회
    SUBWAY = "subway"        # 지하철 실시간 도착
    SHOPPING = "shopping"    # 쇼핑 검색
    SPORTS = "sports"        # KBO/K리그/LCK 경기
    STOCK = "stock"          # 주식/코스피 조회
    SPELLING = "spelling"    # 맞춤법 검사
    POSTAL = "postal"        # 우편번호 검색
    GENERAL = "general"      # LLM으로 넘길 범용


@dataclass
class RouterResult:
    intent: Intent
    confidence: float        # 0.0 ~ 1.0
    needs_llm: bool          # True면 LangGraph Agent 호출 필요
    extracted: dict          # 키워드에서 추출한 데이터


# 키워드 패턴 정의 (우선순위 순서)
_PATTERNS: list[tuple[Intent, list[str]]] = [
    (Intent.WEATHER, [
        "날씨", "기온", "온도", "비", "눈", "맑", "흐림", "습도", "바람",
        "우산", "옷차림", "뭐 입", "뭐 입을", "어떻게 입",
    ]),
    (Intent.ALARM, [
        "알람", "깨워", "모닝콜", "기상",
    ]),
    (Intent.TIMER, [
        "타이머", "분 후", "분 뒤", "초 후", "초 뒤",
    ]),
    (Intent.REMINDER, [
        "리마인더", "알려줘", "알림", "잊지 않게", "잊지않게",
    ]),
    (Intent.CALENDAR, [
        "일정", "캘린더", "약속", "미팅", "회의", "예약", "스케줄",
        "추가해", "등록해", "잡아줘", "넣어줘",
    ]),
    (Intent.TODO, [
        "할일", "투두", "to-do", "목록에", "목록 추가", "장보기",
        "해야 할", "체크리스트",
    ]),
    (Intent.MEMO, [
        "메모", "기록", "노트", "적어", "저장해",
    ]),
    (Intent.FINANCE, [
        "환율", "달러", "유로", "엔화", "원", "환전", "주가", "주식",
        "코스피", "나스닥", "비트코인",
    ]),
    (Intent.TRANSLATE, [
        "번역", "영어로", "한국어로", "일본어로", "중국어로",
        "뭐라고", "어떻게 말해",
    ]),
    (Intent.COMMUNICATION, [
        "전화", "문자", "카톡", "메시지", "연락", "보내줘", "전송",
    ]),
    (Intent.MEDIA, [
        "음악", "노래", "틀어줘", "재생", "유튜브", "플레이리스트",
        "볼륨",
    ]),
    (Intent.NAVIGATION, [
        "길찾기", "가는 길", "얼마나 걸려", "지하철", "버스", "택시",
        "내비", "경로",
    ]),
    (Intent.SMART_HOME, [
        "불", "조명", "에어컨", "히터", "TV", "커튼", "스위치",
        "켜줘", "꺼줘", "온도 설정",
    ]),
    (Intent.SEARCH, [
        "검색해", "찾아봐", "알려줘", "뭐야", "누구야", "어디야",
        "언제야", "얼마야",
    ]),
    # Phase 12 패턴
    (Intent.TRAIN, [
        "ktx", "srt", "무궁화", "새마을", "열차", "기차",
        "승차권", "기차표", "열차표", "예매",
    ]),
    (Intent.SUBWAY, [
        "지하철 도착", "지하철 언제", "몇 분 후", "실시간 도착",
        "다음 열차", "막차", "첫차",
    ]),
    (Intent.SHOPPING, [
        "쿠팡", "올리브영", "다이소", "배달", "주문해줘",
        "쇼핑", "상품 검색", "가격 비교", "최저가", "중고",
        "번개장터", "중고나라",
    ]),
    (Intent.SPORTS, [
        "kbo", "야구", "k리그", "축구", "lck", "롤", "리그오브레전드",
        "경기 결과", "경기 일정", "스코어", "승패",
    ]),
    (Intent.STOCK, [
        "주가", "삼성전자", "카카오", "네이버 주식", "코스피",
        "코스닥", "상장", "시가총액", "종가",
    ]),
    (Intent.SPELLING, [
        "맞춤법", "틀린 글자", "교정", "문법 검사", "맞게 썼",
    ]),
    (Intent.POSTAL, [
        "우편번호", "zip", "주소 검색", "배송 주소",
    ]),
]


def classify_intent(text: str) -> RouterResult:
    """
    입력 텍스트에서 의도를 분류합니다.

    Args:
        text: 사용자 발화 텍스트

    Returns:
        RouterResult (의도, 신뢰도, LLM 필요 여부, 추출 데이터)
    """
    text_lower = text.lower()

    for intent, keywords in _PATTERNS:
        hits = [kw for kw in keywords if kw in text_lower]
        if hits:
            confidence = min(0.9, 0.6 + len(hits) * 0.1)
            extracted = _extract_data(intent, text)
            needs_llm = _needs_llm(intent, text, extracted)
            return RouterResult(
                intent=intent,
                confidence=confidence,
                needs_llm=needs_llm,
                extracted=extracted,
            )

    # 매칭 없으면 범용 처리 (LLM에 위임)
    return RouterResult(
        intent=Intent.GENERAL,
        confidence=0.5,
        needs_llm=True,
        extracted={},
    )


def _extract_data(intent: Intent, text: str) -> dict:
    """의도별 데이터 추출."""
    extracted: dict = {}

    if intent == Intent.WEATHER:
        cities = ["서울", "부산", "대구", "인천", "광주", "대전", "울산", "수원", "제주"]
        for c in cities:
            if c in text:
                extracted["city"] = c
                break

    elif intent in (Intent.TIMER, Intent.REMINDER):
        m = re.search(r"(\d+)\s*분", text)
        if m:
            extracted["minutes"] = int(m.group(1))
        m2 = re.search(r"(\d+)\s*초", text)
        if m2:
            extracted["seconds"] = int(m2.group(1))

    elif intent == Intent.ALARM:
        m = re.search(r"(\d{1,2})\s*시", text)
        if m:
            extracted["hour"] = int(m.group(1))
        m2 = re.search(r"(\d{1,2})\s*분", text)
        if m2:
            extracted["minute"] = int(m2.group(1))

    elif intent == Intent.FINANCE:
        ccy_map = {
            "달러": "USD", "유로": "EUR", "엔": "JPY",
            "위안": "CNY", "파운드": "GBP",
        }
        for word, code in ccy_map.items():
            if word in text:
                extracted["currency"] = code
                break
        m = re.search(r"(\d[\d,]*)\s*(달러|유로|엔|원)", text)
        if m:
            extracted["amount"] = float(m.group(1).replace(",", ""))

    elif intent == Intent.COMMUNICATION:
        m = re.search(r"(전화|문자|카톡)\s*(.{1,20}?)(?:에게|한테|에게|에)?(?:\s|$)", text)
        if m:
            extracted["action"] = m.group(1)
            extracted["contact"] = m.group(2).strip()

    elif intent == Intent.MEDIA:
        m = re.search(r"(?:틀어줘|재생|검색)?\s*(.{1,40}?)\s*(?:노래|음악|틀어줘|재생)", text)
        if m:
            extracted["query"] = m.group(1).strip()
        if "유튜브" in text:
            extracted["platform"] = "youtube"
            m2 = re.search(r"유튜브에서?\s*(.{1,40}?)\s*(?:검색|찾아|봐)", text)
            if m2:
                extracted["query"] = m2.group(1).strip()

    elif intent == Intent.NAVIGATION:
        m = re.search(r"(.{1,20}?)(?:에서|부터)\s*(.{1,20}?)(?:까지|로|으로|에)\s*(?:가는 길|길찾기|경로)", text)
        if m:
            extracted["origin"] = m.group(1).strip()
            extracted["destination"] = m.group(2).strip()
        else:
            m2 = re.search(r"(.{1,20}?)(?:까지|로|으로|에)\s*(?:가는 길|길찾기|경로|어떻게 가)", text)
            if m2:
                extracted["destination"] = m2.group(1).strip()

    # Phase 12 추출
    elif intent == Intent.TRAIN:
        m = re.search(r"(.{1,10}?)(?:에서|역에서|역)\s*(.{1,10}?)(?:까지|역까지|역)", text)
        if m:
            extracted["departure"] = m.group(1).strip()
            extracted["arrival"] = m.group(2).strip()
        if "srt" in text.lower():
            extracted["train_type"] = "SRT"
        elif "ktx" in text.lower():
            extracted["train_type"] = "KTX"
        m_date = re.search(r"(오늘|내일|모레|그제|어제)", text)
        if m_date:
            extracted["date"] = m_date.group(1)
        m_time = re.search(r"(\d{1,2})시", text)
        if m_time:
            extracted["time"] = f"{int(m_time.group(1)):02d}00"

    elif intent == Intent.SUBWAY:
        m = re.search(r"(.{1,15}?)역", text)
        if m:
            extracted["station"] = m.group(1).strip()
        m_line = re.search(r"(\d호선|[가-힣]+선)", text)
        if m_line:
            extracted["line"] = m_line.group(1)

    elif intent == Intent.SHOPPING:
        for platform in ["쿠팡", "올리브영", "다이소", "번개장터", "중고나라"]:
            if platform in text:
                extracted["platform"] = platform.lower()
                break
        m = re.search(r"(?:쿠팡|올리브영|다이소|쇼핑|검색|주문)?\s*(.{2,30}?)\s*(?:찾아줘|검색해|주문해|얼마야|가격)", text)
        if m:
            extracted["query"] = m.group(1).strip()
        m_price = re.search(r"(\d[\d,]*)\s*원\s*이하", text)
        if m_price:
            extracted["max_price"] = int(m_price.group(1).replace(",", ""))

    elif intent == Intent.SPORTS:
        for league in ["kbo", "야구", "k리그", "축구", "lck", "롤"]:
            if league in text.lower():
                extracted["league"] = {"kbo": "kbo", "야구": "kbo",
                                        "k리그": "kleague", "축구": "kleague",
                                        "lck": "lck", "롤": "lck"}.get(league, "kbo")
                break
        m_date = re.search(r"(오늘|어제|내일)", text)
        if m_date:
            extracted["date"] = m_date.group(1)

    elif intent == Intent.STOCK:
        m = re.search(r"(.{2,15}?)\s*(?:주가|주식|종가|현재가)", text)
        if m:
            extracted["company"] = m.group(1).strip()

    elif intent == Intent.SPELLING:
        # 교정할 텍스트 추출 (따옴표나 큰따옴표 안)
        m = re.search(r"[\"\'\"\'](.*?)[\"\'\"\']", text)
        if m:
            extracted["text"] = m.group(1)

    elif intent == Intent.POSTAL:
        m = re.search(r"(?:우편번호|주소)\s*[:\s]?\s*(.{5,50}?)(?:\s*우편번호|\s*zip|$)", text)
        if m:
            extracted["address"] = m.group(1).strip()

    return extracted


def _needs_llm(intent: Intent, text: str, extracted: dict) -> bool:
    """LLM 호출이 필요한지 판단합니다."""
    # 타이머/알람 + 명확한 시간 → LLM 불필요
    if intent == Intent.TIMER and extracted.get("minutes"):
        return False
    if intent == Intent.ALARM and extracted.get("hour") is not None:
        return False
    # 환율 + 명확한 통화 → LLM 불필요
    if intent == Intent.FINANCE and extracted.get("currency"):
        return False
    # Phase 12: 구조화된 데이터가 충분하면 LLM 불필요
    if intent == Intent.TRAIN and extracted.get("departure") and extracted.get("arrival"):
        return False
    if intent == Intent.SUBWAY and extracted.get("station"):
        return False
    if intent == Intent.SPORTS and extracted.get("league"):
        return False
    if intent == Intent.STOCK and extracted.get("company"):
        return False
    if intent == Intent.SPELLING and extracted.get("text"):
        return False
    if intent == Intent.POSTAL and extracted.get("address"):
        return False
    return True

"""
루이스 개인비서 - Agent + Tool Calling 프로토타입
Windows PC에서 음성으로 전체 비서 기능을 검증합니다.

실행 전 설치:
    pip install langchain langchain-anthropic langgraph pydantic
    pip install pvporcupine pvrecorder SpeechRecognition pyttsx3
    pip install requests python-dotenv google-auth google-auth-oauthlib
    pip install google-api-python-client apscheduler sqlalchemy dateparser

.env 파일 필요:
    ANTHROPIC_API_KEY=sk-ant-xxxxx
    PICOVOICE_ACCESS_KEY=xxxxx
    OPENWEATHER_API_KEY=xxxxx
    GOOGLE_CLIENT_SECRET_FILE=credentials.json   (선택)

실행:
    python louis_prototype.py
"""

import json
import logging
import os
import sqlite3
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

import requests
from dotenv import load_dotenv

from langchain_core.tools import tool
from langchain_core.messages import HumanMessage
from langchain_anthropic import ChatAnthropic
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver

from apscheduler.schedulers.background import BackgroundScheduler

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("Louis")


# ─────────────────────────────────────────────────────────
# 1. 로컬 DB (SQLite)
# ─────────────────────────────────────────────────────────

class LocalDB:
    def __init__(self, path: str = "louis_proto.db"):
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self._init()

    def _init(self):
        c = self.conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS todos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                done INTEGER DEFAULT 0,
                created_at TEXT NOT NULL
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS memos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                trigger_at TEXT NOT NULL,
                fired INTEGER DEFAULT 0
            )
        """)
        self.conn.commit()

    def add_todo(self, content: str) -> int:
        c = self.conn.cursor()
        c.execute("INSERT INTO todos (content, created_at) VALUES (?,?)",
                  (content, datetime.now().isoformat()))
        self.conn.commit()
        return c.lastrowid

    def list_todos(self) -> List[Dict]:
        c = self.conn.cursor()
        rows = c.execute(
            "SELECT id, content, done FROM todos WHERE done=0 ORDER BY id DESC"
        ).fetchall()
        return [{"id": r[0], "content": r[1], "done": bool(r[2])} for r in rows]

    def done_todo(self, todo_id: int):
        self.conn.execute("UPDATE todos SET done=1 WHERE id=?", (todo_id,))
        self.conn.commit()

    def add_memo(self, content: str) -> int:
        c = self.conn.cursor()
        c.execute("INSERT INTO memos (content, created_at) VALUES (?,?)",
                  (content, datetime.now().isoformat()))
        self.conn.commit()
        return c.lastrowid

    def list_memos(self, limit: int = 10) -> List[Dict]:
        c = self.conn.cursor()
        rows = c.execute(
            "SELECT id, content, created_at FROM memos ORDER BY id DESC LIMIT ?",
            (limit,)
        ).fetchall()
        return [{"id": r[0], "content": r[1], "at": r[2]} for r in rows]

    def add_reminder(self, content: str, trigger_at: datetime) -> int:
        c = self.conn.cursor()
        c.execute("INSERT INTO reminders (content, trigger_at) VALUES (?,?)",
                  (content, trigger_at.isoformat()))
        self.conn.commit()
        return c.lastrowid


DB = LocalDB()

# ─────────────────────────────────────────────────────────
# 2. 스케줄러 (리마인더)
# ─────────────────────────────────────────────────────────

scheduler = BackgroundScheduler(timezone="Asia/Seoul")
scheduler.start()


def _notify(content: str):
    """리마인더 알림. Windows에서는 MessageBox, 다른 환경에서는 프린트."""
    log.info(f"[리마인더 알림] {content}")
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, content, "루이스 리마인더", 0x40)
    except Exception:
        print(f"\n{'='*40}\n[루이스 리마인더] {content}\n{'='*40}\n")


# ─────────────────────────────────────────────────────────
# 3. Tools
# ─────────────────────────────────────────────────────────

CITY_MAP = {
    "서울": "Seoul", "부산": "Busan", "대구": "Daegu",
    "인천": "Incheon", "광주": "Gwangju", "대전": "Daejeon",
    "제주": "Jeju", "수원": "Suwon",
}


@tool
def get_weather(city: str = "Seoul") -> str:
    """현재 날씨와 오늘 최고/최저 기온을 조회합니다."""
    key = os.getenv("OPENWEATHER_API_KEY", "")
    if not key:
        return json.dumps({"error": "OPENWEATHER_API_KEY가 없어요."}, ensure_ascii=False)

    city_en = CITY_MAP.get(city, city)
    try:
        cur = requests.get(
            "https://api.openweathermap.org/data/2.5/weather",
            params={"q": city_en, "appid": key, "units": "metric", "lang": "kr"},
            timeout=5,
        ).json()
        if cur.get("cod") != 200:
            return json.dumps({"error": f"도시를 찾을 수 없어요: {city}"}, ensure_ascii=False)

        fcast = requests.get(
            "https://api.openweathermap.org/data/2.5/forecast",
            params={"q": city_en, "appid": key, "units": "metric"},
            timeout=5,
        ).json()
        today = datetime.now().date()
        temps = [
            x["main"]["temp"] for x in fcast.get("list", [])
            if datetime.fromtimestamp(x["dt"]).date() == today
        ] or [cur["main"]["temp"]]

        return json.dumps({
            "city": cur["name"],
            "temp_now": round(cur["main"]["temp"], 1),
            "temp_max": round(max(temps), 1),
            "temp_min": round(min(temps), 1),
            "condition": cur["weather"][0]["description"],
            "wind_speed": cur["wind"]["speed"],
            "humidity": cur["main"]["humidity"],
        }, ensure_ascii=False)
    except Exception as exc:
        return json.dumps({"error": f"날씨 조회 실패: {exc}"}, ensure_ascii=False)


@tool
def recommend_outfit(weather_json: str) -> str:
    """날씨 JSON을 받아 오늘 옷차림을 추천합니다."""
    try:
        w = json.loads(weather_json)
    except Exception:
        return "날씨 정보를 파싱할 수 없어요."
    if "error" in w:
        return "날씨 정보를 가져오지 못해 옷차림을 추천하기 어려워요."

    t = w["temp_max"]
    diff = w["temp_max"] - w["temp_min"]
    cond = w.get("condition", "")
    wind = w.get("wind_speed", 0)

    if t >= 28: top = "반팔이나 민소매"
    elif t >= 23: top = "반팔"
    elif t >= 20: top = "긴팔 티셔츠나 얇은 셔츠"
    elif t >= 17: top = "얇은 가디건이나 맨투맨"
    elif t >= 12: top = "자켓이나 후드티"
    elif t >= 9: top = "트렌치코트나 야상"
    elif t >= 5: top = "코트"
    else: top = "두꺼운 패딩"

    extras = []
    if diff >= 10 and t >= 15:
        extras.append("일교차가 크니 겉옷을 챙기세요")
    if wind >= 5:
        extras.append("바람이 강하니 방풍 외투가 좋아요")
    if "비" in cond:
        extras.append("우산 챙기세요")

    result = f"{top} 추천드려요."
    if extras:
        result += " " + " ".join(extras) + "."
    return result


@tool
def set_reminder(content: str, minutes_later: int) -> str:
    """n분 뒤 알림을 등록합니다."""
    try:
        trigger = datetime.now() + timedelta(minutes=minutes_later)
        scheduler.add_job(_notify, "date", run_date=trigger, args=[content])
        DB.add_reminder(content, trigger)
        return f"{minutes_later}분 뒤 '{content}' 알려드릴게요."
    except Exception as exc:
        return f"리마인더 등록 실패: {exc}"


@tool
def add_todo(content: str) -> str:
    """할일 목록에 항목을 추가합니다."""
    tid = DB.add_todo(content)
    return f"할일 추가 완료 (#{tid}): {content}"


@tool
def list_todos() -> str:
    """미완료 할일 목록을 조회합니다."""
    items = DB.list_todos()
    if not items:
        return "진행 중인 할일이 없어요."
    return "\n".join([f"#{i['id']} {i['content']}" for i in items])


@tool
def complete_todo(todo_id: int) -> str:
    """할일을 완료 처리합니다."""
    DB.done_todo(todo_id)
    return f"#{todo_id} 완료 처리했어요."


@tool
def add_memo(content: str) -> str:
    """메모를 저장합니다."""
    mid = DB.add_memo(content)
    return f"메모 저장 완료 (#{mid})"


@tool
def convert_currency(amount: float, from_ccy: str, to_ccy: str = "KRW") -> str:
    """환율을 변환합니다."""
    ccy_map = {
        "달러": "USD", "유로": "EUR", "엔": "JPY",
        "위안": "CNY", "파운드": "GBP",
    }
    from_code = ccy_map.get(from_ccy, from_ccy.upper())
    to_code = ccy_map.get(to_ccy, to_ccy.upper())
    try:
        r = requests.get(
            f"https://open.er-api.com/v6/latest/{from_code}", timeout=5
        ).json()
        rate = r["rates"].get(to_code)
        if not rate:
            return f"{to_ccy} 환율을 찾을 수 없어요."
        converted = amount * rate
        return f"{amount:,.0f} {from_code} = {converted:,.0f} {to_code}"
    except Exception as exc:
        return f"환율 조회 실패: {exc}"


@tool
def web_search(query: str) -> str:
    """웹에서 정보를 검색합니다. (Serper API 키 필요)"""
    key = os.getenv("SERPER_API_KEY", "")
    if not key:
        return f"[검색 미리보기] '{query}' - Serper API 키를 설정하면 실제 검색이 가능해요."
    try:
        r = requests.post(
            "https://google.serper.dev/search",
            headers={"X-API-KEY": key, "Content-Type": "application/json"},
            json={"q": query, "hl": "ko", "gl": "kr"},
            timeout=5,
        )
        data = r.json()
        snippets = [
            item.get("snippet", "")
            for item in data.get("organic", [])[:3]
            if item.get("snippet")
        ]
        return "\n".join(snippets) if snippets else "검색 결과를 찾지 못했어요."
    except Exception as exc:
        return f"웹 검색 실패: {exc}"


# ─────────────────────────────────────────────────────────
# 4. Agent 빌드
# ─────────────────────────────────────────────────────────

SYSTEM_PROMPT = f"""당신은 '루이스'라는 이름의 한국어 개인 비서입니다.

원칙:
- 사용자 요청에 맞는 도구(tool)를 선택해 실행합니다.
- 날짜/시간이 모호하면 현재 시각({datetime.now().strftime('%Y-%m-%d %H:%M')}) 기준으로 해석합니다.
- 날씨+옷차림 요청 시: get_weather 먼저, 그 결과로 recommend_outfit 순차 호출.
- 응답은 음성으로 읽히므로 2~3문장 이내로 간결하게.
- 이모지는 사용하지 않습니다.
"""


def build_agent():
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY가 설정되지 않았어요. .env 파일을 확인해주세요.")

    tools = [
        get_weather, recommend_outfit,
        set_reminder,
        add_todo, list_todos, complete_todo,
        add_memo,
        convert_currency, web_search,
    ]

    llm = ChatAnthropic(
        model="claude-haiku-4-5-20251001",
        api_key=api_key,
        temperature=0.2,
        max_tokens=500,
    )

    memory = MemorySaver()
    return create_react_agent(
        llm, tools,
        prompt=SYSTEM_PROMPT,
        checkpointer=memory,
    )


# ─────────────────────────────────────────────────────────
# 5. 음성 입출력 (Windows)
# ─────────────────────────────────────────────────────────

class Voice:
    def __init__(self):
        try:
            import pyttsx3
            self.tts = pyttsx3.init()
            self.tts.setProperty("rate", 175)
            for v in self.tts.getProperty("voices"):
                if "korean" in v.name.lower() or "heami" in v.name.lower():
                    self.tts.setProperty("voice", v.id)
                    break
            self._tts_ok = True
        except Exception as exc:
            log.warning(f"TTS 초기화 실패 (텍스트 출력 사용): {exc}")
            self._tts_ok = False

        try:
            import speech_recognition as sr
            self.rec = sr.Recognizer()
            self.rec.pause_threshold = 1.0
            self._stt_ok = True
        except Exception as exc:
            log.warning(f"STT 초기화 실패: {exc}")
            self._stt_ok = False

    def speak(self, text: str):
        print(f"\n[루이스] {text}\n")
        if self._tts_ok:
            try:
                self.tts.say(text)
                self.tts.runAndWait()
            except Exception:
                pass  # TTS 실패해도 계속

    def listen(self, timeout: int = 5, phrase_limit: int = 10) -> Optional[str]:
        if not self._stt_ok:
            return input("[사용자 입력] ").strip() or None

        try:
            import speech_recognition as sr
            with sr.Microphone() as src:
                self.rec.adjust_for_ambient_noise(src, duration=0.4)
                print("[루이스 듣는 중...]")
                audio = self.rec.listen(src, timeout=timeout, phrase_time_limit=phrase_limit)
            text = self.rec.recognize_google(audio, language="ko-KR")
            print(f"[사용자] {text}")
            return text
        except Exception:
            return None


# ─────────────────────────────────────────────────────────
# 6. 웨이크워드 + 메인 루프
# ─────────────────────────────────────────────────────────

class Louis:
    def __init__(self, use_wake_word: bool = True):
        self.voice = Voice()
        self.agent = build_agent()
        self.session_id = "prototype-session"
        self.use_wake_word = use_wake_word

        if use_wake_word:
            self._init_wake_word()

    def _init_wake_word(self):
        try:
            import pvporcupine
            from pvrecorder import PvRecorder

            key = os.getenv("PICOVOICE_ACCESS_KEY", "")
            if not key:
                log.warning("PICOVOICE_ACCESS_KEY 없음. 웨이크워드 비활성화.")
                self.use_wake_word = False
                return

            # 실제 배포: keyword_paths=["./assets/wake_words/louis_ko.ppn"]
            # 프로토타입: 영어 'computer' 키워드로 테스트
            self.porcupine = pvporcupine.create(
                access_key=key,
                keywords=["computer"],  # 테스트용. 실제는 'louis_ko.ppn' 사용
            )
            self.recorder = PvRecorder(
                frame_length=self.porcupine.frame_length,
                device_index=-1,
            )
            log.info("웨이크워드 초기화 완료 (테스트 키워드: 'computer')")
            log.info("실제 배포 시 'louis_ko.ppn' 커스텀 모델로 교체하세요.")
        except Exception as exc:
            log.warning(f"웨이크워드 초기화 실패: {exc}. Enter 키로 대체합니다.")
            self.use_wake_word = False

    def ask_agent(self, user_text: str) -> str:
        try:
            result = self.agent.invoke(
                {"messages": [HumanMessage(content=user_text)]},
                config={"configurable": {"thread_id": self.session_id}},
            )
            msgs = result.get("messages", [])
            last = msgs[-1].content if msgs else "처리 중 오류가 발생했어요."
            if isinstance(last, list):
                last = " ".join(b.get("text", "") for b in last if isinstance(b, dict))
            return str(last)
        except Exception as exc:
            log.error(f"Agent 오류: {exc}", exc_info=True)
            return "처리 중 오류가 발생했어요."

    def conversation_loop(self):
        self.voice.speak("네, 말씀하세요.")
        idle = 0
        while idle < 2:
            user = self.voice.listen()
            if not user:
                idle += 1
                if idle < 2:
                    self.voice.speak("잘 못 들었어요. 다시 말씀해주세요.")
                continue

            if any(k in user for k in ["그만", "종료", "됐어", "안녕히", "잘게"]):
                self.voice.speak("알겠어요. 필요하시면 불러주세요.")
                return

            reply = self.ask_agent(user)
            self.voice.speak(reply)
            idle = 0

    def run(self):
        """메인 루프 실행."""
        log.info("루이스 프로토타입 시작")
        self.voice.speak("루이스 준비됐어요.")

        if self.use_wake_word and hasattr(self, "recorder"):
            # 웨이크워드 모드
            self.recorder.start()
            log.info("웨이크워드 대기 중... ('computer'라고 말하면 활성화)")
            try:
                while True:
                    pcm = self.recorder.read()
                    if self.porcupine.process(pcm) >= 0:
                        log.info("웨이크워드 감지!")
                        self.recorder.stop()
                        self.conversation_loop()
                        self.recorder.start()
            except KeyboardInterrupt:
                log.info("종료")
            finally:
                self.recorder.delete()
                self.porcupine.delete()
        else:
            # 텍스트 입력 모드 (웨이크워드 없을 때)
            print("\n" + "="*50)
            print("루이스 텍스트 모드")
            print("Enter를 눌러 대화를 시작하세요. (Ctrl+C로 종료)")
            print("="*50 + "\n")
            try:
                while True:
                    input("▶ Enter를 눌러 대화 시작...")
                    self.conversation_loop()
            except KeyboardInterrupt:
                log.info("종료")
        scheduler.shutdown()


# ─────────────────────────────────────────────────────────
# 7. 실행
# ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    # 빠른 텍스트 테스트 모드: python louis_prototype.py --text
    use_wake = "--text" not in sys.argv

    try:
        louis = Louis(use_wake_word=use_wake)
        louis.run()
    except RuntimeError as e:
        print(f"\n오류: {e}")
        print("\n.env 파일을 확인하고 필요한 API 키를 설정해주세요.")
        sys.exit(1)

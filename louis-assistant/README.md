# 루이스(Louis) 개인비서

스마트폰에서 "루이스"라는 웨이크워드로 호출하는 AI 개인비서 앱.

- **백엔드**: Python 3.11 + FastAPI + LangGraph
- **모바일**: Flutter (Android 우선, iOS 차후)
- **AI**: Claude Haiku 4.5 (기본) / Claude Sonnet 4.6 (복잡 작업)

## 빠른 시작

### 1. API 키 발급 (필수)

| API | 발급처 | 용도 |
|-----|--------|------|
| Anthropic Claude | https://console.anthropic.com | LLM 두뇌 |
| Picovoice | https://console.picovoice.ai | 웨이크워드 |
| OpenWeatherMap | https://openweathermap.org/api | 날씨 |
| Google Cloud | https://console.cloud.google.com | 캘린더, Gmail |

### 2. 백엔드 실행

```bash
cd backend

# 패키지 설치
pip install -r requirements.txt

# 환경변수 설정
cp .env.example .env
# .env 파일에 발급받은 API 키 입력

# 서버 실행
python -m app.main
# → http://localhost:8000/docs 에서 Swagger UI 확인
```

### 3. 프로토타입 테스트 (Windows)

```bash
# 추가 패키지 설치
pip install pvporcupine pvrecorder SpeechRecognition pyttsx3

# 텍스트 모드로 실행 (마이크/스피커 없어도 테스트 가능)
python louis_prototype.py --text

# 음성 모드로 실행
python louis_prototype.py
```

### 4. 테스트 실행

```bash
cd backend
pytest tests/ -v
```

## 주요 기능

| 기능 | 예시 발화 | 사용 API |
|------|----------|---------|
| 날씨 조회 | "오늘 날씨 어때?" | OpenWeatherMap |
| 옷차림 추천 | "오늘 뭐 입을까?" | 규칙 기반 |
| 일정 추가 | "내일 3시 치과 예약 추가해줘" | Google Calendar |
| 리마인더 | "30분 뒤 빨래 알려줘" | APScheduler |
| 할일 관리 | "장보기 목록에 우유 추가" | SQLite |
| 메모 | "아이디어 메모해줘" | SQLite |
| 환율 변환 | "100달러 얼마야?" | open.er-api.com |
| 번역 | "안녕을 영어로 뭐야?" | DeepL |
| 웹 검색 | "최신 뉴스 알려줘" | Serper.dev |

## 프로젝트 구조

```
louis-assistant/
├── backend/                  # FastAPI 서버
│   ├── app/
│   │   ├── main.py           # 엔트리 포인트
│   │   ├── config.py         # 환경변수
│   │   ├── agent/
│   │   │   ├── orchestrator.py  # LangGraph Agent
│   │   │   ├── prompts.py       # 시스템 프롬프트
│   │   │   ├── router.py        # 의도 분류
│   │   │   └── tools/           # 각 기능별 도구
│   │   ├── api/              # FastAPI 라우터
│   │   ├── db/               # SQLAlchemy 모델
│   │   └── services/         # Google OAuth, 캐시
│   └── tests/
├── mobile/                   # Flutter 앱
│   └── lib/
│       ├── core/services/    # 음성 파이프라인
│       └── features/         # 화면별 기능
├── docs/                     # 문서
│   ├── architecture.md
│   ├── prompts.md
│   └── api.md
└── louis_prototype.py        # Windows 프로토타입
```

## 개발 로드맵

- **Phase 1** (Week 1-2): Agent 핵심 로직 ← *현재*
- **Phase 2** (Week 3-4): FastAPI 백엔드 + Cloud Run 배포
- **Phase 3** (Week 5-8): Flutter 모바일 앱
- **Phase 4** (Week 9-10): 고급 기능 (위치 기반, 스마트홈)
- **Phase 5** (Week 11-12): Play Store / App Store 출시

## 비용 예상

1일 50회 대화 기준 (Claude Haiku):
- 약 $0.5~1 / 월 / 사용자
- 유료 플랜 ₩4,900/월 설정 시 건전한 마진

## 보안

- API 키는 백엔드에만 존재 (앱에 하드코딩 금지)
- 앱 ↔ 백엔드: JWT 인증 + HTTPS
- 웨이크워드는 온디바이스 처리 (서버 전송 없음)
- 음성 데이터 30일 후 자동 삭제

## 라이선스

MIT License

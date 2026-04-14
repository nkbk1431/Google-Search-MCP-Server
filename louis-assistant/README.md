# 루이스(Louis) 개인비서

스마트폰에서 "루이스"라는 웨이크워드로 호출하는 AI 개인비서 앱.

- **백엔드**: Python 3.12.13 + FastAPI + LangGraph (Cloud Run 배포)
- **모바일**: Flutter (Android 우선, iOS 차후)
- **AI**: Claude Haiku 4.5 (기본) / Claude Sonnet 4.6 (복잡 작업)
- **현재**: Phase 15 완료 — 프로덕션 배포 준비 완료

> Python 버전: **3.12.13** 사용

---

## 빠른 시작

### Windows (PowerShell + venv)

Python 3.12.13이 설치돼 있어야 합니다. [python.org](https://www.python.org/downloads/) 에서 설치 시 **"Add Python to PATH"** 반드시 체크.

```powershell
# 1. 저장소 클론
git clone https://github.com/LOUIS-1993-AI-Studio/LOUIS_APP.git
cd LOUIS_APP

# 2. 가상환경 생성 및 활성화
python -m venv .venv
.venv\Scripts\activate

# 3. 의존성 설치
pip install -r backend\requirements.txt

# 4. 백엔드 실행 (.env 자동 생성 + 방화벽 설정 + IP 안내 포함)
cd backend
.\quick_start.ps1
# → http://localhost:8000/docs 에서 Swagger UI 확인
```

> 자세한 Windows 가이드: [`docs/windows_setup.md`](docs/windows_setup.md)

### Linux (Ubuntu / bash)

```bash
# 1. 저장소 클론
git clone https://github.com/LOUIS-1993-AI-Studio/LOUIS_APP.git
cd LOUIS_APP

# 2. 가상환경 생성 및 활성화
python3 -m venv .venv
source .venv/bin/activate

# 3. 백엔드 실행 (의존성 자동 설치 + IP 안내 포함)
cd backend
bash quick_start.sh
# → 스마트폰 접속 URL이 출력됩니다
```

### Linux Conda 환경 (선택)

```bash
# 프로젝트 루트에서
conda env create -f environment.yml
conda activate louis
```

---

| API | 발급처 | 필수 여부 |
|-----|--------|----------|
| Anthropic Claude | https://console.anthropic.com | **필수** |
| Google Cloud (OAuth) | https://console.cloud.google.com | **필수** (캘린더·Gmail) |
| OpenWeatherMap | https://openweathermap.org/api | 권장 |
| Serper.dev | https://serper.dev | 권장 (웹 검색) |
| DeepL | https://www.deepl.com/pro-api | 선택 |
| Naver Developers | https://developers.naver.com | 선택 (쇼핑 검색) |
| Kakao Developers | https://developers.kakao.com | 선택 (주소 검색) |
| 서울 열린데이터광장 | https://data.seoul.go.kr | 선택 (지하철) |

### API 키 발급

### 3. Google Calendar / Gmail 연동

Cloud Run 같은 headless 환경에서도 동작하는 웹 OAuth 플로우:

```bash
# 1. Google Cloud Console에서 OAuth 클라이언트 ID 발급
#    → backend/credentials.json 으로 저장

# 2. 서버 실행 후 인증 시작
curl -H "Authorization: Bearer <JWT>" \
  http://localhost:8000/api/v1/auth/google/init

# 3. 반환된 auth_url을 브라우저에서 열어 Google 로그인
# 4. 자동으로 콜백 처리 → tokens/ 에 토큰 저장
```

### 스마트폰 테스트 (APK 빌드)

**Windows:**
```powershell
cd mobile
.\build_test_apk.ps1 192.168.0.10   # 백엔드 PC IP 입력
```

**Linux:**
```bash
cd mobile
bash build_test_apk.sh 192.168.0.10
```

### 테스트 실행

**Windows:**
```powershell
.venv\Scripts\activate
cd backend
pytest tests/ -v --tb=short
```

**Linux:**
```bash
source .venv/bin/activate
cd backend
pytest tests/ -v --tb=short
```

### deploy.sh 스크립트 (Linux / Cloud 배포)

```bash
./deploy.sh dev      # 로컬 uvicorn
./deploy.sh docker   # Docker Compose
./deploy.sh test     # pytest
./deploy.sh gcloud   # Google Cloud Run 배포
./deploy.sh secrets  # Secret Manager에 API 키 등록
```

## 주요 기능

### 날씨 & 옷차림 추천

날씨를 물어보면 현재 기온, 최고/최저 기온, 날씨 상태와 함께 **기온 구간에 맞는 코디 조합**을 바로 알려줍니다.

| 예시 발화 | 응답 예시 |
|----------|----------|
| "오늘 날씨 어때?" | "서울 현재 16°C, 최고 18°C / 최저 9°C예요. 반팔에 자켓이나 바람막이 같은 아우터를 입으세요. 아침저녁이 많이 쌀쌀하니 겉옷을 꼭 챙기세요." |
| "오늘 뭐 입을까?" | 동일하게 날씨 조회 후 코디 추천 |
| "부산 날씨 알려줘" | 해당 도시 날씨 + 옷차림 |

**기온 구간별 코디 추천표:**

| 최고 기온 | 추천 코디 |
|-----------|----------|
| 28°C 이상 | 반팔/민소매 + 얇은 면 하의 |
| 23~27°C | 반팔 |
| 20~22°C | 반팔 + 얇은 가디건이나 셔츠 |
| 13~19°C | 반팔 + 자켓이나 바람막이 같은 아우터 |
| 9~12°C | 긴팔 + 두꺼운 자켓이나 야상 |
| 5~8°C | 니트/후드티 + 트렌치코트나 코트 |
| 0~4°C | 두꺼운 니트 + 패딩이나 두꺼운 코트 |
| 0°C 미만 | 두꺼운 패딩 + 목도리와 장갑 필수 |

추가로 아래 조건이 감지되면 자동으로 부가 안내를 드립니다:
- 아침 10°C 이하 + 낮 20°C 이상 → "아침저녁이 쌀쌀하니 겉옷을 꼭 챙기세요"
- 일교차 10도 이상 → "레이어링을 추천드려요"
- 바람 7m/s 이상 → "방풍 기능이 있는 외투 추천"
- 비 → "우산을 꼭 챙기세요"
- 눈 → "미끄럼 조심, 방수 신발 추천"

### 기본 기능 (Phase 1~11)

| 기능 | 예시 발화 |
|------|----------|
| 날씨 조회 | "오늘 날씨 어때?" |
| 옷차림 추천 | "오늘 뭐 입을까?" |
| 일정 추가 | "내일 3시 치과 예약 추가해줘" |
| 리마인더 | "30분 뒤 빨래 알려줘" |
| 할일 관리 | "장보기 목록에 우유 추가" |
| 메모 | "아이디어 메모해줘" |
| 환율 변환 | "100달러 얼마야?" |
| 번역 | "안녕을 영어로 뭐야?" |
| 웹 검색 | "최신 뉴스 알려줘" |
| 스마트홈 | "거실 불 꺼줘" |
| 음악 재생 | "좋아하는 노래 틀어줘" |

### 한국 특화 기능 (Phase 12)

| 기능 | 예시 발화 |
|------|----------|
| SRT 열차 조회 | "서울-부산 SRT 내일 오전 표 있어?" |
| KTX 열차 조회 | "KTX 대전 가는 거 알아봐줘" |
| 서울 지하철 실시간 | "강남역 2호선 다음 열차 언제야?" |
| 네이버 쇼핑 검색 | "에어팟 최저가 찾아줘" |
| 중고 마켓 | "아이패드 중고 번개장터에서 찾아줘" |
| KBO 야구 경기 | "오늘 두산 경기 결과 어때?" |
| K리그 축구 | "전북 어제 경기 몇 대 몇이야?" |
| LCK e스포츠 | "오늘 LCK 경기 있어?" |
| 맞춤법 검사 | "이 문장 맞춤법 틀린 거 있어?" |
| 주가 조회 | "삼성전자 주가 얼마야?" |
| 코스피/코스닥 | "오늘 코스피 어때?" |
| 우편번호 검색 | "강남구 테헤란로 152 우편번호 알려줘" |

## 프로젝트 구조

```
louis-assistant/
├── backend/                        # FastAPI 서버 (Cloud Run 배포)
│   ├── app/
│   │   ├── main.py                 # 엔트리 포인트
│   │   ├── config.py               # 환경변수 (pydantic-settings)
│   │   ├── agent/
│   │   │   ├── orchestrator.py     # LangGraph ReAct Agent
│   │   │   ├── prompts.py          # 시스템 프롬프트
│   │   │   ├── router.py           # 의도 분류 (22개 Intent)
│   │   │   └── tools/              # 기능별 도구 (18개 파일)
│   │   │       ├── weather.py      # 날씨
│   │   │       ├── calendar.py     # Google Calendar
│   │   │       ├── transport.py    # SRT/KTX/지하철
│   │   │       ├── shopping.py     # 쇼핑/중고마켓
│   │   │       ├── sports.py       # KBO/K리그/LCK
│   │   │       ├── korean_utils.py # 맞춤법/주가/우편번호
│   │   │       └── ...
│   │   ├── api/
│   │   │   ├── auth.py             # JWT 인증
│   │   │   ├── chat.py             # 채팅 API
│   │   │   ├── google_oauth.py     # Google OAuth 웹 플로우
│   │   │   └── webhook.py          # FCM 웹훅
│   │   ├── db/                     # SQLAlchemy 모델
│   │   └── services/               # 개인화, 캐시, TTS, FCM
│   ├── tests/                      # pytest (80+ 테스트)
│   ├── Dockerfile                  # Python 3.13-slim, 비루트 실행
│   └── requirements.txt
├── mobile/                         # Flutter 앱 (Android)
│   ├── lib/
│   │   ├── core/services/
│   │   │   ├── platform_channel.dart  # 네이티브 브리지
│   │   │   └── voice_pipeline.dart    # 음성 파이프라인
│   │   └── features/               # 화면별 기능
│   └── android/
├── docs/
│   ├── architecture.md             # 전체 아키텍처 문서
│   ├── api.md                      # API 레퍼런스
│   └── prompts.md                  # 프롬프트 설계
├── cloudbuild.yaml                 # Google Cloud Build CI/CD
├── deploy.sh                       # 배포 헬퍼 스크립트
└── docker-compose.yml              # 로컬 Docker 실행
```

## 개발 현황

| Phase | 내용 | 상태 |
|-------|------|------|
| Phase 1~3 | Agent 핵심, FastAPI 백엔드, Flutter 기반 | ✅ 완료 |
| Phase 4~6 | Google 연동, 스마트홈, 미디어 | ✅ 완료 |
| Phase 7~9 | 개인화, 비용 관리, FCM 푸시 | ✅ 완료 |
| Phase 10~11 | 테스트 완성, CI/CD, 아키텍처 문서 | ✅ 완료 |
| Phase 12 | 한국 특화 도구 12종 | ✅ 완료 |
| Phase 13 | Flutter 빌드 준비 (url_launcher, 권한) | ✅ 완료 |
| Phase 14 | Google OAuth 웹 플로우 (headless) | ✅ 완료 |
| Phase 15 | Cloud Run 프로덕션 배포 | ✅ 완료 |

## 기술 스택

| 영역 | 기술 |
|------|------|
| AI | Claude Haiku 4.5 / Sonnet 4.6 (Anthropic) |
| Agent 프레임워크 | LangGraph ReAct + MemorySaver |
| 백엔드 | Python 3.13.12 + FastAPI + SQLAlchemy + APScheduler |
| 인증 | JWT (HS256) + Google OAuth 2.0 |
| 개발 환경 | Python 3.12.13 + venv (Windows) / venv or Conda (Linux) |
| 캐시 | Redis (선택) / 인메모리 폴백 |
| 배포 | Google Cloud Run (서울 asia-northeast3) |
| CI/CD | GitHub Actions + Cloud Build |
| 모바일 | Flutter + Riverpod + MethodChannel |
| 주식 데이터 | pykrx (KRX 무료, API 키 불필요) |

## OS별 개발 환경 차이

| 항목 | Windows | Linux (Ubuntu) |
|------|---------|---------------|
| 환경 관리 | `conda activate louis` | `conda activate louis` |
| 백엔드 시작 | `.\quick_start.ps1` | `bash quick_start.sh` |
| APK 빌드 | `.\build_test_apk.ps1 IP` | `bash build_test_apk.sh IP` |
| 방화벽 | PowerShell 스크립트 자동 설정 | `sudo ufw allow 8000` |
| 상세 가이드 | [`docs/windows_setup.md`](docs/windows_setup.md) | `test_on_phone.sh` 참고 |

## 보안

- API 키는 백엔드 Secret Manager에만 존재 (앱 하드코딩 금지)
- 앱 ↔ 백엔드: JWT 인증 + HTTPS
- 웨이크워드 온디바이스 처리 (음성 서버 전송 없음)
- Cloud Run 비루트 사용자 실행
- 프로덕션 환경에서 Swagger UI 비활성화

## 비용 예상

1일 50회 대화 기준 (Claude Haiku 4.5):
- 약 $0.5~1 / 월 / 사용자
- Cloud Run 최소 인스턴스 0 설정 시 유휴 비용 없음

## 라이선스

MIT License

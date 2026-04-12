# 루이스(Louis) 개인비서 - 시스템 아키텍처

## 전체 흐름

```
[사용자 음성]
     ↓
[웨이크워드 감지 "루이스"] ── Picovoice Porcupine (온디바이스)
     ↓
[STT 음성→텍스트] ──────── 안드로이드 SpeechRecognizer (무료)
     ↓
[Flutter 앱] ─────────── /api/v1/chat POST
     ↓
[FastAPI 백엔드]
     ↓
[Intent Router] ────────── 키워드 기반 1차 분류 (LLM 호출 없이)
     ├── 타이머/알람 → 직접 처리 (LLM 불필요)
     └── 나머지 → LangGraph Agent
     ↓
[LangGraph ReAct Agent]
     ├── Claude Haiku 4.5  (기본, 저비용)
     └── Claude Sonnet 4.6 (복잡 작업, 필요시)
     ↓
[Tool 실행]
     ├── get_weather          → OpenWeatherMap API
     ├── recommend_outfit     → 규칙 기반
     ├── add_calendar_event   → Google Calendar API
     ├── set_reminder         → APScheduler
     ├── add_todo / list_todos → SQLite (로컬)
     ├── add_memo / search_memo → SQLite (로컬)
     ├── convert_currency     → open.er-api.com (무료)
     ├── translate_text       → DeepL API
     ├── web_search           → Serper.dev
     └── control_smart_home  → SmartThings / Google Home
     ↓
[응답 생성]
     ↓
[TTS 텍스트→음성] ────── Flutter TTS (무료)
     ↓
[스마트폰 스피커 출력]
```

## 컴포넌트 설명

### 1. 웨이크워드 (Picovoice Porcupine)
- 온디바이스 동작 → 상시대기 가능, 저전력
- 커스텀 웨이크워드 "루이스" 학습 필요 (.ppn 파일)
- 인터넷 연결 없이도 동작

### 2. Intent Router (`app/agent/router.py`)
- LLM 호출 없이 키워드 매칭으로 1차 분류
- 70% 이상의 호출에서 LLM 사용 불필요 → 비용 절감
- 타이머, 알람, 환율 등 단순 의도는 직접 처리

### 3. LangGraph Agent (`app/agent/orchestrator.py`)
- ReAct 패턴: 생각 → 도구 선택 → 실행 → 관찰 → 반복
- MemorySaver로 세션별 대화 컨텍스트 유지
- Haiku(기본) / Sonnet(복잡) 동적 모델 전환

### 4. 로컬 DB (SQLite)
- 할일, 메모, 리마인더 로컬 저장
- 인터넷 없어도 기본 기능 동작
- 향후 Firestore 동기화 추가 가능

## 비용 최적화 전략

| 전략 | 절감 효과 |
|------|----------|
| Intent Router로 LLM 호출 줄이기 | ~70% |
| Haiku 기본, Sonnet은 필요시만 | ~10배 |
| 응답 캐싱 (10분 TTL) | ~30~50% |
| 온디바이스 STT/웨이크워드 | 무료화 |

## 보안 설계

- API 키는 백엔드 서버에만 존재 (앱에 하드코딩 금지)
- 앱 ↔ 백엔드 통신: JWT 인증 + HTTPS
- 웨이크워드 감지 후에만 음성 서버 전송 (온디바이스 처리)
- Google OAuth 토큰: Keychain/Keystore 암호화 저장

## 배포 구성 (Phase 2)

```
[Flutter 앱] → [Google Cloud Run] → [Cloud SQL / Firestore]
                     ↕
               [Redis (캐시)]
```

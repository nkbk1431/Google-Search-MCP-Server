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
     ├── 타이머/알람    → 직접 처리 (LLM 불필요)
     ├── 통신           → get_phone_intent / get_sms_intent
     ├── 미디어         → search_youtube / search_music
     ├── 내비게이션     → get_directions
     ├── 스마트홈       → control_smart_home
     ├── 검색           → web_search
     └── 나머지         → LangGraph Agent
     ↓
[LangGraph ReAct Agent]
     ├── Claude Haiku 4.5  (기본, 저비용)
     └── Claude Sonnet 4.6 (복잡 작업, 필요시)
     ↓
[Tool 실행]
     ├── get_weather          → OpenWeatherMap API  (캐시 10분)
     ├── recommend_outfit     → 규칙 기반
     ├── add_calendar_event   → Google Calendar API
     ├── list_calendar_events → Google Calendar API
     ├── set_reminder         → APScheduler + FCM 푸시
     ├── add_todo / list_todos / complete_todo → SQLite
     ├── add_memo / search_memo / list_memos   → SQLite
     ├── convert_currency     → open.er-api.com (캐시 10분)
     ├── translate_text       → DeepL API
     ├── web_search           → Serper.dev
     ├── search_youtube       → Flutter OPEN_YOUTUBE 인텐트
     ├── search_music         → Spotify API / Flutter PLAY_MUSIC 인텐트
     ├── get_directions       → Google Maps API / Flutter OPEN_MAPS 인텐트
     ├── get_phone_intent     → Flutter PHONE_CALL 인텐트
     ├── get_sms_intent       → Flutter SEND_SMS 인텐트
     └── control_smart_home  → Flutter SMART_HOME_CONTROL 인텐트
     ↓
[응답 생성 + 개인화 학습]
     ├── PersonalizationService → 선호도 추출 후 DB 저장
     └── ConversationSummarizer → 10턴 초과 시 백그라운드 요약
     ↓
[TTS 텍스트→음성]
     ├── ElevenLabs API (eleven_multilingual_v2) → MP3 스트리밍
     └── Flutter TTS (폴백, ElevenLabs 키 없을 때)
     ↓
[스마트폰 스피커 출력]
```

---

## 컴포넌트 설명

### 1. 웨이크워드 (Picovoice Porcupine)
- 온디바이스 동작 → 상시대기 가능, 저전력
- 커스텀 웨이크워드 "루이스" 학습 필요 (.ppn 파일)
- 인터넷 연결 없이도 동작

### 2. Intent Router (`app/agent/router.py`)
- LLM 호출 없이 키워드 매칭으로 1차 분류
- 70% 이상의 호출에서 LLM 사용 불필요 → 비용 절감
- 15개 의도 클래스: ALARM, TIMER, WEATHER, CALENDAR, REMINDER, MEMO,
  TODO, CURRENCY, TRANSLATE, SEARCH, COMMUNICATION, MEDIA, NAVIGATION,
  SMART_HOME, GENERAL
- `needs_llm=False` 의도는 직접 처리, 나머지는 LangGraph로 위임

### 3. LangGraph Agent (`app/agent/orchestrator.py`)
- ReAct 패턴: 생각 → 도구 선택 → 실행 → 관찰 → 반복
- MemorySaver로 세션별 대화 컨텍스트 유지
- Haiku(기본) / Sonnet(복잡) 동적 모델 전환

### 4. PersonalizationService (`app/services/personalization.py`)
- 대화에서 선호도 자동 추출 (정규식 기반)
- `home_city`, `commute_mode`, `wake_time` 등 사용자 프로필 학습
- `UserPreference` 모델로 SQLite에 영구 저장
- `GET/PUT/DELETE /api/v1/preferences` 엔드포인트로 수동 관리 가능

### 5. ConversationSummarizer (`app/services/summarizer.py`)
- 대화가 10턴을 초과하면 백그라운드 `asyncio.create_task`로 요약
- 요약 결과를 MemorySaver 컨텍스트에 주입 → 무한 컨텍스트 비용 방지
- Claude Haiku 사용 (요약은 저비용)

### 6. QuotaGuard (`app/services/quota.py`)
- 분당 API 호출 횟수 제한 (thread-safe)
- 만료된 호출 기록 자동 정리 (1분 슬라이딩 윈도우)
- `RuntimeError`로 한도 초과 알림

### 7. Cache Service (`app/services/cache.py`)
- Redis 우선, 없으면 메모리 딕셔너리 폴백
- 10분 TTL (날씨, 환율 등 자주 변하지 않는 데이터)
- `make_weather_key(city)` / `make_rate_key(ccy)` 키 헬퍼 제공

### 8. TokenTracker (`app/services/token_tracker.py`)
- LLM 호출마다 입·출력 토큰 수를 `TokenUsage` 모델로 DB 저장
- 일별/월별 사용량 조회 및 예상 비용 계산
- `GET /api/v1/chat/usage` 엔드포인트로 노출

### 9. ElevenLabs TTS (`app/services/tts.py`)
- `eleven_multilingual_v2` 모델로 한국어 자연스러운 음성 합성
- 텍스트 전처리: 이모지 제거, 마크다운 제거, 특수문자 정규화
- MP3 스트리밍 응답 (`StreamingResponse`)
- ElevenLabs API 키 없을 때 `204 No Content` 반환 (앱이 Flutter TTS 폴백)
- Rate Limit: 20회/분

### 10. FCM 푸시 알림 (`app/api/webhook.py`)
- `FcmToken` 모델로 FCM 토큰을 DB에 영구 저장 (서버 재시작에도 유지)
- 리마인더 발동 시 `push_reminder_to_user()` 호출 → FCM HTTP v1 API
- `POST /api/v1/webhook/fcm/register` : 토큰 등록/갱신 (upsert)
- `DELETE /api/v1/webhook/fcm/unregister` : 로그아웃 시 토큰 삭제

### 11. 로컬 DB (SQLite)
- 할일, 메모, 리마인더, 선호도, FCM 토큰, 토큰 사용량 로컬 저장
- 인터넷 없어도 기본 기능 동작
- 향후 Firestore 동기화 추가 가능

---

## Flutter 앱 아키텍처

```
lib/
├── main.dart                  # Firebase 초기화, FCM 설정, 앱 진입
├── core/
│   ├── services/
│   │   ├── api_client.dart    # Dio 기반 HTTP 클라이언트 (싱글턴)
│   │   │                      # JWT 자동 갱신 인터셉터 (_PendingRequest 큐)
│   │   │                      # FCM 토큰 등록/해제
│   │   └── notification_service.dart  # 즉시 알림 + zonedSchedule 예약 알림
│   ├── providers/
│   │   ├── auth_provider.dart         # 로그인/로그아웃 상태 (Riverpod)
│   │   ├── chat_provider.dart         # 메시지 목록, 전송, SSE 스트림
│   │   ├── voice_pipeline.dart        # STT → 의도 분류 → API → TTS 파이프라인
│   │   └── settings_provider.dart     # 앱 설정 (SharedPreferences)
│   └── widgets/
│       └── waveform_widget.dart       # WaveformWidget + PulseRingWidget 애니메이션
```

### 인증 흐름 (JWT 자동 갱신)
```
API 요청 → 401 응답
     ↓
_PendingRequest 큐에 추가
     ↓
refresh_token으로 /auth/refresh 호출
     ↓
새 access_token 발급 → SecureStorage 저장
     ↓
큐에 쌓인 요청 모두 재시도
     ↓
refresh도 실패 → AuthExpiredException → 로그아웃 화면
```

### FCM 등록 흐름
```
앱 시작 → Firebase.initializeApp()
     ↓
FirebaseMessaging.getToken() → FCM 토큰 발급
     ↓
POST /api/v1/webhook/fcm/register → 서버 DB 저장
     ↓
서버 리마인더 발동 → FCM 푸시
     ├── 백그라운드: _firebaseMessagingBackgroundHandler → 시스템 알림
     └── 포그라운드: onMessage.listen → NotificationService.show()
     ↓
로그아웃 → DELETE /api/v1/webhook/fcm/unregister
```

---

## 비용 최적화 전략

| 전략 | 절감 효과 |
|------|----------|
| Intent Router로 LLM 호출 줄이기 | ~70% |
| Haiku 기본, Sonnet은 필요시만 | ~10배 |
| Redis/메모리 응답 캐싱 (10분 TTL) | ~30~50% |
| ConversationSummarizer (10턴 압축) | 긴 대화 비용 방지 |
| QuotaGuard 분당 호출 제한 | 과금 폭탄 방지 |
| 온디바이스 STT/웨이크워드 | 무료화 |

---

## 보안 설계

- API 키는 백엔드 서버에만 존재 (앱에 하드코딩 금지)
- 앱 ↔ 백엔드 통신: JWT 인증 + HTTPS
- 웨이크워드 감지 후에만 음성 서버 전송 (온디바이스 처리)
- Google OAuth 토큰: Keychain/Keystore 암호화 저장
- `slowapi` Rate Limiting: `/chat` 30회/분, `/tts` 20회/분 (IP 기준)
- 비밀번호: `passlib[bcrypt]` 해싱

---

## 배포 구성

```
[Flutter 앱]
     ↓ HTTPS + JWT
[Google Cloud Run]
     ├── louis-api (FastAPI)
     │     ├── SQLite (로컬) or Cloud SQL (프로덕션)
     │     ├── Redis (캐시, 선택)
     │     └── APScheduler (리마인더)
     │           ↓ FCM HTTP v1
     └── [Firebase Cloud Messaging]
               ↓ 푸시 알림
          [스마트폰 알림 센터]
```

---

## 테스트 커버리지

| 모듈 | 테스트 파일 | 테스트 수 |
|------|------------|----------|
| Intent Router | `test_router.py` | 32+ |
| 날씨/옷차림 | `test_weather.py` | - |
| 캘린더 | `test_calendar.py` | 17 |
| 알람 | `test_alarm.py` | 5 |
| 통신 (전화/SMS/이메일) | `test_communication.py` | 14 |
| 내비게이션 | `test_navigation.py` | 8 |
| 미디어 (유튜브/음악) | `test_media.py` | 10 |
| 스마트홈 | `test_smart_home.py` | 18 |
| 메모/할일 | `test_memo_todo.py` | 19 |
| 할당량 관리 | `test_quota.py` | 12 |
| 캐시 서비스 | `test_cache.py` | 22 |
| 토큰 트래커 | `test_token_tracker.py` | 15 |
| 웹훅/FCM | `test_webhook.py` | 11 |
| Flutter API 클라이언트 | `api_client_test.dart` | 15 |
| Flutter 인증 | `auth_provider_test.dart` | 10 |
| Flutter 채팅 | `chat_provider_test.dart` | 21 |
| Flutter 설정 | `settings_provider_test.dart` | 13 |
| Flutter 음성 파이프라인 | `voice_pipeline_test.dart` | 14 |
| Flutter 파형 위젯 | `waveform_widget_test.dart` | 13 |

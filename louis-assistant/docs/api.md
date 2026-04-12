# 루이스(Louis) 개인비서 - API 문서

## 기본 URL
- 개발: `http://localhost:8000`
- 프로덕션: `https://your-cloudrun-url.run.app`

---

## 인증

모든 `/api/v1/*` 엔드포인트는 Bearer JWT 토큰 인증이 필요합니다.

### POST /api/v1/auth/token
로그인 (액세스·리프레시 토큰 발급)

```bash
curl -X POST /api/v1/auth/token \
  -d "username=admin&password=louis1234" \
  -H "Content-Type: application/x-www-form-urlencoded"
```

**응답:**
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer"
}
```

### POST /api/v1/auth/register
신규 회원가입

**요청:**
```json
{ "username": "alice", "password": "securepass123" }
```

**검증 규칙:**
- `username`: 3-32자, `[a-zA-Z0-9_]`만 허용
- `password`: 8-64자

**응답:** 201 (성공) · 409 (이미 존재)

### POST /api/v1/auth/refresh
리프레시 토큰으로 액세스 토큰 재발급

```json
{ "refresh_token": "eyJ..." }
```

### GET /api/v1/auth/me
현재 로그인 사용자 정보 조회

```json
{ "username": "admin" }
```

### DELETE /api/v1/auth/me
계정 삭제

---

## 채팅

### POST /api/v1/chat
루이스에게 말하기

**요청:**
```json
{
  "text": "오늘 날씨 어때?",
  "session_id": "user-session-1"
}
```

| 필드 | 타입 | 제약 |
|------|------|------|
| `text` | string | 1-500자 필수 |
| `session_id` | string | 기본값 `"default"` |

**응답:**
```json
{
  "reply": "서울 현재 18도, 최고 22도 최저 12도, 맑음이에요.",
  "tool_calls": [
    {"tool": "get_weather", "args": {"city": "Seoul"}}
  ],
  "tokens": {"in": 150, "out": 45}
}
```

**Rate Limit:** 30회/분 (IP 기준)

### POST /api/v1/chat/stream
SSE 스트리밍 응답

**헤더:** `Accept: text/event-stream`

```
data: 서울
data:  현재
data:  18도
...
data: [DONE]
```

### GET /api/v1/chat/usage
오늘 토큰 사용량 및 월간 예상 비용 조회

```json
{
  "user": "admin",
  "today_tokens": {"in": 1200, "out": 450},
  "today_total": 1650,
  "daily_limit": 100000,
  "remaining": 98350,
  "monthly_cost_usd": 0.0125,
  "monthly_budget_usd": 10.0
}
```

---

## TTS (음성 합성)

### POST /api/v1/tts
텍스트를 MP3 오디오로 변환 (ElevenLabs)

| 파라미터 | 기본값 | 설명 |
|----------|--------|------|
| `text` | — | 변환할 텍스트 (쿼리 파라미터) |
| `voice_id` | `21m00Tcm4TlvDq8ikWAM` | ElevenLabs 보이스 ID |

**응답:**
- `200 OK` + `audio/mpeg` (MP3 바이너리)
- `204 No Content` (ElevenLabs API 키 없을 때)

**Rate Limit:** 20회/분

### GET /api/v1/tts/voices
사용 가능한 보이스 목록

```json
{
  "voices": [
    {"id": "21m00Tcm4TlvDq8ikWAM", "name": "Rachel"},
    {"id": "EXAVITQu4vr4xnSDxMaL", "name": "Bella"}
  ]
}
```

---

## 선호도

### GET /api/v1/preferences
학습된 사용자 선호도 전체 조회

```json
{
  "user": "admin",
  "preferences": {
    "home_city": "서울",
    "commute_mode": "지하철",
    "wake_time": "07:30"
  }
}
```

### PUT /api/v1/preferences/{key}
선호도 수동 설정

```bash
PUT /api/v1/preferences/home_city?value=부산
```

```json
{ "user": "admin", "key": "home_city", "value": "부산", "status": "saved" }
```

### DELETE /api/v1/preferences/{key}
특정 선호도 삭제

---

## 웹훅 / 푸시 알림

### POST /api/v1/webhook/fcm/register
앱의 FCM 토큰을 서버에 등록 (로그인 후 앱 시작 시 자동 호출)

```json
{ "fcm_token": "fBm9cH..." }
```

**응답:**
```json
{ "status": "ok", "user": "admin" }
```

### DELETE /api/v1/webhook/fcm/unregister
FCM 토큰 삭제 (로그아웃 시 자동 호출)

### POST /api/v1/webhook/push/send
사용자에게 푸시 알림 직접 발송

```json
{
  "title": "루이스 리마인더",
  "body": "약 먹을 시간이에요",
  "data": {}
}
```

**에러:** `404` FCM 토큰 미등록

---

## 상태 확인

### GET /
```json
{ "message": "루이스 API 정상 동작 중", "version": "1.0.0" }
```

### GET /health
인증 불필요

```json
{
  "status": "ok",
  "env": "development",
  "llm_model": "claude-haiku-4-5-20251001"
}
```

---

## 에러 코드

| 코드 | 설명 |
|------|------|
| 401 | 인증 토큰 없음 또는 만료 (리프레시 필요) |
| 404 | 리소스를 찾을 수 없음 |
| 409 | 이미 존재하는 리소스 (중복 사용자명 등) |
| 422 | 요청 형식 오류 (필드 검증 실패) |
| 429 | Rate Limit 초과 |
| 500 | 서버 내부 오류 |

---

## 시나리오별 예시

### 날씨 + 옷차림
```json
{"text": "오늘 날씨 어때? 뭐 입을까?"}
// → get_weather → recommend_outfit 순차 호출
```

### 일정 추가
```json
{"text": "내일 오후 3시 치과 예약 추가해줘"}
// → add_calendar_event(title="치과 예약", start_time="내일 오후 3시")
```

### 리마인더
```json
{"text": "30분 뒤에 약 먹으라고 알려줘"}
// → set_reminder(content="약 먹기", minutes_later=30)
```

### 환율
```json
{"text": "100달러 얼마야?"}
// → convert_currency(amount=100, from_ccy="USD", to_ccy="KRW")
```

### 전화 걸기
```json
{"text": "엄마한테 전화해줘"}
// → get_phone_intent(contact_name="엄마")
// → Flutter 앱이 PHONE_CALL 인텐트 처리
```

### 스마트홈 제어
```json
{"text": "거실 불 꺼줘"}
// → control_smart_home(device="불", action="꺼줘", room="거실")
```

### 길찾기
```json
{"text": "강남역에서 홍대까지 가는 길 알려줘"}
// → get_directions(origin="강남역", destination="홍대입구역", mode="transit")
// → Flutter 앱이 OPEN_MAPS 인텐트로 지도 앱 실행
```

---

## 인증 흐름 (Flutter 앱)

```
1. 앱 시작 → FlutterSecureStorage에서 access_token 확인
2. 토큰 있음 → 인증 상태로 진입
3. API 요청 → 401 응답 → refresh_token으로 /auth/refresh 호출
4. 새 토큰 저장 → 원래 요청 재시도
5. refresh도 실패 → 로그아웃 화면으로 이동
```

## FCM 등록 흐름

```
1. 앱 시작 → Firebase.initializeApp()
2. FirebaseMessaging.getToken() → FCM 토큰 발급
3. POST /api/v1/webhook/fcm/register → 서버 DB에 저장
4. 서버 리마인더 발생 → FCM 푸시 → NotificationService.show()
5. 로그아웃 → DELETE /api/v1/webhook/fcm/unregister
```

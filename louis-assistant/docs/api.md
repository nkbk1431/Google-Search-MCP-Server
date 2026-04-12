# 루이스(Louis) 개인비서 - API 문서

## 기본 URL
- 개발: `http://localhost:8000`
- 프로덕션: `https://your-cloudrun-url.run.app`

## 인증

모든 API는 Bearer JWT 토큰 인증이 필요합니다.

```bash
# 토큰 발급
curl -X POST /api/v1/auth/token \
  -d "username=admin&password=louis1234"

# 응답
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer"
}
```

## 엔드포인트

### POST /api/v1/chat
루이스에게 말하기

**요청:**
```json
{
  "text": "오늘 날씨 어때?",
  "session_id": "user-session-1"
}
```

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
오늘 토큰 사용량 조회

**응답:**
```json
{
  "user": "admin",
  "today_tokens": {"in": 1200, "out": 450},
  "limit": 100000,
  "remaining": 98350
}
```

### GET /health
서버 상태 확인 (인증 불필요)

```json
{
  "status": "ok",
  "env": "development",
  "llm_model": "claude-haiku-4-5-20251001"
}
```

## 에러 코드

| 코드 | 설명 |
|------|------|
| 401 | 인증 토큰 없음 또는 만료 |
| 422 | 요청 형식 오류 (text 필드 누락 등) |
| 500 | 서버 내부 오류 |

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

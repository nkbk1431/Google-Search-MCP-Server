#!/bin/bash
# 루이스 백엔드 - 스마트폰 테스트용 빠른 시작 스크립트
# 사용법: cd backend && bash quick_start.sh [포트]
set -e

PORT=${1:-8000}

# ── 현재 머신의 로컬 IP 출력 ──────────────────────────────────────────
LOCAL_IP=$(ip route get 1 2>/dev/null | awk '{print $7; exit}' || \
           ifconfig 2>/dev/null | grep 'inet ' | grep -v '127.0.0.1' | awk '{print $2}' | head -1 || \
           hostname -I 2>/dev/null | awk '{print $1}')

echo "========================================"
echo " 루이스 백엔드 시작 (스마트폰 테스트 모드)"
echo "========================================"
echo ""

# ── .env 파일 생성 (없으면) ──────────────────────────────────────────
if [ ! -f .env ]; then
  echo ">>> .env 파일이 없어 기본 설정으로 생성합니다..."
  cat > .env << 'ENVEOF'
APP_ENV=development
APP_SECRET_KEY=test-secret-key-change-in-production
APP_PORT=8000
APP_HOST=0.0.0.0

# 날씨 기능을 사용하려면 아래 키를 입력하세요
# OpenWeatherMap 무료 계정: https://openweathermap.org/api
OPENWEATHER_API_KEY=

# AI 응답을 사용하려면 아래 키를 입력하세요
# Anthropic 콘솔: https://console.anthropic.com
ANTHROPIC_API_KEY=

DATABASE_URL=sqlite+aiosqlite:///./louis.db
LOG_LEVEL=INFO
ENVEOF
  echo ">>> .env 생성 완료. 키를 입력하려면 backend/.env 파일을 편집하세요."
  echo ""
fi

# ── 의존성 설치 ──────────────────────────────────────────────────────
echo ">>> Python 패키지 설치 중..."
pip install -r requirements.txt -q
echo ""

# ── 서버 시작 안내 ───────────────────────────────────────────────────
echo "========================================"
echo " 접속 정보"
echo "========================================"
echo ""
echo "  PC 브라우저:  http://localhost:${PORT}/docs"
echo "  스마트폰:     http://${LOCAL_IP}:${PORT}"
echo ""
echo "  테스트 계정:  admin / louis1234"
echo ""
echo "  Flutter 앱 빌드 명령:"
echo "  cd mobile"
echo "  flutter build apk --debug --dart-define=BASE_URL=http://${LOCAL_IP}:${PORT}"
echo ""
echo "  또는 앱 설정 화면에서 서버 URL을 직접 입력하세요:"
echo "  http://${LOCAL_IP}:${PORT}"
echo "========================================"
echo ""

# ── 방화벽 안내 (포트가 막혀있을 경우) ──────────────────────────────
if command -v ufw &>/dev/null; then
  if ufw status 2>/dev/null | grep -q "Status: active"; then
    echo ">>> [참고] 방화벽(ufw)이 활성화돼 있어요."
    echo "    스마트폰에서 접속 안 되면 아래 명령을 실행하세요:"
    echo "    sudo ufw allow ${PORT}"
    echo ""
  fi
fi

# ── uvicorn 실행 ──────────────────────────────────────────────────────
uvicorn app.main:app \
  --host 0.0.0.0 \
  --port "${PORT}" \
  --reload \
  --log-level info

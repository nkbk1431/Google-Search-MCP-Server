# 루이스 백엔드 - Windows 스마트폰 테스트용 빠른 시작 스크립트
# 사용법: .\quick_start.ps1 [포트]
# 전제: Python 3.12.13 전역 설치, backend\ 디렉터리에서 실행
param([int]$Port = 8000)

$ErrorActionPreference = "Stop"

# ── 로컬 IP 감지 ──────────────────────────────────────────────────────
$LocalIP = (Get-NetIPAddress -AddressFamily IPv4 |
            Where-Object { $_.IPAddress -notlike "127.*" -and $_.IPAddress -notlike "169.*" } |
            Select-Object -First 1).IPAddress

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host " 루이스 백엔드 시작 (스마트폰 테스트 모드)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# ── .env 파일 생성 (없으면) ────────────────────────────────────────────
if (-not (Test-Path ".env")) {
    Write-Host ">>> .env 파일이 없어 기본 설정으로 생성합니다..." -ForegroundColor Yellow
    @"
APP_ENV=development
APP_SECRET_KEY=test-secret-key-change-in-production
APP_PORT=$Port
APP_HOST=0.0.0.0

# 날씨 기능을 사용하려면 아래 키를 입력하세요
# OpenWeatherMap 무료 계정: https://openweathermap.org/api
OPENWEATHER_API_KEY=

# AI 응답을 사용하려면 아래 키를 입력하세요
# Anthropic 콘솔: https://console.anthropic.com
ANTHROPIC_API_KEY=

DATABASE_URL=sqlite+aiosqlite:///./louis.db
LOG_LEVEL=INFO
"@ | Out-File -FilePath ".env" -Encoding utf8
    Write-Host ">>> .env 생성 완료. 키를 입력하려면 backend\.env 파일을 편집하세요." -ForegroundColor Green
    Write-Host ""
}

# ── 의존성 설치 ────────────────────────────────────────────────────────
Write-Host ">>> Python 패키지 설치 중..." -ForegroundColor Yellow
python -m pip install -r requirements.txt -q
Write-Host ""

# ── 방화벽 규칙 확인 및 추가 (관리자 권한 있을 때만) ──────────────────────
$RuleName = "Louis Backend Port $Port"
$existingRule = Get-NetFirewallRule -DisplayName $RuleName -ErrorAction SilentlyContinue
if (-not $existingRule) {
    try {
        New-NetFirewallRule -DisplayName $RuleName -Direction Inbound -Protocol TCP -LocalPort $Port -Action Allow | Out-Null
        Write-Host ">>> 방화벽 포트 $Port 열었어요." -ForegroundColor Green
    } catch {
        Write-Host ">>> [참고] 방화벽 설정 권한 없음. 스마트폰 접속 안 되면 관리자 PowerShell에서 실행하세요:" -ForegroundColor Yellow
        Write-Host "    netsh advfirewall firewall add rule name=`"Louis Backend`" dir=in action=allow protocol=TCP localport=$Port" -ForegroundColor Gray
    }
}
Write-Host ""

# ── 접속 정보 출력 ──────────────────────────────────────────────────────
Write-Host "========================================" -ForegroundColor Green
Write-Host " 접속 정보" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "  PC 브라우저:  http://localhost:$Port/docs" -ForegroundColor White
Write-Host "  스마트폰:     http://${LocalIP}:$Port" -ForegroundColor White
Write-Host ""
Write-Host "  테스트 계정:  admin / louis1234" -ForegroundColor White
Write-Host ""
Write-Host "  Flutter APK 빌드 명령:" -ForegroundColor White
Write-Host "  cd ..\mobile" -ForegroundColor Gray
Write-Host "  .\build_test_apk.ps1 $LocalIP" -ForegroundColor Gray
Write-Host ""
Write-Host "  또는 앱 설정 화면에서 서버 URL을 직접 입력:" -ForegroundColor White
Write-Host "  http://${LocalIP}:$Port" -ForegroundColor Gray
Write-Host "========================================" -ForegroundColor Green
Write-Host ""

# ── uvicorn 실행 ────────────────────────────────────────────────────────
uvicorn app.main:app --host 0.0.0.0 --port $Port --reload --log-level info

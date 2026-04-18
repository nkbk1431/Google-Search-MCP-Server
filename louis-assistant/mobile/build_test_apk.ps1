# 루이스 Flutter - Windows 스마트폰 테스트용 APK 빌드 스크립트
# 사용법: .\build_test_apk.ps1 <백엔드_IP>
#
# 예시:
#   .\build_test_apk.ps1 192.168.0.10
#   .\build_test_apk.ps1 192.168.0.10:8080
#   .\build_test_apk.ps1 abc123.ngrok-free.app
param([string]$BackendAddr = "")

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

if (-not $BackendAddr) {
    Write-Host "사용법: .\build_test_apk.ps1 <백엔드_주소>" -ForegroundColor Red
    Write-Host ""
    Write-Host "예시:"
    Write-Host "  .\build_test_apk.ps1 192.168.0.10"
    Write-Host "  .\build_test_apk.ps1 192.168.0.10:8080"
    Write-Host "  .\build_test_apk.ps1 abc123.ngrok-free.app"
    exit 1
}

# http:// 없으면 자동 추가
if ($BackendAddr -notmatch "^https?://") {
    if ($BackendAddr -match "ngrok") {
        $BaseUrl = "https://$BackendAddr"
    } else {
        $BaseUrl = "http://$BackendAddr"
    }
} else {
    $BaseUrl = $BackendAddr
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host " 루이스 APK 빌드" -ForegroundColor Cyan
Write-Host " 백엔드 URL: $BaseUrl" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Flutter 설치 확인
if (-not (Get-Command flutter -ErrorAction SilentlyContinue)) {
    Write-Host "[에러] flutter 명령을 찾을 수 없어요." -ForegroundColor Red
    Write-Host "Flutter SDK 설치 후 PATH에 추가해주세요." -ForegroundColor Yellow
    exit 1
}

Write-Host ">>> flutter pub get..." -ForegroundColor Yellow
flutter pub get

Write-Host ""
Write-Host ">>> APK 빌드 중... (처음 빌드는 5~10분 소요)" -ForegroundColor Yellow
flutter build apk --debug --dart-define="BASE_URL=$BaseUrl"

$ApkPath = "build\app\outputs\flutter-apk\app-debug.apk"

if (Test-Path $ApkPath) {
    $Size = [math]::Round((Get-Item $ApkPath).Length / 1MB, 1)
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host " 빌드 완료!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "  APK 위치: mobile\$ApkPath" -ForegroundColor White
    Write-Host "  파일 크기: ${Size}MB" -ForegroundColor White
    Write-Host ""
    Write-Host "  설치 방법:" -ForegroundColor White
    Write-Host "  1) USB 연결 후:  adb install $ApkPath" -ForegroundColor Gray
    Write-Host "  2) 파일 전송:    APK를 스마트폰에 복사 후 직접 설치" -ForegroundColor Gray
    Write-Host "     (설정 > 보안 > 출처를 알 수 없는 앱 허용 필요)" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  로그인 정보:" -ForegroundColor White
    Write-Host "    아이디: admin" -ForegroundColor Gray
    Write-Host "    비밀번호: louis1234" -ForegroundColor Gray
    Write-Host "========================================" -ForegroundColor Green

    $open = Read-Host "`n탐색기에서 APK 파일 위치를 열까요? (y/n)"
    if ($open -eq 'y' -or $open -eq 'Y') {
        Start-Process explorer.exe -ArgumentList "/select,`"$(Resolve-Path $ApkPath)`""
    }
} else {
    Write-Host "[에러] 빌드 실패. 위 오류 메시지를 확인하세요." -ForegroundColor Red
    exit 1
}

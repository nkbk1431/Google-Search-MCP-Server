#!/bin/bash
# 루이스 Flutter - 스마트폰 테스트용 APK 빌드 스크립트
# 사용법: cd mobile && bash build_test_apk.sh <백엔드_IP>
#
# 예시:
#   bash build_test_apk.sh 192.168.0.10          # 포트 8000 기본값
#   bash build_test_apk.sh 192.168.0.10:8080     # 포트 지정
#   bash build_test_apk.sh my-server.ngrok.io    # ngrok URL

set -e

INPUT=${1:-""}

if [ -z "$INPUT" ]; then
  echo "사용법: bash build_test_apk.sh <백엔드_주소>"
  echo ""
  echo "예시:"
  echo "  bash build_test_apk.sh 192.168.0.10"
  echo "  bash build_test_apk.sh 192.168.0.10:8080"
  echo "  bash build_test_apk.sh abc123.ngrok.io"
  exit 1
fi

# http:// 없으면 자동 추가
if [[ "$INPUT" != http* ]]; then
  # ngrok 도메인이면 https, 로컬 IP면 http
  if [[ "$INPUT" == *.ngrok* ]] || [[ "$INPUT" == *.ngrok-free* ]]; then
    BASE_URL="https://${INPUT}"
  else
    BASE_URL="http://${INPUT}"
  fi
else
  BASE_URL="$INPUT"
fi

echo "========================================"
echo " 루이스 APK 빌드"
echo " 백엔드 URL: ${BASE_URL}"
echo "========================================"
echo ""

# Flutter 의존성 확인
echo ">>> flutter pub get..."
flutter pub get

echo ""
echo ">>> APK 빌드 중... (처음 빌드는 5~10분 소요)"
flutter build apk \
  --debug \
  --dart-define=BASE_URL="${BASE_URL}"

APK_PATH="build/app/outputs/flutter-apk/app-debug.apk"

if [ -f "$APK_PATH" ]; then
  SIZE=$(du -sh "$APK_PATH" | cut -f1)
  echo ""
  echo "========================================"
  echo " 빌드 완료!"
  echo "========================================"
  echo ""
  echo "  APK 위치: mobile/${APK_PATH}"
  echo "  파일 크기: ${SIZE}"
  echo ""
  echo "  설치 방법:"
  echo "  1) USB 연결 후:  adb install ${APK_PATH}"
  echo "  2) 파일 전송:    ${APK_PATH} 를 스마트폰에 복사 후 직접 설치"
  echo "     (설정 > 보안 > 출처를 알 수 없는 앱 허용 필요)"
  echo ""
  echo "  로그인 정보:"
  echo "    아이디: admin"
  echo "    비밀번호: louis1234"
  echo ""
  echo "  서버 URL 변경: 앱 설정 화면에서도 변경 가능"
  echo "========================================"
else
  echo "빌드 실패. 위 오류 메시지를 확인하세요."
  exit 1
fi

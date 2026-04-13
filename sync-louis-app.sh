#!/bin/bash
# LOUIS_APP 동기화 스크립트
# 사용법: ./sync-louis-app.sh <GITHUB_PAT>
#
# louis-assistant/ 폴더를 LOUIS-1993-AI-Studio/LOUIS_APP의 main 브랜치에 동기화합니다.
# git subtree를 사용하므로 서브폴더만 LOUIS_APP 루트로 올라갑니다.
#
# 최초 1회 설정: git remote add louis-app https://github.com/LOUIS-1993-AI-Studio/LOUIS_APP.git
#   → 이미 설정된 경우 다시 실행하지 않아도 됩니다.

set -e

PAT="${1:-${LOUIS_APP_PAT}}"

if [[ -z "$PAT" ]]; then
  echo "사용법: ./sync-louis-app.sh <GITHUB_PAT>"
  echo "   또는: LOUIS_APP_PAT=ghp_xxx ./sync-louis-app.sh"
  exit 1
fi

REPO="https://${PAT}@github.com/LOUIS-1993-AI-Studio/LOUIS_APP.git"

echo ">>> LOUIS_APP 동기화 시작..."

# 현재 브랜치 저장
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)

# PAT을 remote URL에 임시 주입
git remote set-url louis-app "$REPO"

# subtree push: louis-assistant/ → LOUIS_APP main
git subtree push --prefix=louis-assistant louis-app main

# PAT 제거 (URL을 PAT 없는 버전으로 복원)
git remote set-url louis-app "https://github.com/LOUIS-1993-AI-Studio/LOUIS_APP.git"

echo ""
echo "✅ 동기화 완료!"
echo "   https://github.com/LOUIS-1993-AI-Studio/LOUIS_APP"

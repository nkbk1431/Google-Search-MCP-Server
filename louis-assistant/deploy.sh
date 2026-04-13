#!/bin/bash
# 루이스 개인비서 - 로컬 개발 / 프로덕션 배포 스크립트
set -e

COMMAND=${1:-help}

case "$COMMAND" in
  dev)
    echo ">>> 로컬 개발 서버 시작..."
    cd backend
    pip install -r requirements.txt -q
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
    ;;

  docker)
    echo ">>> Docker Compose로 시작..."
    docker-compose up --build
    ;;

  test)
    echo ">>> 테스트 실행..."
    cd backend
    pip install -r requirements.txt -q
    pytest tests/ -v --tb=short
    ;;

  gcloud)
    echo ">>> Google Cloud Run 배포..."
    PROJECT_ID=$(gcloud config get-value project)
    echo "프로젝트: $PROJECT_ID"
    gcloud builds submit --config cloudbuild.yaml
    echo "배포 완료!"
    gcloud run services describe louis-api --region=asia-northeast3 --format="value(status.url)"
    ;;

  logs)
    echo ">>> Cloud Run 로그 확인..."
    gcloud logs tail --filter="resource.type=cloud_run_revision AND resource.labels.service_name=louis-api"
    ;;

  secrets)
    echo ">>> Secret Manager에 API 키 등록..."

    _upsert_secret() {
      local name=$1 value=$2
      echo -n "$value" | gcloud secrets create "$name" --data-file=- 2>/dev/null || \
      echo -n "$value" | gcloud secrets versions add "$name" --data-file=-
    }

    # ── 필수 키 ────────────────────────────────────────────
    read -p "ANTHROPIC_API_KEY: " v; _upsert_secret anthropic-api-key "$v"
    read -p "APP_SECRET_KEY (JWT 서명, 32자+): " v; _upsert_secret louis-app-secret "$v"

    # ── 날씨/검색 ──────────────────────────────────────────
    read -p "OPENWEATHER_API_KEY [skip=Enter]: " v
    [[ -n "$v" ]] && _upsert_secret openweather-key "$v"

    read -p "SERPER_API_KEY [skip=Enter]: " v
    [[ -n "$v" ]] && _upsert_secret serper-key "$v"

    read -p "DEEPL_API_KEY [skip=Enter]: " v
    [[ -n "$v" ]] && _upsert_secret deepl-key "$v"

    read -p "ELEVENLABS_API_KEY [skip=Enter]: " v
    [[ -n "$v" ]] && _upsert_secret elevenlabs-key "$v"

    # ── Phase 12: 한국 특화 ─────────────────────────────────
    read -p "NAVER_CLIENT_ID [skip=Enter]: " v
    [[ -n "$v" ]] && _upsert_secret naver-client-id "$v"

    read -p "NAVER_CLIENT_SECRET [skip=Enter]: " v
    [[ -n "$v" ]] && _upsert_secret naver-client-secret "$v"

    read -p "SEOUL_API_KEY (지하철 실시간) [skip=Enter]: " v
    [[ -n "$v" ]] && _upsert_secret seoul-api-key "$v"

    read -p "KAKAO_API_KEY (주소검색) [skip=Enter]: " v
    [[ -n "$v" ]] && _upsert_secret kakao-api-key "$v"

    echo ""
    echo "✅ Secret Manager 등록 완료."
    echo "   gcloud secrets list 로 확인하세요."
    ;;

  *)
    echo "사용법: ./deploy.sh [dev|docker|test|gcloud|logs|secrets]"
    echo ""
    echo "  dev      - 로컬 uvicorn 개발 서버"
    echo "  docker   - Docker Compose 로컬 실행"
    echo "  test     - pytest 테스트"
    echo "  gcloud   - Google Cloud Run 배포"
    echo "  logs     - Cloud Run 로그 스트리밍"
    echo "  secrets  - Secret Manager에 API 키 등록"
    ;;
esac

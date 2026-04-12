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
    read -p "ANTHROPIC_API_KEY: " ANTHROPIC_KEY
    echo -n "$ANTHROPIC_KEY" | gcloud secrets create anthropic-api-key --data-file=- 2>/dev/null || \
    echo -n "$ANTHROPIC_KEY" | gcloud secrets versions add anthropic-api-key --data-file=-

    read -p "OPENWEATHER_API_KEY: " WEATHER_KEY
    echo -n "$WEATHER_KEY" | gcloud secrets create openweather-key --data-file=- 2>/dev/null || \
    echo -n "$WEATHER_KEY" | gcloud secrets versions add openweather-key --data-file=-

    echo "Secret Manager 등록 완료."
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

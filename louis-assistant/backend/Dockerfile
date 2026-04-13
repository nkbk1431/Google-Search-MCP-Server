FROM python:3.13-slim

WORKDIR /app

# 시스템 패키지 (pykrx의 lxml, numpy 빌드에 필요)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libffi-dev \
    libxml2-dev \
    libxslt1-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 파이썬 패키지 (캐시 레이어 최적화)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 소스 복사 (테스트 제외)
COPY app/ ./app/

# Google OAuth 토큰 디렉토리
RUN mkdir -p tokens

# 비루트 사용자 실행 (보안)
RUN adduser --disabled-password --gecos "" louis && \
    chown -R louis:louis /app
USER louis

# 포트
EXPOSE 8000

# 헬스체크
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 실행 (프로덕션: workers=2, 메모리 512Mi 기준)
CMD ["uvicorn", "app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "2", \
     "--log-level", "info", \
     "--access-log"]

"""
루이스 개인비서 - 환경변수 및 설정 관리
pydantic-settings로 .env 파일을 자동 로드합니다.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Anthropic ──────────────────────────────────────────
    anthropic_api_key: str = ""

    # ── Picovoice ──────────────────────────────────────────
    picovoice_access_key: str = ""

    # ── 날씨 (기상청 API허브) ──────────────────────────────
    kma_auth_key: str = ""   # apihub.kma.go.kr authKey

    # ── Google OAuth ───────────────────────────────────────
    google_client_secret_file: str = "./credentials.json"

    # ── 웹 검색 ────────────────────────────────────────────
    serper_api_key: str = ""

    # ── 번역 ───────────────────────────────────────────────
    deepl_api_key: str = ""

    # ── TTS ────────────────────────────────────────────────
    elevenlabs_api_key: str = ""

    # ── SMS/전화 ───────────────────────────────────────────
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_from_number: str = ""

    # ── 음악 ───────────────────────────────────────────────
    spotify_client_id: str = ""
    spotify_client_secret: str = ""

    # ── 지도 ───────────────────────────────────────────────
    google_maps_api_key: str = ""

    # ── 앱 ────────────────────────────────────────────────
    app_env: str = "development"
    app_secret_key: str = "change-this-to-a-long-random-string"
    app_port: int = 8000
    app_host: str = "0.0.0.0"

    # ── JWT ────────────────────────────────────────────────
    jwt_access_token_expire: int = 900       # 15분
    jwt_refresh_token_expire: int = 2592000  # 30일

    # ── LLM ────────────────────────────────────────────────
    llm_default_model: str = "claude-haiku-4-5-20251001"
    llm_complex_model: str = "claude-sonnet-4-6"
    llm_temperature: float = 0.2
    llm_max_tokens: int = 500

    # ── 비용 관리 ──────────────────────────────────────────
    daily_token_limit: int = 100_000
    monthly_budget_usd: float = 10.0

    # ── DB ─────────────────────────────────────────────────
    database_url: str = "sqlite+aiosqlite:///./louis.db"
    local_db_path: str = "./louis.db"

    # ── Redis ──────────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"

    # ── Phase 12: 교통 ────────────────────────────────────
    srt_id: str = ""               # SRT 회원 아이디
    srt_pw: str = ""               # SRT 비밀번호
    korail_id: str = ""            # 코레일 멤버십 아이디
    korail_pw: str = ""            # 코레일 멤버십 비밀번호
    seoul_api_key: str = ""        # 서울 열린데이터광장 API 키

    # ── Phase 12: 쇼핑 ────────────────────────────────────
    naver_client_id: str = ""      # 네이버 개발자센터 클라이언트 ID
    naver_client_secret: str = ""  # 네이버 개발자센터 시크릿

    # ── Phase 12: 지도/주소 ───────────────────────────────
    kakao_api_key: str = ""        # 카카오 REST API 키
    juso_api_key: str = ""         # 도로명주소 개발자센터 API 키 (행안부)

    # ── 기타 ──────────────────────────────────────────────
    timezone: str = "Asia/Seoul"
    log_level: str = "INFO"

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def google_quota_per_minute(self) -> int:
        return 50


@lru_cache
def get_settings() -> Settings:
    """싱글턴 설정 인스턴스 반환."""
    return Settings()


settings = get_settings()

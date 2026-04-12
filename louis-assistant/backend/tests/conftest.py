"""
pytest 공용 픽스처 (fixtures)
모든 테스트에서 공유하는 설정과 mock 객체 정의.
"""
import os
import pytest

# 테스트 환경변수 설정 (실제 API 호출 없이)
os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-test-key")
os.environ.setdefault("OPENWEATHER_API_KEY", "test-weather-key")
os.environ.setdefault("SERPER_API_KEY", "test-serper-key")
os.environ.setdefault("DEEPL_API_KEY", "test-deepl-key:fx")
os.environ.setdefault("APP_SECRET_KEY", "test-secret-key-for-pytest-only")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_louis.db")


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """테스트 전 인메모리 DB 초기화, 테스트 후 제거."""
    import sqlite3, os
    db_path = "./test_louis.db"
    yield
    # 테스트 완료 후 DB 파일 삭제
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
        except Exception:
            pass


@pytest.fixture
def mock_anthropic(mocker):
    """Claude API 모킹."""
    mock_llm = mocker.MagicMock()
    mock_llm.invoke.return_value = mocker.MagicMock(
        content="테스트 응답입니다.",
        usage_metadata={"input_tokens": 100, "output_tokens": 30},
    )
    return mock_llm


@pytest.fixture
def sample_weather_json():
    import json
    return json.dumps({
        "city": "Seoul",
        "temp_now": 18.5,
        "temp_max": 22.0,
        "temp_min": 13.0,
        "condition": "맑음",
        "wind_speed": 3.2,
        "humidity": 55,
    }, ensure_ascii=False)

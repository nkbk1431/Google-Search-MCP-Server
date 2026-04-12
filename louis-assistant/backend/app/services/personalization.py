"""
사용자 개인화 서비스

- 사용자 발화/행동 패턴에서 선호도를 자동 추출합니다.
- 선호도는 DB에 저장되고 시스템 프롬프트에 주입됩니다.
- 선호 도시, 이동 수단, 즐겨찾는 연락처 등을 학습합니다.
"""
import json
import logging
import re
from typing import Any

from app.db.session import get_sync_db
from app.db.models import UserPreference

log = logging.getLogger("louis.personalization")


# ── 선호도 키 상수 ──────────────────────────────────────────────────

class PrefKey:
    HOME_CITY = "home_city"           # 자주 묻는 날씨 도시
    COMMUTE_MODE = "commute_mode"     # 자주 쓰는 이동 수단
    WAKE_TIME = "wake_time"           # 자주 설정하는 알람 시각
    MUSIC_GENRE = "music_genre"       # 음악 장르/아티스트 선호
    FREQUENT_CONTACTS = "frequent_contacts"  # 자주 연락하는 사람
    PREFERRED_LANGUAGE = "language"   # 번역 대상 언어
    CURRENCY_PAIR = "currency_pair"   # 자주 쓰는 환율 쌍


# 패턴 → (pref_key, 값 추출 함수)
_EXTRACTORS: list[tuple[re.Pattern, str, callable]] = [
    (
        re.compile(r"(서울|부산|대구|인천|광주|대전|울산|세종|제주|수원|성남|고양|용인).*날씨", re.I),
        PrefKey.HOME_CITY,
        lambda m: m.group(1),
    ),
    (
        re.compile(r"(지하철|버스|택시|걷|자전거|드라이브|운전).*길|지도", re.I),
        PrefKey.COMMUTE_MODE,
        lambda m: {
            "지하철": "transit", "버스": "transit",
            "택시": "driving", "운전": "driving", "드라이브": "driving",
            "걷": "walking", "자전거": "bicycling",
        }.get(m.group(1), "transit"),
    ),
    (
        re.compile(r"(\d{1,2})시\s*(?:(\d{1,2})분)?\s*알람", re.I),
        PrefKey.WAKE_TIME,
        lambda m: f"{int(m.group(1)):02d}:{int(m.group(2) or 0):02d}",
    ),
    (
        re.compile(r"(영어|일본어|중국어|프랑스어|스페인어|독일어|러시아어)\s*로\s*번역", re.I),
        PrefKey.PREFERRED_LANGUAGE,
        lambda m: m.group(1),
    ),
    (
        re.compile(r"(달러|유로|엔|위안|파운드)\s*→?\s*(원|달러|유로|엔|위안|파운드)", re.I),
        PrefKey.CURRENCY_PAIR,
        lambda m: f"{m.group(1)}→{m.group(2)}",
    ),
]


class PersonalizationService:
    """사용자 선호도를 학습하고 제공합니다."""

    def learn_from_text(self, user_id: str, text: str) -> list[str]:
        """
        사용자 발화에서 선호도를 추출하여 DB에 저장합니다.

        Returns:
            저장된 pref_key 목록
        """
        learned: list[str] = []
        for pattern, key, extractor in _EXTRACTORS:
            m = pattern.search(text)
            if m:
                try:
                    value = extractor(m)
                    self._upsert(user_id, key, str(value))
                    learned.append(key)
                except Exception as exc:
                    log.debug(f"선호도 추출 실패 ({key}): {exc}")
        return learned

    def get_preference(self, user_id: str, key: str) -> str | None:
        """특정 선호도 값을 반환합니다."""
        prefs = self.get_all_preferences(user_id)
        return prefs.get(key)

    def get_all_preferences(self, user_id: str) -> dict[str, str]:
        """사용자의 모든 선호도를 {key: value} 딕셔너리로 반환합니다."""
        try:
            with get_sync_db() as db:
                rows = (
                    db.query(UserPreference)
                    .filter(UserPreference.user_id == user_id)
                    .order_by(UserPreference.update_count.desc())
                    .all()
                )
                return {r.pref_key: r.pref_value for r in rows}
        except Exception as exc:
            log.warning(f"선호도 조회 실패 ({user_id}): {exc}")
            return {}

    def set_preference(self, user_id: str, key: str, value: str) -> None:
        """선호도를 명시적으로 설정합니다 (사용자가 직접 설정한 경우)."""
        self._upsert(user_id, key, value, count_increment=0)

    def build_personalization_context(self, user_id: str) -> str:
        """
        시스템 프롬프트에 삽입할 개인화 컨텍스트 문자열을 생성합니다.
        선호도가 없으면 빈 문자열을 반환합니다.
        """
        prefs = self.get_all_preferences(user_id)
        if not prefs:
            return ""

        lines = ["[사용자 개인화 정보]"]
        label_map = {
            PrefKey.HOME_CITY: "자주 묻는 도시",
            PrefKey.COMMUTE_MODE: "선호 이동 수단",
            PrefKey.WAKE_TIME: "자주 설정하는 알람 시각",
            PrefKey.MUSIC_GENRE: "음악 선호",
            PrefKey.FREQUENT_CONTACTS: "자주 연락하는 사람",
            PrefKey.PREFERRED_LANGUAGE: "번역 선호 언어",
            PrefKey.CURRENCY_PAIR: "자주 쓰는 환율 쌍",
        }
        for key, value in prefs.items():
            label = label_map.get(key, key)
            lines.append(f"- {label}: {value}")

        return "\n".join(lines) + "\n"

    def _upsert(self, user_id: str, key: str, value: str, count_increment: int = 1) -> None:
        """선호도를 삽입 또는 업데이트합니다."""
        try:
            with get_sync_db() as db:
                row = (
                    db.query(UserPreference)
                    .filter(
                        UserPreference.user_id == user_id,
                        UserPreference.pref_key == key,
                    )
                    .first()
                )
                if row is None:
                    db.add(UserPreference(
                        user_id=user_id,
                        pref_key=key,
                        pref_value=value,
                        update_count=1,
                    ))
                else:
                    row.pref_value = value
                    row.update_count += count_increment
                db.commit()
                log.debug(f"선호도 저장: user={user_id} {key}={value}")
        except Exception as exc:
            log.warning(f"선호도 저장 실패 ({user_id}/{key}): {exc}")


# 싱글턴
_personalization_service: PersonalizationService | None = None


def get_personalization_service() -> PersonalizationService:
    global _personalization_service
    if _personalization_service is None:
        _personalization_service = PersonalizationService()
    return _personalization_service

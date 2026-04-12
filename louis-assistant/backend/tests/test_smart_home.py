"""
스마트홈 도구 테스트
control_smart_home 기능을 검증합니다.
"""
import json
import pytest

from app.agent.tools.smart_home import control_smart_home, DEVICE_ALIASES, ROOM_ALIASES


class TestControlSmartHome:

    def test_returns_json_string(self):
        result = control_smart_home.invoke({
            "device": "불",
            "action": "on",
        })
        data = json.loads(result)
        assert isinstance(data, dict)

    def test_action_is_smart_home_control(self):
        result = control_smart_home.invoke({
            "device": "조명",
            "action": "켜줘",
        })
        data = json.loads(result)
        assert data["action"] == "SMART_HOME_CONTROL"

    # ── 기기 별칭 매핑 ─────────────────────────────────

    def test_device_alias_불_maps_to_light(self):
        result = control_smart_home.invoke({"device": "불", "action": "on"})
        data = json.loads(result)
        assert data["device"] == "light"

    def test_device_alias_에어컨(self):
        result = control_smart_home.invoke({"device": "에어컨", "action": "on"})
        data = json.loads(result)
        assert data["device"] == "air_conditioner"

    def test_device_alias_tv(self):
        result = control_smart_home.invoke({"device": "TV", "action": "off"})
        data = json.loads(result)
        assert data["device"] == "tv"

    def test_unknown_device_preserved(self):
        """알 수 없는 기기명은 그대로 전달됩니다."""
        result = control_smart_home.invoke({"device": "로봇청소기", "action": "on"})
        data = json.loads(result)
        assert data["device"] == "로봇청소기"

    # ── 방 별칭 매핑 ───────────────────────────────────

    def test_room_alias_거실(self):
        result = control_smart_home.invoke({
            "device": "불",
            "action": "on",
            "room": "거실",
        })
        data = json.loads(result)
        assert data["room"] == "living_room"

    def test_room_alias_침실(self):
        result = control_smart_home.invoke({
            "device": "조명",
            "action": "off",
            "room": "침실",
        })
        data = json.loads(result)
        assert data["room"] == "bedroom"

    def test_no_room_defaults_to_all(self):
        result = control_smart_home.invoke({"device": "불", "action": "on"})
        data = json.loads(result)
        assert data["room"] == "all"

    # ── 동작 정규화 ────────────────────────────────────

    def test_action_켜줘_normalized_to_on(self):
        result = control_smart_home.invoke({"device": "불", "action": "켜줘"})
        data = json.loads(result)
        assert data["command"] == "on"

    def test_action_꺼줘_normalized_to_off(self):
        result = control_smart_home.invoke({"device": "에어컨", "action": "꺼줘"})
        data = json.loads(result)
        assert data["command"] == "off"

    def test_action_set_normalized(self):
        result = control_smart_home.invoke({
            "device": "에어컨",
            "action": "설정",
            "value": "24",
        })
        data = json.loads(result)
        assert data["command"] == "set"
        assert data["value"] == "24"

    # ── 메시지 생성 ────────────────────────────────────

    def test_message_켰어요(self):
        result = control_smart_home.invoke({
            "device": "불",
            "action": "켜줘",
            "room": "거실",
        })
        data = json.loads(result)
        assert "켰어요" in data["message"]
        assert "거실" in data["message"]

    def test_message_껐어요(self):
        result = control_smart_home.invoke({
            "device": "에어컨",
            "action": "꺼줘",
        })
        data = json.loads(result)
        assert "껐어요" in data["message"]

    def test_message_with_value(self):
        result = control_smart_home.invoke({
            "device": "에어컨",
            "action": "설정",
            "room": "거실",
            "value": "22도",
        })
        data = json.loads(result)
        assert "22도" in data["message"]

    def test_value_preserved_in_payload(self):
        result = control_smart_home.invoke({
            "device": "에어컨",
            "action": "set",
            "value": "25",
        })
        data = json.loads(result)
        assert data["value"] == "25"


# ── 별칭 사전 커버리지 ─────────────────────────────────────

class TestAliasCompleteness:

    def test_device_aliases_cover_major_devices(self):
        assert "불" in DEVICE_ALIASES
        assert "조명" in DEVICE_ALIASES
        assert "에어컨" in DEVICE_ALIASES
        assert "히터" in DEVICE_ALIASES
        assert "TV" in DEVICE_ALIASES
        assert "커튼" in DEVICE_ALIASES

    def test_room_aliases_cover_major_rooms(self):
        assert "거실" in ROOM_ALIASES
        assert "침실" in ROOM_ALIASES
        assert "주방" in ROOM_ALIASES
        assert "화장실" in ROOM_ALIASES
        assert "현관" in ROOM_ALIASES

    def test_device_alias_values_are_strings(self):
        for k, v in DEVICE_ALIASES.items():
            assert isinstance(v, str), f"{k} 값이 문자열이 아닙니다"

    def test_room_alias_values_are_strings(self):
        for k, v in ROOM_ALIASES.items():
            assert isinstance(v, str), f"{k} 값이 문자열이 아닙니다"

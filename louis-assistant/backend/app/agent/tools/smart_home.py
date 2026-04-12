"""
루이스 개인비서 - 스마트홈 도구
Google Home / SmartThings 연동 신호 반환.
실제 기기 제어는 OAuth 토큰이 필요하며, 여기서는 제어 신호를 생성합니다.
"""
import json
import logging

from langchain_core.tools import tool

log = logging.getLogger("louis.tools.smart_home")

DEVICE_ALIASES: dict[str, str] = {
    "불": "light", "조명": "light", "전등": "light",
    "에어컨": "air_conditioner", "에어콘": "air_conditioner",
    "히터": "heater", "난방": "heater",
    "TV": "tv", "티비": "tv",
    "커튼": "curtain", "블라인드": "curtain",
    "선풍기": "fan",
}

ROOM_ALIASES: dict[str, str] = {
    "거실": "living_room", "방": "bedroom", "침실": "bedroom",
    "화장실": "bathroom", "욕실": "bathroom",
    "주방": "kitchen", "부엌": "kitchen",
    "현관": "entrance",
}


@tool
def control_smart_home(device: str, action: str, room: str = "", value: str = "") -> str:
    """스마트홈 기기를 제어합니다.

    Args:
        device: 기기 이름 (예: '불', '에어컨', 'TV')
        action: 동작 ('on', 'off', 'set')
        room: 방 이름 (예: '거실', '침실'). 생략 시 전체.
        value: 설정 값 (예: 온도 '24', 밝기 '50%')

    Returns:
        제어 신호 JSON 또는 결과 메시지
    """
    device_key = DEVICE_ALIASES.get(device, device)
    room_key = ROOM_ALIASES.get(room, room) if room else "all"
    action_lower = action.lower()

    # 동작 정규화
    if action_lower in ("켜줘", "켜", "on", "켜줘요"):
        action_norm = "on"
    elif action_lower in ("꺼줘", "꺼", "off", "꺼줘요"):
        action_norm = "off"
    elif action_lower in ("set", "설정", "맞춰"):
        action_norm = "set"
    else:
        action_norm = action_lower

    payload = {
        "action": "SMART_HOME_CONTROL",
        "device": device_key,
        "room": room_key,
        "command": action_norm,
        "value": value,
    }

    room_str = f"{room} " if room else ""
    action_str = "켰어요" if action_norm == "on" else "껐어요" if action_norm == "off" else "설정했어요"
    msg = f"{room_str}{device} {action_str}."
    if value:
        msg = f"{room_str}{device}을 {value}로 {action_str}."

    payload["message"] = msg
    return json.dumps(payload, ensure_ascii=False)

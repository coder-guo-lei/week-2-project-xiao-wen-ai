"""用户偏好：规范化与注入 LLM 系统提示的文案片段。"""

from typing import Optional

DEFAULT_PREFERENCES = {
    "replyStyle": "concise",
    "ttsVoice": "female",
    "userNickname": "",
    "assistantTone": "friendly",
}

VALID_REPLY_STYLES = frozenset({"concise", "detailed"})
VALID_TTS_VOICES = frozenset({"female", "female_jiuxu"})
VALID_TONES = frozenset({"friendly", "professional"})


def normalize_preferences(raw) -> dict:
    """合并默认值，过滤非法字段。"""
    base = dict(DEFAULT_PREFERENCES)
    if not isinstance(raw, dict):
        return base
    if raw.get("replyStyle") in VALID_REPLY_STYLES:
        base["replyStyle"] = raw["replyStyle"]
    if raw.get("ttsVoice") in VALID_TTS_VOICES:
        base["ttsVoice"] = raw["ttsVoice"]
    if raw.get("assistantTone") in VALID_TONES:
        base["assistantTone"] = raw["assistantTone"]
    nick = raw.get("userNickname")
    if isinstance(nick, str):
        base["userNickname"] = nick.strip()[:32]
    return base


def build_preference_prompt_addon(prefs: Optional[dict]) -> str:
    """将用户偏好转为追加到 system prompt 的中文说明。"""
    p = normalize_preferences(prefs)
    lines = []

    if p["replyStyle"] == "detailed":
        lines.append("用户偏好：回答可更详细，适当分点展开，但仍保持口语化、适合朗读。")
    else:
        lines.append("用户偏好：回答务必简洁，通常控制在几句话内，除非用户明确要求长文。")

    if p["assistantTone"] == "professional":
        lines.append("语气偏好：偏专业、条理清晰，少用夸张语气词。")
    else:
        lines.append("语气偏好：亲切自然，像朋友聊天。")

    if p["userNickname"]:
        lines.append(f"用户希望被称呼为「{p['userNickname']}」，在合适时自然使用。")

    return "\n".join(lines)

"""
偏好设置 API（Flask Blueprint「pref」）。

提供：
  · GET  /api/preferences  — 获取当前用户偏好（含默认值）
  · PUT  /api/preferences  — 批量更新偏好（仅允许 DEFAULT_KEYS 中的键）
"""
import logging

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from models.user import get_db

logger = logging.getLogger(__name__)

pref_bp = Blueprint("pref", __name__, url_prefix="/api")

# 允许的偏好键及其默认值
DEFAULT_PREFERENCES = {
    "display_name": "",
    "role": "",
    "interests": "",
    "language_style": "casual",
    "response_length": "medium",
    "tts_voice": "default",
}


def load_user_preferences(user_id: int) -> dict:
    """从 user_preferences 表加载指定用户偏好的函数（供 task_parser 等复用）。"""
    conn = get_db()
    rows = conn.execute(
        "SELECT pref_key, pref_value FROM user_preferences WHERE user_id = ?",
        (user_id,),
    ).fetchall()
    conn.close()
    prefs = dict(DEFAULT_PREFERENCES)
    for row in rows:
        if row["pref_key"] in DEFAULT_PREFERENCES:
            prefs[row["pref_key"]] = row["pref_value"]
    return prefs


def build_personalized_system_prompt(prefs: dict) -> str:
    """根据偏好字典生成可追加到 system prompt 的偏好片段。"""
    lines = []
    if prefs.get("display_name"):
        lines.append(f"- 用户称呼：{prefs['display_name']}")
    if prefs.get("role"):
        lines.append(f"- 用户职业/角色：{prefs['role']}，请据此调整回复的专业程度和术语")
    if prefs.get("interests"):
        lines.append(f"- 用户兴趣领域：{prefs['interests']}，可在合适时引用")
    style = prefs.get("language_style", "")
    if style == "casual":
        lines.append("- 请用轻松随意的口语化语气回复")
    elif style == "formal":
        lines.append("- 请用正式专业的语气回复")
    elif style == "concise":
        lines.append("- 请用简洁精炼的语气回复，尽量短")

    rlen = prefs.get("response_length", "")
    if rlen == "short":
        lines.append("- 请始终保持回复简短（1-2句话即可）")
    elif rlen == "long":
        lines.append("- 请提供详细、深入的回复，充分展开说明")

    if not lines:
        return ""
    return "\n\n## 用户偏好（来自个人设置）\n" + "\n".join(lines)


@pref_bp.route("/preferences", methods=["GET"])
@jwt_required()
def get_preferences():
    user_id = int(get_jwt_identity())
    prefs = load_user_preferences(user_id)
    return jsonify({"preferences": prefs})


@pref_bp.route("/preferences", methods=["PUT"])
@jwt_required()
def update_preferences():
    user_id = int(get_jwt_identity())
    data = request.get_json(silent=True) or {}
    conn = get_db()
    updated = 0
    for key, value in data.items():
        if key not in DEFAULT_PREFERENCES:
            continue
        conn.execute(
            """INSERT INTO user_preferences (user_id, pref_key, pref_value)
               VALUES (?, ?, ?)
               ON CONFLICT(user_id, pref_key)
               DO UPDATE SET pref_value = ?, updated_at = datetime('now','localtime')""",
            (user_id, key, str(value), str(value)),
        )
        updated += 1
    conn.commit()
    conn.close()
    logger.info("用户 %d 更新了 %d 项偏好", user_id, updated)
    return jsonify({"status": "ok", "updated": updated})

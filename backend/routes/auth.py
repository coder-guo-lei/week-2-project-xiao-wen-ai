"""
认证路由：用户注册、登录、获取当前用户信息。

所有 /api/auth/* 为公开接口，不要求 JWT。
"""

import re
import logging

from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token,
    jwt_required,
    get_jwt_identity,
)
from werkzeug.security import generate_password_hash, check_password_hash
from models.user import UserModel

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")
logger = logging.getLogger(__name__)

# ── 参数校验 ──────────────────────────────────────────────

_USERNAME_RE = re.compile(r"^[a-zA-Z0-9_\u4e00-\u9fff]{3,20}$")


def _validate_credentials(username: str, password: str):
    """校验用户名和密码格式，返回 (ok, error_message)。"""
    if not username or not password:
        return False, "用户名和密码不能为空"
    if not _USERNAME_RE.match(username):
        return False, "用户名 3-20 个字符，仅支持字母/数字/下划线/中文"
    if len(password) < 6:
        return False, "密码至少 6 位"
    return True, ""


# ── 路由 ──────────────────────────────────────────────────


@auth_bp.route("/register", methods=["POST"])
def register():
    """
    注册新用户。
    Body: { username, password, displayName? }
    成功返回 201: { token, user: { id, username, displayName } }
    """
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password", "")
    display_name = (data.get("displayName") or username).strip()

    ok, err = _validate_credentials(username, password)
    if not ok:
        return jsonify({"error": err}), 400

    # 检查用户名唯一性
    if UserModel.get_by_username(username):
        return jsonify({"error": "用户名已存在"}), 409

    try:
        hashed = generate_password_hash(password)
        user_id = UserModel.create(username, hashed, display_name)
        token = create_access_token(identity=str(user_id))

        logger.info("用户注册成功: %s (id=%d)", username, user_id)
        return jsonify({
            "token": token,
            "user": {
                "id": user_id,
                "username": username,
                "displayName": display_name,
            },
        }), 201
    except Exception as e:
        logger.error("注册失败: %s", e)
        return jsonify({"error": "注册失败，请稍后重试"}), 500


@auth_bp.route("/login", methods=["POST"])
def login():
    """
    用户登录。
    Body: { username, password }
    成功返回 200: { token, user: { id, username, displayName } }
    """
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password", "")

    if not username or not password:
        return jsonify({"error": "用户名和密码不能为空"}), 400

    user = UserModel.get_by_username(username)
    if not user or not check_password_hash(user["password"], password):
        return jsonify({"error": "用户名或密码错误"}), 401

    token = create_access_token(identity=str(user["id"]))

    logger.info("用户登录: %s (id=%d)", username, user["id"])
    return jsonify({
        "token": token,
        "user": {
            "id": user["id"],
            "username": user["username"],
            "displayName": user.get("display_name", ""),
        },
    })


@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def get_me():
    """
    获取当前登录用户信息（前端初始化时验证 token）。
    Header: Authorization: Bearer <token>
    """
    user_id = int(get_jwt_identity())
    user = UserModel.get_by_id(user_id)
    if not user:
        return jsonify({"error": "用户不存在"}), 404

    return jsonify({
        "user": {
            "id": user["id"],
            "username": user["username"],
            "displayName": user.get("display_name", ""),
            "role": user.get("role", ""),
            "avatarUrl": user.get("avatar_url", ""),
        },
    })

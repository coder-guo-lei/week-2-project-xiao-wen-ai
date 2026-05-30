"""
用户日志 API — 按 user_id 隔离，支持分页和按会话筛选。
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models.user import get_db

logs_bp = Blueprint("logs_bp", __name__, url_prefix="/api/logs")


@logs_bp.route("", methods=["GET"])
@jwt_required()
def get_logs():
    """获取当前用户的对话日志，支持分页和按会话筛选。"""
    user_id = int(get_jwt_identity())
    session_id = request.args.get("sessionId")
    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("pageSize", 50))
    offset = (page - 1) * page_size

    conn = get_db()

    # 查询日志
    if session_id:
        rows = conn.execute(
            """SELECT * FROM user_logs
               WHERE user_id = ? AND session_id = ?
               ORDER BY created_at DESC
               LIMIT ? OFFSET ?""",
            (user_id, session_id, page_size, offset),
        ).fetchall()
        total = conn.execute(
            "SELECT COUNT(*) FROM user_logs WHERE user_id = ? AND session_id = ?",
            (user_id, session_id),
        ).fetchone()[0]
    else:
        rows = conn.execute(
            """SELECT * FROM user_logs
               WHERE user_id = ?
               ORDER BY created_at DESC
               LIMIT ? OFFSET ?""",
            (user_id, page_size, offset),
        ).fetchall()
        total = conn.execute(
            "SELECT COUNT(*) FROM user_logs WHERE user_id = ?", (user_id,)
        ).fetchone()[0]

    # 会话列表（按最后活跃时间倒序）
    sessions = conn.execute(
        """SELECT DISTINCT session_id,
                  MIN(created_at) AS first_at,
                  MAX(created_at) AS last_at,
                  COUNT(*)        AS turn_count
           FROM user_logs
           WHERE user_id = ?
           GROUP BY session_id
           ORDER BY last_at DESC""",
        (user_id,),
    ).fetchall()

    conn.close()

    return jsonify(
        {
            "logs": [dict(r) for r in rows],
            "sessions": [dict(s) for s in sessions],
            "total": total,
            "page": page,
            "pageSize": page_size,
        }
    )

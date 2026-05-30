"""
数据库模型层：用户认证、偏好设置、对话日志。

使用 SQLite 存储，通过 get_db() 获取连接。
所有表通过 init_db() 统一创建，幂等可重复执行。
"""

import os
import sqlite3

# 数据库文件路径：backend/xiaowen.db
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "xiaowen.db")


def get_db():
    """获取数据库连接，自动启用 WAL 模式和外键约束。调用方负责 close()。"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """初始化所有数据库表（幂等：IF NOT EXISTS）。在 app.py 启动时调用。"""
    conn = get_db()
    conn.executescript("""
        -- ====== 用户表 ======
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            username      TEXT    UNIQUE NOT NULL,
            password      TEXT    NOT NULL,
            display_name  TEXT    DEFAULT '',
            avatar_url    TEXT    DEFAULT '',
            role          TEXT    DEFAULT '',
            created_at    TEXT    DEFAULT (datetime('now', 'localtime')),
            updated_at    TEXT    DEFAULT (datetime('now', 'localtime'))
        );

        -- ====== 用户偏好表 ======
        CREATE TABLE IF NOT EXISTS user_preferences (
            user_id     INTEGER NOT NULL,
            pref_key    TEXT    NOT NULL,
            pref_value  TEXT    NOT NULL,
            updated_at  TEXT    DEFAULT (datetime('now', 'localtime')),
            PRIMARY KEY (user_id, pref_key),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        -- ====== 用户日志表 ======
        CREATE TABLE IF NOT EXISTS user_logs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL,
            session_id  TEXT    NOT NULL,
            role        TEXT    NOT NULL,
            content     TEXT    NOT NULL,
            intent      TEXT    DEFAULT '',
            metadata    TEXT    DEFAULT '{}',
            created_at  TEXT    DEFAULT (datetime('now', 'localtime')),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_logs_user_id
            ON user_logs(user_id);
        CREATE INDEX IF NOT EXISTS idx_logs_user_session
            ON user_logs(user_id, session_id);
        CREATE INDEX IF NOT EXISTS idx_logs_created
            ON user_logs(user_id, created_at);
    """)
    conn.commit()
    conn.close()


# ── 日志写入工具 ──────────────────────────────────────────────


def save_log(user_id: int, session_id: str, role: str, content: str, intent: str = ""):
    """向 user_logs 表写入一条对话日志。"""
    conn = get_db()
    conn.execute(
        """INSERT INTO user_logs (user_id, session_id, role, content, intent)
           VALUES (?, ?, ?, ?, ?)""",
        (user_id, session_id, role, content, intent or ""),
    )
    conn.commit()
    conn.close()


class UserModel:
    """用户数据访问对象。"""

    @staticmethod
    def get_by_id(user_id: int):
        conn = get_db()
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        conn.close()
        return dict(row) if row else None

    @staticmethod
    def get_by_username(username: str):
        conn = get_db()
        row = conn.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()
        conn.close()
        return dict(row) if row else None

    @staticmethod
    def create(username: str, password_hash: str, display_name: str = ""):
        conn = get_db()
        cursor = conn.execute(
            "INSERT INTO users (username, password, display_name) VALUES (?, ?, ?)",
            (username, password_hash, display_name),
        )
        user_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return user_id

    @staticmethod
    def update_profile(user_id: int, **kwargs):
        """更新用户资料，kwargs 仅允许 display_name, role, avatar_url。"""
        allowed = {"display_name", "role", "avatar_url"}
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            return
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [user_id]
        conn = get_db()
        conn.execute(
            f"UPDATE users SET {set_clause}, updated_at = datetime('now','localtime') WHERE id = ?",
            values,
        )
        conn.commit()
        conn.close()

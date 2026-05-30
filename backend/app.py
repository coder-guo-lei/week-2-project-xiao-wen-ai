"""Flask 后端「小文」：只做应用装配与启动，业务在 routes/ 与 logic/。"""

import logging
import os

from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager

import config  # noqa: F401
from config import AMAP_KEY, DASHSCOPE_API_KEY, DEEPSEEK_API_KEY, DEEPSEEK_CHAT_MODEL
from logic.task_parser import primary_chat_model_label
from models.user import init_db
from routes.api import api_bp
from routes.auth import auth_bp
from routes.logs import logs_bp
from routes.preferences import pref_bp

logger = logging.getLogger(__name__)

app = Flask(__name__)

# ── JWT 配置 ──────────────────────────────────────────────
app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "xiaowen-dev-secret-change-in-production")
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = 86400  # 24 小时
jwt = JWTManager(app)

# ── 数据库初始化 ──────────────────────────────────────────
init_db()

# ── CORS ──────────────────────────────────────────────────
CORS(
    app,
    expose_headers=["Content-Type", "X-TTS-VCN", "X-TTS-Cache", "X-TTS-Engine"],
)

# ── 注册蓝图 ──────────────────────────────────────────────
app.register_blueprint(auth_bp)  # /api/auth/* 公开
app.register_blueprint(api_bp)   # /api/* 业务接口（需认证）
app.register_blueprint(logs_bp)  # /api/logs 日志查询
app.register_blueprint(pref_bp)  # /api/preferences 偏好设置

# ── 启动日志 ──────────────────────────────────────────────
logger.info(
    "LLM：DashScope=%s | DeepSeek=%s | 对话模型展示=%s | 高德=%s | JWT=已启用",
    "已配置" if DASHSCOPE_API_KEY else "未配置",
    "已配置(%s)" % DEEPSEEK_CHAT_MODEL if DEEPSEEK_API_KEY else "未配置",
    primary_chat_model_label(),
    "已配置 AMAP_KEY" if AMAP_KEY else "未配置（天气为占位数据）",
)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5001, debug=True)

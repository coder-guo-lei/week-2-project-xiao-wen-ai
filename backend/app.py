"""Flask 后端「小文」：只做应用装配与启动，业务在 routes/ 与 logic/。"""

import logging  # 标准库：分级日志

from flask import Flask  # Web 框架：WSGI 应用对象
from flask_cors import CORS  # 跨域：允许浏览器前端（如 Vite 开发端口）调用本机 API（默认 5001）

import config  # noqa: F401 — 副作用：执行 config 时加载 .env 并写入 os.environ
from config import AMAP_KEY, DASHSCOPE_API_KEY, DEEPSEEK_API_KEY, DEEPSEEK_CHAT_MODEL  # 仅用于启动时打日志
from logic.task_parser import primary_chat_model_label  # 人类可读的「当前对话模型」摘要字符串
from routes.api import api_bp  # 所有 /api/* 路由集中在此 Blueprint
from sync_hub import sock  # 多端日志 WebSocket：/ws/sync

logger = logging.getLogger(__name__)  # 本模块日志器名称 = __name__

app = Flask(__name__)  # 创建应用；__name__ 用于模板/静态资源相对路径解析
CORS(
    app,
    # 允许前端 JS 读取的响应头（TTS 二进制流附带发音人、缓存命中等元信息）
    expose_headers=["Content-Type", "X-TTS-VCN", "X-TTS-Cache", "X-TTS-Engine"],
)
app.register_blueprint(api_bp)  # 挂载路由：实际路径为 api_bp 内各 @route 声明的路径
sock.init_app(app)

logger.info(
    "LLM：DashScope=%s | DeepSeek=%s | 对话模型展示=%s | 高德=%s",
    "已配置" if DASHSCOPE_API_KEY else "未配置",
    "已配置(%s)" % DEEPSEEK_CHAT_MODEL if DEEPSEEK_API_KEY else "未配置",
    primary_chat_model_label(),
    "已配置 AMAP_KEY" if AMAP_KEY else "未配置（天气为占位数据）",
)


if __name__ == "__main__":
    # 仅「直接 python app.py」时使用；生产环境请用 gunicorn 等托管并关闭 debug
    # 手机/模拟器联调：set BACKEND_HOST=0.0.0.0（允许局域网访问）
    import os
    host = os.environ.get("BACKEND_HOST", "127.0.0.1")
    app.run(host=host, port=5001, debug=True)

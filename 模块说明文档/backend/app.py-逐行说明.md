# `backend/app.py` — 逐行说明

源文件约 35 行，职责是**装配 Flask 应用并启动**；业务逻辑不在此文件。

| 行号 | 代码含义 |
|------|----------|
| 1 | 模块文档字符串：说明本文件只做应用装配与启动，业务在 `routes/` 与 `logic/`。 |
| 3 | `import logging`：使用标准库分级日志。 |
| 5 | `from flask import Flask`：引入 WSGI 应用类。 |
| 6 | `from flask_cors import CORS`：跨域中间件，允许前端不同端口访问 API。 |
| 8 | `import config` 且 `noqa: F401`：执行 `config` 模块的副作用（加载 `.env` 到 `os.environ`），避免静态分析报未使用。 |
| 9 | 从 `config` 再导入若干常量，仅用于下面 `logger.info` 的占位提示（是否已配置密钥等）。 |
| 10 | 从 `logic.task_parser` 导入 `primary_chat_model_label()`：人类可读的当前对话模型摘要。 |
| 11 | 从 `routes.api` 导入 `api_bp`：挂载所有 `/api/*` 的 Blueprint。 |
| 13 | 取本模块日志器 `logging.getLogger(__name__)`。 |
| 15 | `app = Flask(__name__)`：创建应用实例。 |
| 16–20 | `CORS(app, expose_headers=[...])`：除允许跨域外，显式暴露 TTS 响应自定义头（发音人、缓存命中、引擎类型），供前端读取。 |
| 21 | `app.register_blueprint(api_bp)`：注册路由蓝图。 |
| 23–29 | `logger.info(...)`：启动时打印 LLM（百炼/DeepSeek）、对话模型展示名、高德 Key 是否配置。 |
| 32–34 | `if __name__ == "__main__":`：仅直接 `python app.py` 时以 `127.0.0.1:5001`、`debug=True` 启动；生产应用 gunicorn 等托管。 |

## 与其它模块的关系

- **不**应在本文件写业务分支；新增 API 在 `routes/api.py` 增加路由并调用 `logic`。
- 端口 **5001** 与前端 Vite 代理目标一致（见前端 `vite.config.js` 文档）。

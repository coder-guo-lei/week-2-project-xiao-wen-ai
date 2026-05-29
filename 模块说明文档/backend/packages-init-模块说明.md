# 后端包 `__init__.py` — 模块说明

## `backend/logic/__init__.py`

- **内容**：一行文档字符串「指令解析与世界模拟等核心业务逻辑。」
- **作用**：将 `logic` 声明为 Python 包，便于 `from logic.task_parser import ...`。

## `backend/routes/__init__.py`

- **内容**：「HTTP 路由（Blueprint）。」
- **作用**：包标识；实际路由在 `routes/api.py`。

## `backend/services/__init__.py`

- **内容**：「业务服务子包（讯飞 TTS 等）。」
- **作用**：包标识；具体实现在 `xfyun_tts.py`、`xfyun_iat.py`。

这三份文件**无**可执行逻辑，仅文档与包结构需要。

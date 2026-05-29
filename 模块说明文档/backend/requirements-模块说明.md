# `backend/requirements.txt` — 逐行说明

| 行号 | 包 | 用途 |
|------|-----|------|
| 1 | `Flask==2.3.3` | Web 框架，提供 `Flask`、`request`、`jsonify`、`Response` 等。 |
| 2 | `flask-cors==4.0.0` | 跨域支持，与 `app.py` 中 `CORS(app, ...)` 配合。 |
| 3 | `requests==2.31.0` | HTTP 客户端：高德、百炼、网易云搜索等。 |
| 4 | `python-dotenv==1.0.1` | `load_dotenv` 读取 `backend/.env`。 |
| 5 | `openpyxl==3.1.5` | 图表上传分支解析 `.xlsx`（见 `parse_chart_file`）。 |
| 6 | `zhdate==0.1` | 农历相关（`task_parser` 中 `lunar_year_anchor_facts_for_llm` 等）。 |
| 7 | `websockets>=12.0` | 讯飞 TTS / IAT 的 WebSocket 异步客户端。 |

可选：`task_parser` 在部分环境尝试 `zoneinfo`（标准库）；`zhdate` 缺失时农历功能降级。

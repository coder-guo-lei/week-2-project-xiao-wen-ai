# 后端（backend）总览

## 技术栈

- **运行时**：Python 3，建议与 `requirements.txt` 中版本兼容的环境。
- **Web**：Flask 2.x，`flask-cors` 解决浏览器跨域。
- **对外能力**：阿里云 DashScope（对话/文生图/VL）、DeepSeek（可选对话）、高德地图（天气/逆地理/周边 POI）、讯飞开放平台（TTS、IAT 听写）。

## 目录与模块对应

| 文件/目录 | 模块职责 |
|-----------|----------|
| `app.py` | 创建 `Flask` 实例、注册 CORS、挂载 `api` Blueprint、启动时打日志。 |
| `config.py` | 读取 `.env`、常量（超时、模型名、TTS 参数）、Windows 下应用路径解析、世界模拟词表。 |
| `session.py` | 进程内全局：`WORLD_STATE`、`CHAT_HISTORY`、`KNOWLEDGE_SNIPPETS`。 |
| `routes/api.py` | 所有 `/api/*` 路由：参数校验 → 调用 `logic`/`services` → JSON 或音频流。 |
| `logic/task_parser.py` | 自然语言指令路由、天气/音乐/图表/世界/应用启动/LLM 等全部业务分支（含与用户白名单合并的 `launch_local_app`）。 |
| `logic/user_apps.py` | 用户自定义可启动应用：读写 `data/user_app_launchers.json`、`merge_launchers`、Windows 下子进程弹窗选 `.exe`。 |
| `scripts/pick_exe_dialog.py` | 由 `user_apps` 子进程执行：tkinter 文件对话框，路径输出到 stdout。 |
| `data/` | 运行时数据目录；含 `user_app_launchers.json`（用户白名单，首次添加时生成）。 |
| `services/xfyun_tts.py` | 讯飞在线 TTS / 超拟人 WebSocket、文本清洗、缓存键、PCM→WAV。 |
| `services/xfyun_iat.py` | WAV→16k PCM、讯飞听写 WebSocket、并行收发帧。 |
| `logic/__init__.py`、`routes/__init__.py`、`services/__init__.py` | 包标识与简短说明字符串。 |
| `requirements.txt` | 固定版本依赖列表。 |

## 典型请求路径

1. 用户在前端输入 → `POST /api/send-task` → `parse_command()` → 返回 `type`/`msg`/扩展字段。
2. 朗读 → `POST /api/tts` → `async_xfyun_tts_audio()` → `audio/wav` 或 `audio/mpeg`。
3. 上传 WAV 听写 → `POST /api/speech-to-text` → `transcribe_wav_bytes()`。
4. 用户应用白名单 → `GET/POST/DELETE /api/user-apps`、`POST /api/user-apps/pick`（见 [logic-user_apps-模块说明.md](./logic-user_apps-模块说明.md)）。

更细的逐文件说明见同目录下各 `*.md` 文件。

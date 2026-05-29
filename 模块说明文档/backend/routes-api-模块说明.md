# `backend/routes/api.py` — 模块说明

## 文件角色

- Flask **Blueprint** `api_bp`，路由路径均带 `/api` 前缀。
- **原则**（见文件头注释）：只做参数提取、调用 `logic`/`services`、组装 HTTP 响应；复杂意图分支在 `logic.task_parser.parse_command`。

## 导入（约 1–55 行）

| 块 | 含义 |
|----|------|
| `asyncio` | TTS 视图中 `asyncio.run(async_xfyun_tts_audio(...))` 调用异步合成。 |
| `logging`、`os`、`Blueprint`、`Response`、`jsonify`、`request` | 日志与 Flask；`os.name` 用于 `capabilities` / `user_apps_pick_exe`。 |
| `config` | TTS 字符上限、讯飞密钥、语速音量、磁盘缓存、`xfyun_vcn_ok`。 |
| `logic.task_parser` | 图表、图片、翻译、历史规范化、主指令解析、工作流包装等。 |
| `logic.user_apps` | `add_user_app`、`remove_user_app`、`user_apps_public_list`、`pick_exe_windows_blocking`：用户自定义可启动应用白名单。 |
| `services.xfyun_iat` | `transcribe_wav_bytes`。 |
| `services.xfyun_tts` | 异步合成、文本清洗、缓存路径、MP3 判定。 |
| `websockets` | 可选依赖；缺失时 TTS 返回 503 提示安装。 |

## 路由一览

### `POST /api/translate-selection`（`translate_selection`）

- Body：`{ text, targetLang }`（`zh`/`en`）。
- 调 `translate_selected_text`；长度截断 2000。

### `GET /api/image-status/<task_id>`（`image_status`）

- 文生图异步轮询：`dashscope_poll_image`。

### `POST /api/analyze-image`（`analyze_image_upload`）

- `multipart`：`image`、`question`、`kind`。
- 返回 `reply`、`workflow`、`mode`/`modeLabel` 等。

### `POST /api/tts`（`tts_xfyun`）

- JSON：`text`、`voice`、`speed?`、`volume?`。
- 校验 `websockets` 与讯飞三要素；映射 `voice` 到 vcn；`plain_text_for_tts`；可选磁盘缓存命中直接返回 `Response` 字节流。
- 否则 `asyncio.run(async_xfyun_tts_audio(...))`，写缓存后返回音频；捕获讯飞错误码 `11200` 时改写友好文案。

### `POST /api/generate-chart`（`generate_chart_upload`）

- `multipart`：`file?`、`task`。
- 有文件则 `parse_chart_file`，点数不足则 `generate_demo_chart_points`；无文件则 `resolve_chart_points_from_task`。
- `build_chart_payload` + `with_workflow` 返回 JSON。

### `POST /api/send-task`（`send_task`）

- JSON：`task`、`history?`、`location?`（浏览器 WGS84 经纬度对象）。
- `normalize_chat_history` → `parse_command`；若 `type==chat` 且非 `resetUI` 则 `remember_chat_turn`。
- 将 `parse_command` 返回字典中的键**白名单**拷贝到响应（避免泄露内部字段）。

### `GET /api/capabilities`（`capabilities`）

- 返回 `code: 200`。
- **`xfyunAsr`**（bool）：与 TTS 共用讯飞三要素是否齐全，供前端是否展示讯飞听写相关 UI。
- **`userExePick`**（bool）：**`os.name == "nt"`** 时为 `true`，表示后端支持 `POST /api/user-apps/pick` 弹出 Windows 原生选 `.exe` 对话框；非 Windows 为 `false`，前端可隐藏「浏览电脑添加应用」按钮。

### 用户应用白名单 API（`logic.user_apps`）

以下路由与 **`backend/logic/user_apps.py`**、**`backend/data/user_app_launchers.json`** 对应；完整字段与行为见 [logic-user_apps-模块说明.md](./logic-user_apps-模块说明.md)。

#### `GET /api/user-apps`（`user_apps_get`）

- **作用**：列出当前用户已添加的白名单项。
- **成功响应**：`{ "code": 200, "apps": [ { "name": "显示名", "path": "绝对路径无 exe 前缀" }, ... ] }`（`path` 已去掉存储时的 `exe:` 前缀，便于前端 `title` 展示）。
- **失败**：`500`，`apps` 为空数组，可选 `error` 字符串。

#### `POST /api/user-apps`（`user_apps_post`）

- **Body（JSON）**：`{ "name": "显示名称", "path": "绝对路径" }`。`path` 通常来自上一条 `pick` 接口返回。
- **逻辑**：调用 `add_user_app(name, path)`：校验 exe 存在、Windows 后缀、名称字符与长度、不与内置 `APP_LAUNCHERS` 重名、不与已有用户项重名（均忽略大小写）；通过后写入 JSON。
- **成功**：`200`，`{ "code": 200, "message": "已添加…可以说：打开某某" }`。
- **业务错误**：`400`，`{ "code": 400, "message": "错误原因" }`。
- **异常**：`500`。

#### `DELETE /api/user-apps`（`user_apps_delete`）

- **Query**：`name` — 要移除的显示名称（大小写不敏感匹配 JSON 中的键）。
- **逻辑**：`remove_user_app(name)`，仅删除用户 JSON 中的项，**不能**删除内置应用。
- **响应**：与 POST 类似，`200` / `400` / `500` + `message`。

#### `POST /api/user-apps/pick`（`user_apps_pick_exe`）

- **作用**：在 **Windows** 上阻塞调用 `pick_exe_windows_blocking()`，直到用户在子进程 tkinter 对话框中选择文件或取消。
- **非 Windows**：`501`，`path`/`suggestedName` 为 `null`，`message` 说明仅支持本机 Windows 后端。
- **未选择或无法弹窗**（无 tkinter、无桌面等）：`200`，**`code: 204`**，`path`/`suggestedName` 为 `null`，`message` 说明原因（与「成功」区分靠 `code` 字段）。
- **成功**：`200`，**`code: 200`**，`path` 为规范化绝对路径，`suggestedName` 为 `os.path.splitext(os.path.basename(path))[0]`，供前端默认填入名称输入框。
- **异常**：`500`。

**注意**：`pick` 请求在处理期间会**长时间占用**一个 Flask worker 线程，直至对话框关闭；本机开发单用户可接受。

### `POST /api/speech-to-text`（`speech_to_text`）

- `multipart` 字段 `audio`：读取字节，大小与 RIFF/WAV 头校验。
- `transcribe_wav_bytes` → `{ code, text, error? }`。

## 扩展新 API 时

1. 在 `api.py` 增加 `@api_bp.route`。
2. 业务放 `task_parser` 或新 `logic` 模块；保持视图层薄。

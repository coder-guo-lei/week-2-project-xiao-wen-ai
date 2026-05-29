# `src/App.jsx` — 模块说明

> 约 **690+ 行**（随功能迭代略有增减）。根组件负责：**布局编排**、**全局状态**、**浏览器定位**、**与后端 `/api/*` 通信**、**根据响应 `type` 切换左栏内容**。文件顶部已有较完整块注释（约 1–12 行），此处补充结构化索引。

---

## 1. 导入（约 13–33 行）

- React：`useState`、`useCallback`、`useEffect`、`useRef`。
- 样式：`./App.css`。
- 子组件：`CommandInput`、`LogPanel`、`MusicPlayer`、`WeatherCard`、`ChatPanel`、`ImagePreview`、`DefaultPanel`、`SelectionToolbar`、`ModeBar`、`WorkflowPanel`、`ImageAnalyzer`、`FaceWellnessCamera`、`ChartPanel`、`XiaowenBot`。
- Hooks：`useMusicPlayer`、`useVoiceRecognition`。
- `apiUrl` from `./apiBase`。

---

## 2. 模块级常量（约 35–43 行）

| 常量 | 含义 |
|------|------|
| `COMMAND_HISTORY_KEY` / `CHAT_HISTORY_KEY` | `localStorage` 键名。 |
| `MAX_COMMAND_HISTORY` / `MAX_CHAT_HISTORY` | 列表长度上限。 |
| `IMAGE_POLL_MAX_MS` | 文生图轮询最长等待（略大于后端默认任务超时）。 |
| `LAST_LOC_KEY` | `sessionStorage` 中缓存上次定位 JSON 的键。 |

---

## 3. 定位辅助函数（约 46–98 行）

| 函数 | 作用 |
|------|------|
| `readCachedClientLocation(maxAgeMs)` | 从 `sessionStorage` 读 `{lat,lng,accuracy,t}`，过期或格式错误返回 `null`。 |
| `writeCachedClientLocation(loc)` | 写入带时间戳的坐标。 |
| `fetchClientLocation(timeoutMs)` | `navigator.geolocation.getCurrentPosition`；超时/失败用缓存兜底；成功则写缓存。 |

供 `autoSendTask` 拼到 `POST /api/send-task` 的 `location` 字段。

---

## 4. `App()` 内状态分组（约 100–140 行）

- **输入与日志**：`task`、`logList`。
- **左栏展示**：`contentType`（`default`/`chat`/`weather`/`music`/`image`/`chart` 等）、`chatReply`、`chatHistory`（持久化）、`weatherData`、`imageUrl`/`imagePrompt`/`imageGenerating`/`imageElapsed`。
- **发送锁**：`isSending`。
- **模式与世界**：`mode`、`modeLabel`、`worldState`、`quickActions`、`workflowSteps`。
- **图表**：`chartData`、`isGeneratingChart`。
- **指令历史**：`commandHistory`（持久化）。
- **Refs**：轮询定时器、`feedbackRef` 用于滚动到反馈区。
- **用户应用白名单（约 142–148 行）**：
  - `userAppList`：`{ name, path }[]`，来自 `GET /api/user-apps`。
  - `userExePickSupported`：是否展示「浏览添加」区块；由 `GET /api/capabilities` 的 **`userExePick`**（后端 `os.name == "nt"`）更新，首屏默认为 `true` 直至拉取完成。
  - `pickBrowseBusy`：`POST /api/user-apps/pick` 等待期间为 `true`，禁用按钮防重复点。
  - `addAppDraft`：`null` 或 `{ path, suggestedName }`，选完 exe 后弹出 `DefaultPanel` 确认层。
  - `addAppNameInput`：确认层内受控字符串，与后端显示名 24 字上限一致。

---

## 4.1 用户白名单：副作用与刷新（约 278–294 行）

| 符号 | 说明 |
|------|------|
| `refreshUserApps` | `useCallback`：`fetch(apiUrl('/api/user-apps'))`，`code===200` 且 `apps` 为数组则 `setUserAppList`。 |
| `useEffect`（依赖 `[refreshUserApps]`） | 挂载时：先 `refreshUserApps()`，再 `fetch(apiUrl('/api/capabilities'))`；若响应里 **`userExePick` 为 boolean** 则 `setUserExePickSupported`，用于非 Windows 后端隐藏浏览按钮。 |

---

## 5. 重要回调（约 141–398 行及白名单相关约 494–564 行）

| 名称 | 职责摘要 |
|------|----------|
| `addLog` / `clearLogList` | 右侧日志追加/清空。 |
| `rememberCommand` | 指令历史去重置顶 + `localStorage`。 |
| `updateChatHistory` / `clearChatHistory` | 多轮对话与告别重置。 |
| `resetAllContent` | 清天气/图/聊/图表/音乐定时器等（不切 `contentType`）。 |
| `returnToInitialView` | 调用 `resetAllContent` 后回到 `default` 与初始 `mode`。 |
| `startImagePolling(taskId)` | 每秒递增已等待时间 + 每 1.5s 请求 `/api/image-status/:id` 直到成功/失败/超时。 |
| `autoSendTask(cmdText)` | **核心**：定位 → `POST /api/send-task` → 按 `data.type`/`extraData`/`resetUI` 等分支设置状态；错误时提示后端未连接。 |
| `handleDefaultExample` | 默认面板示例：肤质入口滚动或 `autoSendTask`。 |
| `generateChartFromFile` | `POST /api/generate-chart` multipart。 |
| `handleCancelAddApp` | `setAddAppDraft(null)`、`setAddAppNameInput('')`，关闭确认层。 |
| `handleBrowsePickExe` | `setPickBrowseBusy(true)` → `POST /api/user-apps/pick` → 若 `code===200` 且 `path` 存在则设置 draft 与默认名称；`501`/`204` 等通过 `addLog` 提示；`finally` 结束 busy。 |
| `handleConfirmAddApp` | 校验名称非空 → `POST /api/user-apps` body `{ name, path }` → 成功则清空 draft、**`refreshUserApps()`**。 |
| `handleRemoveUserApp(name)` | `DELETE` + query `name` → 成功则 **`refreshUserApps()`**。 |

`useVoiceRecognition`（约 414–423 行，行号随上文插入可能下移）：`onResult` 里 `setTask`、`clearLogList`、`autoSendTask`；当前 `useXfyunAsr: false` 固定 Web Speech。

---

## 6. JSX 布局（约 450 行至文件末尾，行号随版本变化）

- 左侧：标题、`ModeBar`、`WorkflowPanel`、按 `contentType` 条件渲染各面板 + `CommandInput` + 双入口（图片分析/肤质相机）。
- **`DefaultPanel`**（`contentType === 'default'` 时）：除 `isCmdActive` / `isWakeActive` / `onExampleClick` 外，传入 **`userExePickSupported`、`pickBrowseBusy`、`userAppList`、`addAppDraft`、`addAppNameInput`、`onAddAppNameChange`、`onBrowsePickExe`、`onCancelAddApp`、`onConfirmAddApp`、`onRemoveUserApp`**，与 [DefaultPanel-模块说明.md](./DefaultPanel-模块说明.md) 一致。
- 右侧：`LogPanel`、`MusicPlayer`（`music` Hook）、`XiaowenBot`。
- `SelectionToolbar` 划词翻译等。

---

## 7. 与后端契约

- 主路径：`/api/send-task` 的 JSON 与 `routes/api.py` 白名单字段一致。
- 图表上传：`/api/generate-chart`。
- **用户应用白名单**：`/api/user-apps`（GET/POST/DELETE）、`/api/user-apps/pick`（POST）；能力位 `/api/capabilities` 的 **`userExePick`**。
- 不在本文件：`/api/tts` 由 `ChatPanel`/`SelectionToolbar` 经 `utils/xfyunTts.js` 调用。

---

## 8. 维护提示

- 新增 `parse_command` 返回字段：在 `autoSendTask` 增加分支，并在 `routes/api.py` 白名单中加入键（若需到前端）。
- 用户白名单：若后端新增字段或错误码，需同步 **`DefaultPanel`** 与 **`App.jsx`** 中的 `addLog` 文案及 [routes-api-模块说明.md](../backend/routes-api-模块说明.md)。

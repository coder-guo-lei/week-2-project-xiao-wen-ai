# `src/components/` — 各组件模块说明汇总

以下均为 **默认导出** 的函数组件（除非注明），由 `App.jsx` 组合；props 以源码为准。

---

## `CommandInput.jsx`

- **职责**：受控输入框 `task`/`setTask`、发送按钮、`isSending` 禁用、命令历史点击回填、语音按钮（唤醒/指令状态来自 props）、示例与快捷键提示。
- **关键 props**：`task`、`setTask`、`onSend`、`commandHistory`、`voice` 相关布尔与方法等（见文件顶部参数解构）。

## `LogPanel.jsx`

- **职责**：右侧运行日志列表、`onClear` 清空。

## `MusicPlayer.jsx`

- **职责**：渲染 `<audio ref={music.audioRef}>` 并绑定 `music.audioHandlers`；展示封面区、播放控制、进度条、音量、历史列表、`qishui` 外链按钮等。
- **依赖**：`useMusicPlayer()` 返回对象（由 `App` 传入 `music` prop）。

## `WeatherCard.jsx`

- **职责**：接收 `weatherData`（后端 `extraData`），展示城市、实况、图标、背景渐变、`outdoorTips` 等；内含 `getWeatherBg`、`weatherIcon` 辅助函数。

## `ChatPanel.jsx`

- **职责**：展示 `reply` 字符串；`renderTextWithLinks` 将 URL 转为可点击链接；集成朗读（`playXfyunTts` / `cleanupTtsAudio`）与音色偏好。

## `ImagePreview.jsx`

- **职责**：文生图结果或加载中 UI；`safeFilenameFromPrompt` 生成下载文件名；显示已等待秒数。

## `DefaultPanel.jsx` + `DefaultPanel.css`

- **职责**：默认视图下的状态点、**用户应用白名单（浏览 .exe、确认名称、列表与移除）**、示例指令卡片网格。
- **白名单依赖**：`userExePickSupported`（来自 `/api/capabilities.userExePick`）、`pickBrowseBusy`、`userAppList`、`addAppDraft`、`addAppNameInput` 及若干回调均由 `App.jsx` 注入。
- **详细文档**（逐块 JSX、全部 CSS 类说明、与 App 数据流）：[DefaultPanel-模块说明.md](./DefaultPanel-模块说明.md)。

（原「仅待机欢迎 + 示例」的描述已扩展为含白名单；旧版行为仍保留。）

## `SelectionToolbar.jsx`

- **职责**：监听 `mouseup` 选区、`detectTargetLang` 粗判中/英；调用 `POST /api/translate-selection`；可触发划词朗读（TTS）。

## `ModeBar.jsx`

- **职责**：展示当前 `mode` / `modeLabel`；模拟世界时 `worldState` 与 `quickActions`；`onQuickAction` 将快捷句回传发送。

## `WorkflowPanel.jsx`

- **职责**：将 `steps` 数组渲染为步骤列表（标题 + 详情）。

## `ImageAnalyzer.jsx`

- **职责**：本地上传图片 + 问题文本，`multipart` 调 `POST /api/analyze-image`；回调 `onAnalyze` 把结果交给 `App`。

## `FaceWellnessCamera.jsx`

- **职责**：`getUserMedia` 视频预览、抓拍 canvas → Blob → 同样走图片分析接口（肤质类 `kind`）；`onAnalyze` 回调。

## `ChartPanel.jsx`

- **职责**：根据 `chartData` 计算 SVG 几何（`buildChartGeometry`、`computeBarLayout` 等）；支持本地上传触发 `onUpload`（父级 `generateChartFromFile`）。

## `XiaowenBot.jsx`

- **职责**：可拖拽吉祥物；`clampPos` 限制在视口内；装饰性动画。

---

## 组件与后端接口对照

| 组件 | 典型 API |
|------|----------|
| `App` | `/api/send-task`、`/api/generate-chart`、`/api/image-status/*`、**`/api/user-apps`（GET/POST/DELETE）**、**`/api/user-apps/pick`（POST）**、**`/api/capabilities`（含 `userExePick`）** |
| `ImageAnalyzer` / `FaceWellnessCamera` | `/api/analyze-image` |
| `ChartPanel`（上传） | 由 `App` 调 `/api/generate-chart` |
| `ChatPanel` / `SelectionToolbar` | `/api/tts`；`SelectionToolbar` 另用 `/api/translate-selection` |
| `useVoiceRecognition` + utils | 可选 `/api/speech-to-text` |
| **`DefaultPanel`（白名单）** | 同上表 `App` 列出的 user-apps 与 capabilities |

---

## 扩展新面板建议

1. 新建 `MyPanel.jsx` + `MyPanel.css`。
2. 在 `App.jsx` 增加 `contentType` 分支与状态。
3. 若需新 API：先加后端 `routes/api.py` 与 `task_parser` 或独立 service，再在前端 `fetch`。

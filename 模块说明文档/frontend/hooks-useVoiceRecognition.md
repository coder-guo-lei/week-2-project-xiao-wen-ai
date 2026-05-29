# `src/hooks/useVoiceRecognition.js` — 模块说明

> 文件较长（约 **770+ 行**），实现 **双路 Web Speech API**：唤醒（continuous）+ 指令（单次），以及可选 **讯飞后端听写** 路径。文件头 **1–23 行** 为权威结构说明。

---

## 1. 常量区（约 28–44 行）

| 常量 | 含义 |
|------|------|
| `RECOVERABLE_WAKE_ERRORS` | `aborted`/`no-speech`/`network` 等可尝试重启唤醒监听。 |
| `FATAL_WAKE_ERRORS` | 权限被拒等致命错误，停止自动重试。 |
| `CMD_NO_INPUT_MS` | 指令识别全程无文字约 20s 超时。 |
| `CMD_SILENCE_AFTER_SPEECH_MS` | 已有文字后约 2.8s 无更新则 `stop`。 |
| `CMD_AUDIO_CONSTRAINTS` | `getUserMedia` 音频约束（回声消除关闭等策略）。 |

---

## 2. 纯函数工具（约 46–135 行）

| 函数 | 作用 |
|------|------|
| `bestTranscriptFromRow(row)` | 同一 `SpeechRecognitionResult` 多候选中取最长 `transcript`。 |
| `concatCmdResults(results)` | 拼接当前会话所有结果行文本。 |
| `WAKE_NAMES` / 各 `RE_*` 正则 | 同音唤醒词与去前缀模式。 |
| `normalizeWakeText` | 去空白与标点，便于匹配。 |
| `matchesWakePhrase` | 是否命中唤醒（叠词、称呼开头、你好小文等）。 |
| `matchesInterimWakeOnly` / `matchesInterimSingleWakeName` | interim 阶段可提前触发的短句规则。 |
| `stripWakePrefix` | 从归一化文本去掉唤醒前缀，得到可发送后端的指令。 |

---

## 3. Hook 参数与返回值

**参数**：`{ onResult, addLog, useXfyunAsr }`

- `onResult(text)`：`App` 传入，收到最终指令文本时调用（通常再 `autoSendTask`）。
- `addLog`：右侧日志。
- `useXfyunAsr`：`App` 当前传 `false`；为 `true` 时可走 `recordAndTranscribeXfyun`（`micRecorderXfyun.js`）。

**对外 API**（见文件头注释）：`isWakeActive`、`isCmdActive`、`startCmdRecognition`、`stopCmdRecognition`、`toggleWakeMode` 等（以 `export` 对象为准）。

---

## 4. 实现要点（逻辑层）

- **先占麦克风再开识别**：减少 Chrome 立即丢轨道问题（`cmdMicStreamRef`）。
- **唤醒通道**：`continuous` 识别，`onresult` 里检测唤醒词后启动指令识别，并可从 `stripWakePrefix` 得到已含指令的文本直接提交。
- **指令通道**：非 continuous；合并 `results`；定时器处理无输入与句尾静音。
- **网络错误**：带次数限制的 `network` 重试（`cmdNetworkRetryCountRef`）。
- **讯飞分支**：`AbortController` 取消进行中的后端听写。

---

## 5. 依赖

- `../utils/micRecorderXfyun` 的 `recordAndTranscribeXfyun`。
- 浏览器需 `webkitSpeechRecognition` 或 `SpeechRecognition`（Chrome/Edge 常见）。

---

## 6. 维护建议

- 调整唤醒灵敏度：改 `WAKE_NAMES` 与 `matchesWakePhrase` 规则，注意误唤醒与漏唤醒权衡。
- 与 `App.jsx` 的 `useXfyunAsr` 联动：开启时需后端 `/api/capabilities` 中 `xfyunAsr` 为 true 且用户理解上传 WAV 流程。

# 前端（xiao-wen-ai）总览

## 技术栈

- **构建**：Vite 8 + `@vitejs/plugin-react`。
- **UI**：React 19，无额外 UI 库；样式为各组件 `.css` + `index.css` / `App.css`。
- **包管理**：`pnpm`（见 `package.json` 的 `packageManager`）。

## 目录与模块对应

| 路径 | 职责 |
|------|------|
| `index.html` | HTML 壳、字体预连接、`#root`、入口脚本。 |
| `vite.config.js` | React 插件、`/api` 代理到 `127.0.0.1:5001`。 |
| `src/main.jsx` | `createRoot` 挂载 `App`，`StrictMode`。 |
| `src/apiBase.js` | `API_BASE`、`apiUrl()`：开发与生产基址。 |
| `src/App.jsx` | 全局状态、定位、`/api/send-task` 编排、**用户应用白名单请求与状态**、子组件组合。 |
| `src/components/*.jsx` | 各功能面板与控件（**`DefaultPanel`** 含浏览添加 `.exe` 与列表）。 |
| `src/hooks/*.js` | `useMusicPlayer`、`useVoiceRecognition`。 |
| `src/utils/*.js` | 讯飞 TTS 请求、麦克风录音 WAV、AudioWorklet。 |
| `src/index.css`、`App.css`、各 `*.css` | 布局与主题样式。 |

详见同目录下各 Markdown 文件；**默认面板与白名单 UI** 见 [DefaultPanel-模块说明.md](./DefaultPanel-模块说明.md)。

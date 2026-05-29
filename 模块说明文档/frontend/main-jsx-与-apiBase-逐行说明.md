# `src/main.jsx` 与 `src/apiBase.js` — 逐行说明

## `main.jsx`

| 行号 | 含义 |
|------|------|
| 1–4 | 文件注释：说明入口职责（挂载到 `#root`、全局样式）。 |
| 5 | `import { StrictMode } from 'react'`：严格模式。 |
| 6 | `import { createRoot } from 'react-dom/client'`：React 18+ 客户端 API。 |
| 7 | `import './index.css'`：全局样式最先注入。 |
| 8 | `import App from './App.jsx'`：根组件。 |
| 10–11 | 注释：在 `#root` 创建根并渲染。 |
| 11–14 | `createRoot(document.getElementById('root')).render(<StrictMode><App /></StrictMode>)`：挂载整树。 |

## `apiBase.js`

| 行号 | 含义 |
|------|------|
| 1–5 | 注释：开发默认 `''` 走相对路径 + Vite 代理；生产默认直连 `http://127.0.0.1:5001`；可用 `VITE_API_URL` 或 `VITE_API_BASE` 覆盖。 |
| 6 | `_fromEnv`：读取两个环境变量名之一（Vite 以 `import.meta.env` 注入）。 |
| 7–9 | `export const API_BASE`：若 env 非空则 trim 并去尾斜杠；否则 `DEV ? '' : 'http://127.0.0.1:5001'`。 |
| 11–15 | `export function apiUrl(path)`：保证 path 以 `/` 开头；`API_BASE` 为空则返回相对 path，否则拼接绝对基址 + path。 |

**注意**：`VITE_*` 变量在 **`pnpm build` 时静态替换**；改 env 后需重新 build。

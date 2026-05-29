# `xiao-wen-ai/vite.config.js` — 逐行说明

| 行号 | 含义 |
|------|------|
| 1 | 从 `vite` 导入 `defineConfig`，获得类型提示与默认合并行为。 |
| 2 | 导入 `@vitejs/plugin-react`：JSX 转换、Fast Refresh 等。 |
| 4 | 注释：官方文档链接占位。 |
| 5 | `export default defineConfig({ ... })`：导出 Vite 配置对象。 |
| 6 | `plugins: [react()]`：启用 React 插件数组。 |
| 7 | `server: {`：仅开发服务器相关配置。 |
| 8 | `proxy: {`：开发期反向代理表。 |
| 9 | `'/api': {`：凡请求路径以 `/api` 开头。 |
| 10 | `target: 'http://127.0.0.1:5001'`：转发到本机 Flask 后端（与 `backend/app.py` 默认端口一致）。 |
| 11 | `changeOrigin: true`：改写 Host 头，减少部分代理场景下的跨域问题。 |
| 12–13 | 闭合 `proxy`、`server`。 |
| 14–15 | 闭合 `defineConfig`。 |

**效果**：前端 `fetch('/api/send-task')` 在开发环境无需写完整后端域名；生产环境依赖 `apiBase.js` 的 `API_BASE`。

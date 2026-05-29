# `xiao-wen-ai/index.html` — 逐行说明

| 行号 | 含义 |
|------|------|
| 1 | `<!doctype html>`：HTML5 文档类型。 |
| 2 | `<html lang="zh-CN">`：根元素，中文语言标记（无障碍与搜索引擎）。 |
| 3 | `<head>`：元数据与资源引用区。 |
| 4 | `<meta charset="UTF-8" />`：字符编码 UTF-8。 |
| 5 | `<link rel="icon" ... href="/favicon.svg" />`：站点图标。 |
| 6 | `<meta name="viewport" ...>`：移动端视口宽度与初始缩放。 |
| 7 | `<meta name="color-scheme" content="light dark" />`：告知浏览器支持浅色/深色配色。 |
| 8 | `<title>小文 · 智能语音助手</title>`：浏览器标签标题。 |
| 9–10 | `preconnect` 到 Google Fonts，加速字体握手。 |
| 11–14 | 加载字体 CSS：`Fraunces`、`JetBrains Mono`、`Noto Sans SC` 多字重。 |
| 15 | `</head>`。 |
| 16 | `<body>`：可见内容容器。 |
| 17 | `<div id="root"></div>`：React 挂载点，`main.jsx` 中 `getElementById('root')`。 |
| 18 | `<script type="module" src="/src/main.jsx"></script>`：Vite 以 ESM 加载入口（开发时经 Vite 转换）。 |
| 19 | `</body>`。 |
| 20 | `</html>`。 |

# 样式模块说明（`index.css`、`App.css`、各组件 CSS）

## `src/index.css`

- **角色**：全站基础——CSS 变量（颜色、圆角、阴影、间距）、`box-sizing` reset、body 背景与字体栈（与 `index.html` 引入的 Google Fonts 呼应）、暗色 `prefers-color-scheme` 变量覆盖、滚动条美化、通用工具类（若存在）。
- **维护**：改主题色或字体优先改此处变量，再让组件用 `var(--token)` 引用。

## `src/App.css`

- **角色**：根布局网格或 Flex：`App.jsx` 最外层 class（如主栏/侧栏比例）、响应式断点、与智慧助手空间标题相关的布局。
- **维护**：避免把每个小组件细节都堆进来；组件独有视觉放在对应 `Component.css`。

## `src/components/*.css`

每个 JSX 同名 CSS 负责该组件局部：间距、卡片、按钮态、动画等。

| 文件 | 典型职责（以文件名为准） |
|------|---------------------------|
| `ChatPanel.css` | 聊天气泡、链接样式、朗读按钮区。 |
| `CommandInput.css` | 输入框、发送/语音按钮、历史下拉。 |
| `ModeBar.css` | 模式标签、世界快捷按钮条。 |
| `WorkflowPanel.css` | 步骤时间线或卡片列表。 |
| `WeatherCard.css` | 天气卡片背景与图标排版。 |
| `MusicPlayer.css` | 播放器控件与进度条。 |
| `ChartPanel.css` | SVG 图表容器与坐标轴。 |
| `DefaultPanel.css` | 默认欢迎区与示例卡片。 |
| `LogPanel.css` | 右侧日志列表与清空按钮。 |
| `XiaowenBot.css` | 吉祥物位置与动画。 |
| `ImagePreview.css` / `ImageAnalyzer.css` | 图片预览与上传分析 UI。 |
| `FaceWellnessCamera.css` | 摄像头区域与抓拍按钮。 |
| `SelectionToolbar.css` | 划词浮动条。 |

**原则**：组件样式与结构同名，便于删除组件时一并清理。

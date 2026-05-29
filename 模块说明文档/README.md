# 小文项目 — 模块说明文档索引

本目录为「小文」智能语音助手前后端源码的**模块级说明**，与仓库根目录下的 `backend/`、`xiao-wen-ai/` 对应。

## 说明约定

- **逐行**：对行数很少或关键的文件，按行号解释每一行在做什么。
- **分段/函数级**：对 `task_parser.py`、`App.jsx` 等超长文件，采用「文件头导入 + 章节标题 + 函数索引 + 核心逻辑说明」，避免无意义地复制三千行源码；需要对照时请直接在 IDE 中打开源文件并结合本目录中的行号区间。

## 目录结构

| 路径 | 内容 |
|------|------|
| [backend/README.md](./backend/README.md) | 后端技术栈与目录总览 |
| [backend/app.py-逐行说明.md](./backend/app.py-逐行说明.md) | Flask 应用入口 |
| [backend/config-模块说明.md](./backend/config-模块说明.md) | 环境变量与路径解析 |
| [backend/session-逐行说明.md](./backend/session-逐行说明.md) | 进程内会话状态 |
| [backend/routes-api-模块说明.md](./backend/routes-api-模块说明.md) | HTTP API Blueprint |
| [backend/logic-task_parser-模块说明.md](./backend/logic-task_parser-模块说明.md) | 指令解析与业务核心 |
| [backend/logic-user_apps-模块说明.md](./backend/logic-user_apps-模块说明.md) | 用户自定义应用白名单（JSON、合并、校验、子进程选文件） |
| [backend/scripts-pick_exe_dialog-逐行说明.md](./backend/scripts-pick_exe_dialog-逐行说明.md) | Windows 下 tkinter 选 `.exe` 子进程脚本（逐行） |
| [backend/data-用户应用白名单-说明.md](./backend/data-用户应用白名单-说明.md) | `data/` 目录与 `user_app_launchers.json` 格式 |
| [backend/services-xfyun_tts-模块说明.md](./backend/services-xfyun_tts-模块说明.md) | 讯飞语音合成 |
| [backend/services-xfyun_iat-模块说明.md](./backend/services-xfyun_iat-模块说明.md) | 讯飞语音听写 |
| [backend/packages-init-模块说明.md](./backend/packages-init-模块说明.md) | `__init__.py` 包说明 |
| [backend/requirements-模块说明.md](./backend/requirements-模块说明.md) | Python 依赖 |
| [frontend/README.md](./frontend/README.md) | 前端技术栈与目录总览 |
| [frontend/index-html-逐行说明.md](./frontend/index-html-逐行说明.md) | HTML 壳 |
| [frontend/vite-config-逐行说明.md](./frontend/vite-config-逐行说明.md) | Vite 与代理 |
| [frontend/main-jsx-与-apiBase-逐行说明.md](./frontend/main-jsx-与-apiBase-逐行说明.md) | React 入口与 API 基址 |
| [frontend/App.jsx-模块说明.md](./frontend/App.jsx-模块说明.md) | 根组件状态机与请求编排 |
| [frontend/DefaultPanel-模块说明.md](./frontend/DefaultPanel-模块说明.md) | 默认面板 + 白名单 UI 与样式说明 |
| [frontend/hooks-useMusicPlayer.md](./frontend/hooks-useMusicPlayer.md) | 音乐播放 Hook |
| [frontend/hooks-useVoiceRecognition.md](./frontend/hooks-useVoiceRecognition.md) | 语音识别 Hook |
| [frontend/utils-语音与TTS工具.md](./frontend/utils-语音与TTS工具.md) | TTS、录音、Worklet |
| [frontend/styles-模块说明.md](./frontend/styles-模块说明.md) | 全局与根布局样式 |
| [frontend/components-模块说明汇总.md](./frontend/components-模块说明汇总.md) | 各 UI 组件职责 |

文档生成时对照的源码位于：`D:\Desktop\xiaowen\backend\`、`D:\Desktop\xiaowen\xiao-wen-ai\`。

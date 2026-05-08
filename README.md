# 小文智能语音助手（交付仓库）

面向个人桌面的 **React + Vite** 前端与 **Flask** 后端一体化智能助手：语音唤醒、多轮对话、天气、音乐、文生图、图表、划词翻译、本机应用白名单启动等。

## 仓库结构

| 路径 | 说明 |
|------|------|
| `backend/` | Flask API：`app.py`、依赖 `requirements.txt`、环境模板 `.env.example` |
| `xiao-wen-ai/` | 前端工程：`pnpm dev` / `pnpm build`，详见该目录 [README](xiao-wen-ai/README.md) |
| `generate_xiaowen_ppt.py` | 可选：生成答辩用 PPTX（需 `pip install python-pptx`） |
| `AI与前端项目汇总.md` | 通用前端/AI 学习笔记与小文项目摘要 |

## 快速启动

**后端（默认 `http://127.0.0.1:5001`）**

```bash
cd backend
pip install -r requirements.txt
copy .env.example .env   # Windows：手动复制后填写密钥
python app.py
```

**前端（默认 `http://localhost:5173`）**

```bash
cd xiao-wen-ai
pnpm install
pnpm dev
```

## 环境变量要点

- **DashScope（百炼）**：对话、文生图、视觉、翻译等主能力。  
- **DeepSeek（可选）**：OpenAI 兼容接口，作对话/翻译/知识库兜底。  
- **AMAP_KEY**：高德地图天气与地理编码，勿硬编码。  
- **LOCAL_TIMEZONE**：对话里「今天」所用 IANA 时区（默认 `Asia/Shanghai`）。  

完整列表见 `backend/.env.example`。

## 交付版行为说明（与时间相关）

- 系统提示中注入 **服务端当前公历时刻**，减少模型编造日期。  
- **农历**由 **zhdate** 换算；传入 `ZhDate` 前使用本地墙钟 **naive** `datetime`，避免与库内 naive 日期运算冲突。  
- 当年度 **农历锚点**（如正月初一、三月廿六等）写入提示，禁止模型手算「阴历生日→公历」。  

详细设计与功能清单见 [xiao-wen-ai/README.md](xiao-wen-ai/README.md)。

## 生成汇报 PPT

```bash
pip install python-pptx
python generate_xiaowen_ppt.py
```

输出文件：`xiaowen-report-final.pptx`（与脚本同目录；可按需在资源管理器中重命名为中文名）。

## 安全提示

勿将 `.env`、真实 API Key 提交到公开仓库；泄露密钥后请及时在各云平台重置。

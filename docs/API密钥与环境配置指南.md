# 小文项目 · API 密钥与环境配置指南

> 组员从 Git 克隆仓库后，按本文配置即可本地跑通。  
> **所有密钥只放在 `backend/.env`，不要写进前端代码，也不要提交到 Git。**

---

## 一、5 分钟快速上手

```bash
# 1. 克隆仓库
git clone git@gitee.com:orange-feimao/week-2-project-xiao-wen-ai.git
cd week-2-project-xiao-wen-ai

# 2. 后端：复制配置模板并填写密钥
cd backend
pip install -r requirements.txt
copy .env.example .env        # macOS/Linux: cp .env.example .env
# 用编辑器打开 .env，按第二节填写必填项

python app.py                 # 启动后默认 http://127.0.0.1:5001

# 3. 前端（新开一个终端）
cd xiao-wen-ai
pnpm install
pnpm dev                      # 默认 http://localhost:5173
```

浏览器打开 `http://localhost:5173`，能对话、查天气、朗读即表示配置基本成功。

---

## 二、配置文件放在哪里

| 文件 | 路径 | 说明 |
|------|------|------|
| **环境变量（主配置）** | `backend/.env` | 所有 API Key、本机路径等，**每人本地一份** |
| **配置模板（可提交 Git）** | `backend/.env.example` | 变量名与注释说明，复制后改名为 `.env` |
| **加载逻辑** | `backend/config.py` | 启动时自动 `load_dotenv`，无需改代码 |
| **前端 API 地址（可选）** | `xiao-wen-ai/.env` 或 `.env.local` | 仅生产构建时需要，见第六节 |

`.env` 已被 `.gitignore` 忽略，Git 上**没有**真实密钥。每人需自行申请或在组内安全渠道获取。

---

## 三、密钥总览（按优先级）

### 必填（建议至少配齐，才能完整演示）

| 变量名 | 用途 | 对应功能 | 申请地址 |
|--------|------|----------|----------|
| `DASHSCOPE_API_KEY` | 阿里云百炼 API Key | AI 对话、文生图、图片理解、划词翻译 | [百炼控制台](https://bailian.console.aliyun.com/) |
| `AMAP_KEY` | 高德 Web 服务 Key | 城市天气、地理编码 | [高德开放平台](https://console.amap.com/) → 应用管理 → 添加 Key（类型选 **Web 服务**） |
| `XFYUN_APP_ID` | 讯飞应用 ID | 语音朗读 TTS、后端语音听写 IAT | [讯飞开放平台](https://console.xfyun.cn/) |
| `XFYUN_API_KEY` | 讯飞 API Key | 同上 | 同上 |
| `XFYUN_API_SECRET` | 讯飞 API Secret | 同上 | 同上 |

### 推荐（二选一或都配，对话更灵活）

| 变量名 | 用途 | 说明 |
|--------|------|------|
| `DEEPSEEK_API_KEY` | DeepSeek API Key | 可作对话 / 翻译 / 知识库兜底；[DeepSeek 开放平台](https://platform.deepseek.com/) 申请。**不能**替代百炼的文生图、看图 |

### 可选（按需填写）

| 变量名 | 用途 | 说明 |
|--------|------|------|
| `XFYUN_SUPER_TTS_WS_URL` | 讯飞超拟人 TTS WebSocket 地址 | 在讯飞控制台「超拟人语音合成」产品页复制完整 `wss://...`；**不填**则使用在线语音合成 v2 |
| `DOUYIN_EXE_PATH` | 本机抖音 PC 客户端路径 | 仅「打开抖音」指令需要；例：`D:/软件/douyin/douyin.exe` |
| `DASHSCOPE_CHAT_MODEL` | 对话模型 | 默认 `qwen-turbo`，可按百炼控制台可用模型修改 |
| `DASHSCOPE_IMAGE_MODEL` | 文生图模型 | 默认 `wanx2.1-t2i-turbo` |
| `DASHSCOPE_VL_MODEL` | 图片理解模型 | 默认 `qwen-vl-plus` |
| `IMAGE_SIZE` | 生成图片尺寸 | 默认 `768*1024` |
| `PRIMARY_LLM` | 优先使用哪家大模型 | `dashscope`（默认）或 `deepseek` |
| `LOCAL_TIMEZONE` | 对话里「今天」的时区 | 默认 `Asia/Shanghai` |
| `CHAT_TIMEOUT` | 对话请求超时（秒） | 默认 `60` |

---

## 四、完整 `.env` 示例（请替换为你的真实值）

在 `backend/` 目录创建 `.env`（或从 `.env.example` 复制），格式如下：

```env
# ========== 阿里云百炼（对话 / 生图 / 看图 / 翻译）==========
DASHSCOPE_API_KEY=sk-你的百炼密钥
DASHSCOPE_CHAT_MODEL=qwen-turbo
DASHSCOPE_IMAGE_MODEL=wanx2.1-t2i-turbo
DASHSCOPE_VL_MODEL=qwen-vl-plus
IMAGE_SIZE=768*1024

# ========== DeepSeek（可选，对话/翻译兜底）==========
DEEPSEEK_API_KEY=sk-你的DeepSeek密钥
# DEEPSEEK_CHAT_MODEL=deepseek-chat

# ========== 高德地图（天气）==========
AMAP_KEY=你的高德Web服务Key

# ========== 讯飞（朗读 TTS + 听写 IAT，三件套同一应用）==========
XFYUN_APP_ID=你的AppID
XFYUN_API_KEY=你的APIKey
XFYUN_API_SECRET=你的APISecret

# 超拟人朗读（可选）：不填则用在线合成 v2
# XFYUN_SUPER_TTS_WS_URL=wss://cbm01.cn-huabei-1.xf-yun.com/v1/private/你的实例路径

# ========== 本机路径（可选）==========
# DOUYIN_EXE_PATH=D:/你的路径/douyin.exe

# ========== 其它（一般不用改）==========
# LOCAL_TIMEZONE=Asia/Shanghai
# PRIMARY_LLM=dashscope
# CHAT_TIMEOUT=60
```

**填写注意：**

- 等号后面**不要加引号**，不要多余空格。
- 修改后 **Ctrl+S 保存**，并 **重启后端** `python app.py` 才会生效。
- 百炼与 DeepSeek 至少配一个，对话才能用；天气必须配 `AMAP_KEY`；朗读必须配讯飞三件套。

---

## 五、各平台申请步骤（简版）

### 1. 阿里云百炼 `DASHSCOPE_API_KEY`

1. 登录 [百炼控制台](https://bailian.console.aliyun.com/)。
2. 进入 **API-KEY 管理**，创建并复制 Key（形如 `sk-xxxxxxxx`）。
3. 确保账户已开通 **通义千问**（对话）、**万相**（文生图）、**通义千问 VL**（看图）等所需服务（按你们演示功能开通即可）。

**项目里用在哪：** `backend/logic/task_parser.py` — 对话、翻译、文生图、图片理解等。

### 2. DeepSeek `DEEPSEEK_API_KEY`（可选）

1. 登录 [DeepSeek 开放平台](https://platform.deepseek.com/)。
2. 创建 API Key 并复制。

**项目里用在哪：** 与百炼类似的对话/翻译链路；配置 `PRIMARY_LLM=deepseek` 可优先走 DeepSeek。

### 3. 高德 `AMAP_KEY`

1. 登录 [高德开放平台](https://console.amap.com/)。
2. **应用管理 → 我的应用 → 创建新应用 → 添加 Key**。
3. Key 类型选择 **Web 服务**（不是 JS API、不是 Android）。

**项目里用在哪：** 用户说「北京天气怎么样」时，后端调高德地理编码 + 天气接口。

### 4. 讯飞 `XFYUN_APP_ID` / `XFYUN_API_KEY` / `XFYUN_API_SECRET`

1. 登录 [讯飞开放平台](https://console.xfyun.cn/)。
2. 创建应用，在同一应用下开通：
   - **在线语音合成** 或 **超拟人语音合成**（朗读 `/api/tts`）
   - **语音听写（流式版）**（若使用后端 IAT）
3. 在应用详情页复制 **APPID、APIKey、APISecret** 三个值。

**超拟人（可选）：** 若使用超拟人，还需在对应产品页复制 **WebSocket 服务地址**，填入 `XFYUN_SUPER_TTS_WS_URL`。

**项目里用在哪：**

- `backend/services/xfyun_tts.py` — 回复朗读、划词朗读
- `backend/services/xfyun_iat.py` — 语音听写（若启用）

### 5. 抖音路径 `DOUYIN_EXE_PATH`（可选）

仅当需要语音/文字「打开抖音」且自动扫描找不到安装路径时填写。

Windows：右键桌面抖音快捷方式 → 属性 → **目标** 一栏即为 `douyin.exe` 完整路径。

---

## 六、前端环境变量（多数情况不用配）

开发时前端通过 Vite 代理，请求走相对路径 `/api/*` → `http://127.0.0.1:5001`，**不需要**在前端放任何 API Key。

仅 **生产构建** 且后端不在本机 `5001` 时，在 `xiao-wen-ai/` 下创建 `.env`：

```env
VITE_API_URL=http://你的后端地址:5001
```

或使用等价变量 `VITE_API_BASE`。修改后需重新执行 `pnpm build`。

逻辑见：`xiao-wen-ai/src/apiBase.js`。

---

## 七、功能 ↔ 密钥对照表

| 你想用的功能 | 最少需要配置的变量 |
|--------------|-------------------|
| AI 聊天、讲故事、笑话 | `DASHSCOPE_API_KEY` 或 `DEEPSEEK_API_KEY` |
| 划词翻译 | 同上 |
| 文生图「画一只猫」 | `DASHSCOPE_API_KEY` |
| 图片理解 / 上传看图 | `DASHSCOPE_API_KEY` |
| 查天气 | `AMAP_KEY` |
| 小文朗读回复 | `XFYUN_APP_ID` + `XFYUN_API_KEY` + `XFYUN_API_SECRET` |
| 超拟人音色朗读 | 讯飞三件套 + `XFYUN_SUPER_TTS_WS_URL` |
| 打开抖音 | `DOUYIN_EXE_PATH`（或本机已安装且能被自动发现） |
| 打开微信/QQ/网易云 | 无需 Key，需本机已安装对应软件 |

---

## 八、配置后自检

1. **后端启动无报错**  
   `cd backend && python app.py`，终端应监听 `5001`。

2. **对话**  
   前端输入「你好」→ 有正常回复（否则检查百炼/DeepSeek Key）。

3. **天气**  
   输入「北京天气」→ 出现天气卡片（否则检查 `AMAP_KEY` 是否为 Web 服务类型）。

4. **朗读**  
   点击回复旁的朗读按钮 → 有声音（否则检查讯飞三件套及服务是否开通）。

5. **生图**  
   输入「画一只水彩小猫」→ 进入生成中并最终出图（需百炼 Key 且开通万相）。

---

## 九、常见问题

| 现象 | 可能原因 | 处理 |
|------|----------|------|
| 对话提示「未配置对话模型」 | 未填 `DASHSCOPE_API_KEY` 和 `DEEPSEEK_API_KEY` | 至少填一个并重启后端 |
| 天气一直是占位/失败 | `AMAP_KEY` 未填或 Key 类型不对 | 使用高德 **Web 服务** Key |
| 朗读报错 11200 | 发音人未在讯飞控制台授权 | 换默认音色或领取对应发音人 |
| 改了 `.env` 不生效 | 未重启后端 | 保存文件后重新 `python app.py` |
| 前端连不上后端 | 后端未启动或端口不对 | 确认 `5001` 已监听；开发态用 `pnpm dev` |
| 生图/看图失败但聊天正常 | 只配了 DeepSeek | 生图和看图**必须**百炼 `DASHSCOPE_API_KEY` |

---

## 十、安全提醒

1. **不要把 `backend/.env` 提交到 Git**（仓库已忽略，提交前用 `git status` 确认）。
2. 密钥只在组内通过安全方式共享（私聊、密码管理器），不要贴在公开 Issue / 群公告。
3. 若密钥泄露，立即在对应云平台 **作废并重新生成**。
4. 前端仓库与构建产物中**不应出现**任何 `sk-` 或讯飞 Secret。

---

## 十一、相关文件索引

| 文件 | 作用 |
|------|------|
| `backend/.env.example` | 可提交的变量模板 |
| `backend/config.py` | 读取环境变量、默认值、本机软件解析 |
| `backend/logic/task_parser.py` | 对话、天气、生图等业务 |
| `backend/services/xfyun_tts.py` | 讯飞朗读 |
| `backend/services/xfyun_iat.py` | 讯飞听写 |
| `xiao-wen-ai/src/apiBase.js` | 前端 API 根地址 |
| 根目录 `README.md` | 仓库结构与启动命令 |

如有新增加密钥类配置，请同步更新 `backend/.env.example` 与本文档。

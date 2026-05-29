# `backend/config.py` — 模块说明（分段 + 关键符号）

本文件约 450+ 行，承担：**环境加载**、**全局常量**、**Windows 应用路径解析**、**文字世界词表**、**用户提示文案**。下面按源码顺序说明；行号为撰写文档时的大致区间，以仓库内实际文件为准。

---

## 1–27：模块说明、导入与 `.env` 加载

| 行号（约） | 含义 |
|------------|------|
| 1–9 | 顶层文档字符串，概括文件职责。 |
| 10–16 | `logging`、`os`、`re`、`shutil`、`Path`；`dotenv_values`、`load_dotenv`。 |
| 18–21 | `BASE_DIR` = `backend` 目录；`REPO_ROOT` = 上一级；`_ENV_FILE` = `backend/.env`。 |
| 22–26 | `load_dotenv` 后遍历 `dotenv_values`，把非空键写回 `os.environ`（覆盖空值策略：仅非空写入）。 |
| 27–28 | `logging.basicConfig`：INFO 级别与格式串。 |

---

## `APP_LAUNCHERS`（约 126–147 行）与用户白名单的关系

- **`APP_LAUNCHERS`**：源码内嵌字典，键为自然语言称呼（如「记事本」「微信」），值为 `notepad`、`resolve:wechat` 等**固定**启动策略。
- **用户扩展**：不修改本字典文件；用户通过前端添加的条目保存在 **`backend/data/user_app_launchers.json`**（`exe:绝对路径`），由 **`logic.user_apps.merge_launchers()`** 与内置表合并后供 `task_parser.launch_local_app` 遍历。详见 [logic-user_apps-模块说明.md](./logic-user_apps-模块说明.md)。

---

## 30–66：讯飞 TTS 相关环境变量与默认发音人

- `MAX_TTS_CHARS`、`XFYUN_*`：应用 ID、密钥、语速音量、磁盘缓存开关、音频格式/采样率。
- `XFYUN_SUPER_TTS_WS_URL`：非空则 `USE_XFYUN_SUPER_TTS=True`，走超拟人 WebSocket。
- `XFYUN_VCN_PATTERN`、`xfyun_vcn_ok()`：校验自定义发音人 ID 格式。
- `TTS_CACHE_DIR`：磁盘缓存目录 `backend/cache/tts`。
- 分支：超拟人开启时用 `XFYUN_DEFAULT_VCN_FEMALE` 默认超拟人 vcn，否则经典 `xiaoyan`。

---

## 67–96：地图、百炼、DeepSeek、对话与上传限制

- `AMAP_KEY`、`REQUEST_TIMEOUT`、`CHAT_TIMEOUT`、`LOCAL_TIMEZONE`。
- DashScope：URL、对话/文生图/VL 模型名、上传图片大小、轮询间隔等。
- DeepSeek：`DEEPSEEK_API_KEY`、聊天 URL、模型名。
- `PRIMARY_LLM` → `PRIMARY_LLM_DEEPSEEK_FIRST`：对话优先厂商。
- `NETEASE_HEADERS`：网易云 HTTP 头伪装浏览器。
- `MAX_KNOWLEDGE_SNIPPETS`、`MAX_CHAT_HISTORY_MESSAGES`、`MAX_CHAT_MESSAGE_CHARS`：对话与知识库截断策略。
- `WORLD_SIM_LLM`、`WORLD_SIM_LLM_MIN_LEN`：模拟世界是否用 LLM 润色及长度阈值。

---

## 101–124：`WORLD_THEMES` 与 `WORLD_ACTIONS`

- 三个主题字典键：`修仙`、`末日`、`奇幻`；每主题含 `cores`、`birthplaces`、`resources`、`scenes`、`events` 列表，供 `task_parser` 随机叙事。
- `WORLD_ACTIONS`：用户可输入的动作关键词列表。

---

## 126–147：`APP_LAUNCHERS`

- 中文别名到启动命令字符串的映射。
- `resolve:wechat` 等特殊值在 `launch_local_app` 中再解析为真实路径。

---

## 150–436：Windows 路径解析函数族

- `_tencent_install_roots()`：从环境变量收集 `ProgramFiles` 等根目录。
- `_winreg_try_wechat_exe()` / `resolve_tencent_wechat_exe()`：注册表 + 常见相对路径找微信。
- `resolve_tencent_qq_exe()`：QQ / QQNT。
- `DOUYIN_EXE_PATH`、`_winreg_resolve_app_paths_exe`、`_winreg_douyin_from_uninstall`、`_resolve_douyin_exe_impl()`、`resolve_douyin_exe()`：抖音多策略查找（环境变量、PATH、App Paths、卸载表、ByteDance 目录）。
- `resolve_netease_cloud_exe()`：`cloudmusic.exe` 常见路径。

---

## 438–450：未配置服务时的用户可见提示常量

- `MSG_LLM_NOT_CONFIGURED`、`MSG_TRANSLATE_NOT_CONFIGURED`、`MSG_VISION_NEED_DASHSCOPE`：供 `task_parser` 在缺 Key 时返回友好说明。

---

## 维护建议

- 新增环境变量：在本文件集中声明并文档化，避免在业务文件散落 `os.environ.get`。
- 非 Windows 平台：`resolve_*_exe` 系列多返回 `None`，启动本机应用分支会走提示逻辑。

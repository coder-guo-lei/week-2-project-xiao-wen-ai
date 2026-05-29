# `backend/logic/task_parser.py` — 模块说明

> 本文件约 **3300+ 行**，为整个后端的**业务中枢**。下文给出：**文件头与导入**、**章节导读**、**全部顶层函数索引（行号）**、**`parse_command` 分支顺序**、**与其它模块的边界**。  
> 若需要「逐行」阅读，请在 IDE 中打开源文件并对照下列行号；不建议将三千行复制进 Markdown。

---

## 1. 文件头（约 1–83 行）

| 区间 | 内容 |
|------|------|
| 1 | 模块文档字符串。 |
| 2–14 | 标准库与三方：`requests`、`csv`、`json`、`re`、`subprocess`、`urllib`、`datetime`、`zoneinfo`（可选）、`zhdate`（可选）。 |
| 14 | `from pathlib import Path`：路径解析；本机应用 `exe:` 分支与图表上传等共用。 |
| 27–62 | 从 `config` 大量导入：高德/百炼/DeepSeek/超时/世界词表、各 `resolve_*_exe` 等（**不再**导入 `APP_LAUNCHERS`，改由 `user_apps.merge_launchers()` 统一提供合并表）。 |
| 63 | `import session`：读写 `WORLD_STATE`、`CHAT_HISTORY` 等。 |
| 64 | `from logic.user_apps import load_user_apps, merge_launchers`：用户白名单读取与合并。 |
| 66 | `logger`。 |
| 67–82 | **维护导读**：用编辑器搜索 `# ----------` 章节标题；列出天气、音乐、绘画、对话、本机应用、模拟世界、图表、`parse_command` 等块。 |

---

## 2. 章节结构（与源码内 `# ----------` 一致）

源码在约 163 行后进入 `is_music_intent` 等大段；文件中段用注释分隔「天气」「音乐」「文生图」「对话」「本机应用」「模拟世界」「图表」「指令解析核心」等（**以仓库内实际注释为准**）。

---

## 3. 顶层函数索引（`def` 起始行）

以下行号来自当前仓库 `task_parser.py` 的 `grep ^def` 结果，便于跳转。

| 行号 | 函数名 |
|------|--------|
| 85 | `primary_chat_model_label` |
| 99 | `openai_compat_chat` |
| 129 | `openai_compat_chat_fallback` |
| 153 | `workflow_steps` |
| 158 | `with_workflow` |
| 163 | `is_music_intent` |
| 332 | `sanitize_weather_city_fragment` |
| 353 | `extract_city_candidate` |
| 385 | `infer_city_from_single_task` |
| 398 | `infer_city_from_chat_history` |
| 436 | `short_city_label` |
| 448 | `get_weather_info` |
| 542 | `_amap_wgs84_to_gcj02` |
| 561 | `amap_regeocode_lng_lat` |
| 648 | `amap_nearby_dining` |
| 676 | `format_location_hint_for_llm` |
| 696 | `is_local_life_food_intent` |
| 711 | `compose_nearby_food_reply` |
| 736–751 | `_parse_temp_celsius`、`_parse_wind_power_level`、`_parse_humidity_pct`、`weather_outdoor_advice` |
| 796 | `is_weather_travel_intent` |
| 822 | `task_should_skip_weather_branch` |
| 842 | `weather_travel_fallback` |
| 867 | `compose_weather_travel_plan` |
| 894 | `build_weather_reply` |
| 927–1202 | 音乐：`_assistant_song_titles_in_order` … `search_music_url` |
| 1256–1368 | 文生图：`extract_image_prompt` … `generate_image` |
| 1387–1540 | 知识库与视觉：`split_text_chunks` … `analyze_uploaded_image` |
| 1581–1711 | 对话与翻译：`normalize_chat_history` … `translate_selected_text` |
| 1730–1999 | 本机应用：`extract_app_name` … `launch_local_app`、`wants_douyin_web_open` |
| 2016–2660 | 模拟世界：`detect_world_theme` … `apply_world_action` |
| 2825–3044 | 图表：`is_chart_intent` … `build_chart_payload` |
| 3048 | `is_goodbye_intent` |
| 3057 | **`parse_command`**（核心路由） |

（中间省略的函数名与上表连续块一致，完整列表可用仓库内 `rg "^def " backend/logic/task_parser.py` 重新生成。）

---

## 4. `parse_command(task, chat_history, client_location)` 分支顺序摘要

**先匹配的分支先生效**（见函数内 docstring，约 3057–3067 行）。

1. **`is_goodbye_intent`**：清空 `WORLD_STATE`、`CHAT_HISTORY`，`type: goodbye`，`resetUI`。
2. **若 `session.WORLD_STATE` 非空**：退出世界意图则清空并提示；否则 `apply_world_action`。
3. **`is_app_list_query`**：可启动应用列表。
4. **`is_knowledge_intent`**：知识库检索 + LLM 回答。
5. **`is_image_lookup_intent`**：百度图片搜索链接。
6. **`is_image_understanding_intent`**：URL 图片理解。
7. **`is_chart_intent`**：从指令文本解析图表数据或报错提示。
8. **天气**：`"天气" in task` 且非跳过分支 → `resolve_weather_city` → `get_weather_info` → `build_weather_reply` 等，`type: weather`，`extraData`。
9. **`parse_music_navigation`**：上一首/下一首控制。
10. **音乐点歌**：`is_music_intent` 或语言跟唱跟进 → `search_music_url`，`type: music` 或汽水音乐字段。
11. **`is_local_life_food_intent`**：需浏览器 `location` → 高德周边餐饮。
12. **`is_world_create_intent`**：创建文字世界。
13. **`is_image_intent`**：文生图 pending 或同步 URL。
14. **抖音网页**：`wants_douyin_web_open` 且「打开」类前缀。
15. **「打开」本机应用**：`launch_local_app` 白名单。
16. **泛化「打开」**：百度首页或百度搜索词。
17. **默认**：`format_location_hint_for_llm` + `ai_chat`（OpenAI 兼容接口 + 历史 + 服务端 `session.CHAT_HISTORY` 兜底）。

---

## 5. 与其它文件的关系

| 依赖方 | 调用内容 |
|--------|----------|
| `routes/api.py` | `parse_command`、`normalize_chat_history`、`remember_chat_turn`、图表/图片/翻译等若干函数。 |
| `app.py` | `primary_chat_model_label()` 仅日志。 |
| `session.py` | 世界状态、聊天历史、知识片段。 |
| `config.py` | 全部密钥与业务常量。 |
| `logic/user_apps.py` | `load_user_apps`（`supported_app_message`）、`merge_launchers`（`launch_local_app` 遍历键值对）。 |

---

## 5.1 用户应用白名单与 `exe:` 启动（`launch_local_app` / `supported_app_message`）

### `supported_app_message()`（约 1740–1756 行）

- 在原有内置应用名称列表基础上，调用 **`load_user_apps()`**；若非空，追加段落「你在本机添加的白名单应用：…」。
- 文末增加一句引导：在首页使用「浏览电脑添加应用」选好程序并起名后，可说「打开【你起的名字】」。

### `launch_local_app(task)`（约 1903 行起）

- **匹配表**：由 `for name, cmd in APP_LAUNCHERS.items()` 改为 **`for name, cmd in merge_launchers().items()`**，使自定义名称参与「打开某某」的模糊匹配（与原先一致：`name.lower() in app_name or app_name in name.lower()`）。
- **未匹配提示**：`supported = "、".join(sorted(merge_launchers().keys()))`，包含用户添加的键名。
- **新分支 `command.startswith("exe:")`**（位于 `resolve:` 分支之后、通用 `subprocess.Popen(command, shell=True)` 之前）：
  - 取 `exe_p = command[4:].strip()`，构造 `Path(exe_p)`。
  - 若文件仍存在且 **`_start_exe_best_effort(pp)`** 成功，返回「已为你打开：{matched_name}」。
  - 否则返回失败提示，引导用户到首页重新添加（路径失效或权限问题）。

**安全**：用户路径**不**走 `shell=True`，仅直接启动可执行文件，与内置 `resolve:*` 解析出的 exe 一致。

---

## 6. 修改建议

- 新增意图：在 `parse_command` **合适深度**插入 `if`，并抽独立 `is_*` / `handle_*` 保持单函数可读。
- 调整优先级：牢记**顺序即优先级**，避免天气误伤音乐等回归问题。

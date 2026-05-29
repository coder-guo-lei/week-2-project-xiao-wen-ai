# `backend/logic/user_apps.py` — 模块说明（完整）

## 1. 模块职责（总览）

本文件实现**用户自定义「打开某某」白名单**，与 `config.APP_LAUNCHERS`（系统内置记事本、微信等）**合并**后，供 `logic.task_parser.launch_local_app` 做名称匹配与启动。

设计要点：

- **持久化**：`backend/data/user_app_launchers.json`，UTF-8，人类可读 JSON。
- **值格式**：每条为 `exe:` + **规范化后的绝对路径**（与内置条目的 `notepad`、`resolve:wechat` 等区分，避免把用户路径当 shell 命令执行）。
- **选文件**：浏览器无法拿到真实磁盘路径，故由 **`pick_exe_windows_blocking()`** 在 Windows 上通过**子进程**运行 `scripts/pick_exe_dialog.py`（tkinter 原生对话框），父进程读 stdout 得到路径。
- **安全**：添加时校验路径为真实存在的文件；Windows 限定 `.exe`；显示名称禁止路径分隔符与若干特殊字符，且不得与 `APP_LAUNCHERS` 的键名（忽略大小写）冲突。

---

## 2. 常量与路径（第 1–15 行）

| 行号 | 代码 | 说明 |
|------|------|------|
| 1 | 模块 docstring | 说明本模块：持久化 JSON + 与内置表合并供 `launch_local_app` 使用。 |
| 2 | `from __future__ import annotations` | 推迟注解求值，便于前向引用与类型标注。 |
| 3 | （空行） | 分隔。 |
| 4–9 | `import json, os, re, subprocess, sys`；`from pathlib import Path` | JSON 读写、OS 判断、名称校验正则、子进程调对话框、可执行解释器路径、路径对象。 |
| 11 | `from config import APP_LAUNCHERS, BASE_DIR` | 内置启动表与 `backend` 目录根（`config.BASE_DIR`）。 |
| 12 | （空行） |  |
| 13 | `USER_APPS_PATH = BASE_DIR / "data" / "user_app_launchers.json"` | 用户白名单文件固定路径。 |
| 14 | `_PICK_SCRIPT = BASE_DIR / "scripts" / "pick_exe_dialog.py"` | 弹窗脚本路径，供子进程调用。 |
| 15 | （空行） |  |

---

## 3. `_ensure_data_dir()`（第 17–18 行）

| 行号 | 说明 |
|------|------|
| 17 | 函数定义：无参数，返回 `None`。 |
| 18 | `USER_APPS_PATH.parent.mkdir(parents=True, exist_ok=True)`：确保 `backend/data/` 存在，不因首次写入失败。 |

---

## 4. `load_user_apps()`（第 21–40 行）

| 行号 | 说明 |
|------|------|
| 21 | 函数定义；返回类型注解 `dict[str, str]`。 |
| 22 | Docstring：键为显示名称，值为 `'exe:绝对路径'`。 |
| 23 | 调用 `_ensure_data_dir()`。 |
| 24–25 | 若 JSON 文件不存在，返回空字典。 |
| 26–28 | `try`：`json.loads` 读文件，`encoding="utf-8"`。 |
| 28 | 若根不是 `dict`，返回 `{}`（防止文件被改坏）。 |
| 30–37 | 遍历键值：仅保留 `str` 键值、`key` 去空白非空、`val` 以 `exe:` 开头；其余丢弃（兼容旧数据或手改错误）。 |
| 38 | 返回清洗后的 `out`。 |
| 39–40 | `OSError` / `JSONDecodeError` 时返回 `{}`，避免整站崩溃。 |

---

## 5. `save_user_apps(apps)`（第 43–45 行）

| 行号 | 说明 |
|------|------|
| 43 | 接收完整字典，覆盖写文件。 |
| 44 | 再次确保目录存在。 |
| 45 | `write_text`：`indent=2`、`ensure_ascii=False` 便于中文阅读与版本管理。 |

---

## 6. `merge_launchers()`（第 48–52 行）

| 行号 | 说明 |
|------|------|
| 48 | 函数定义。 |
| 49 | Docstring：先拷贝内置表，再 `update` 用户表；若用户键与内置同名，理论上用户覆盖内置，但 **`add_user_app` 禁止与内置同名**，故正常数据下用户表只增新键。 |
| 50 | `merged = dict(APP_LAUNCHERS)` 浅拷贝内置。 |
| 51 | `merged.update(load_user_apps())` 叠用户条目。 |
| 52 | 返回合并后的字典，供 `launch_local_app` 遍历匹配。 |

---

## 7. `validate_exe_path(path)`（第 55–65 行）

| 行号 | 说明 |
|------|------|
| 55 | 返回 `(bool, str)`：成功时第二元组为规范化绝对路径字符串，失败时为错误文案。 |
| 56 | `Path(path).expanduser()` 展开 `~`。 |
| 57–60 | `resolve()` 取真实路径；`OSError`（无效路径）返回失败。 |
| 61–62 | 必须 `is_file()`，排除目录与不存在。 |
| 63–64 | **Windows**（`os.name == "nt"`）要求后缀为 `.exe`，防止误加脚本或其它格式。 |
| 65 | 成功返回 `(True, str(p))`。 |

---

## 8. `validate_display_name(name)`（第 68–76 行）

| 行号 | 说明 |
|------|------|
| 69 | 去首尾空白。 |
| 70–71 | 长度 1～24。 |
| 72–73 | 禁止 `/ \ : < > \| "`，避免名称被误用为路径或注入感。 |
| 74–75 | 正则：中文、单词字符、空格、短横线、间隔号 `·`。 |
| 76 | 成功返回 `(True, n)`。 |

---

## 9. `add_user_app(name, exe_path)`（第 79–94 行）

| 行号 | 说明 |
|------|------|
| 80–83 | 先校验 exe 路径，失败直接返回。 |
| 84–86 | 再校验显示名。 |
| 87–88 | 与 **`APP_LAUNCHERS` 所有键**忽略大小写比较，冲突则拒绝（保护「记事本」等内置名）。 |
| 89–91 | 与**已有用户键**忽略大小写比较，重复则拒绝（避免重复条目；需改路径可先删再加）。 |
| 92 | 写入 `exe:{path}`，`path` 已为 `validate_exe_path` 解析后的绝对路径。 |
| 93 | `save_user_apps`。 |
| 94 | 成功消息中提示语音说法：`打开{name_clean}`。 |

---

## 10. `remove_user_app(name)`（第 97–111 行）

| 行号 | 说明 |
|------|------|
| 98–100 | 空名称直接失败。 |
| 101 | 加载当前用户表。 |
| 102–106 | 按**忽略大小写**查找第一个匹配的键 `hit`。 |
| 107–108 | 未找到则提示仅可移除自行添加项（内置不在此 JSON 中）。 |
| 109–110 | 删除并保存。 |
| 111 | 返回成功文案（使用磁盘上真实键名 `hit`）。 |

---

## 11. `pick_exe_windows_blocking()`（第 114–135 行）

| 行号 | 说明 |
|------|------|
| 115–117 | 非 Windows 或脚本不存在则返回 `None`。 |
| 120–126 | `subprocess.run([sys.executable, str(_PICK_SCRIPT)], ...)`：`capture_output=True` 读路径，`text=True` 文本模式，`timeout=600` 秒（用户可能长时间浏览文件夹）。 |
| 127–128 | 超时返回 `None`。 |
| 129–130 | 子进程以退出码 **3** 表示未安装 tkinter（与 `pick_exe_dialog.py` 一致），返回 `None`。 |
| 131–133 | stdout 去空白为空则视为取消。 |
| 134–135 | 再次 `validate_exe_path`，通过则返回规范化路径，否则 `None`。 |

**注意**：该函数会阻塞当前 Flask 工作线程直到用户关闭对话框；本机单用户使用可接受。

---

## 12. `user_apps_public_list()`（第 138–144 行）

| 行号 | 说明 |
|------|------|
| 138 | 供 `GET /api/user-apps` 给前端列表展示。 |
| 141 | 按显示名**不区分大小写**排序。 |
| 142 | 去掉 `exe:` 前缀得到纯路径，便于 UI `title` 展示。 |
| 143 | 每项 `{ "name", "path" }`。 |

---

## 13. 与 `task_parser.launch_local_app` 的衔接

- `launch_local_app` 遍历 **`merge_launchers()`** 而非仅 `APP_LAUNCHERS`。
- 当匹配到的 `command` 以 **`exe:`** 开头时，走 **`_start_exe_best_effort(Path(...))`** 分支（与解析出的微信 exe 同源），不再 `subprocess.Popen(command, shell=True)`，避免 shell 注入。

详见 [logic-task_parser-模块说明.md](./logic-task_parser-模块说明.md) 中的「用户应用白名单与 `exe:` 启动」一节。

---

## 14. 与 `routes/api.py` 的衔接

详见 [routes-api-模块说明.md](./routes-api-模块说明.md) 中的「用户应用白名单 API」一节。

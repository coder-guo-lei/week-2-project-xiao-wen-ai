# `backend/data/` — 用户应用白名单数据说明

## 1. 目录作用

- **`backend/data/`**：存放后端运行时生成的、**可随用户操作变化**的持久化数据（与代码分离）。
- **`backend/data/.gitkeep`**：空文件，使空目录在 Git 中仍被跟踪；首次克隆后目录存在，避免首次写入 JSON 时父目录缺失（实际写入前 `user_apps._ensure_data_dir()` 也会 `mkdir`）。

---

## 2. `user_app_launchers.json`（运行时生成）

### 2.1 路径

`backend/data/user_app_launchers.json`（由 `logic.user_apps.USER_APPS_PATH` 定义）。

### 2.2 文件格式

顶层为 **JSON 对象**：

- **键（string）**：用户对小文说的**显示名称**（例如 `原神`、`剪映`），与 `add_user_app` 校验规则一致。
- **值（string）**：固定前缀 **`exe:`** + **规范化后的绝对路径**（Windows 下为 `.exe` 的 `resolve()` 结果）。

示例：

```json
{
  "原神": "exe:D:\\Games\\Genshin Impact\\GenshinImpact.exe",
  "剪映专业版": "exe:C:\\Program Files\\JianyingPro\\JianyingPro.exe"
}
```

### 2.3 读写方

| 操作 | 代码位置 |
|------|----------|
| 读 | `logic.user_apps.load_user_apps()` |
| 写 | `logic.user_apps.save_user_apps()`，由 `add_user_app` / `remove_user_app` 调用 |
| 合并进启动逻辑 | `merge_launchers()` → `task_parser.launch_local_app` |

### 2.4 与内置表的关系

- **`config.APP_LAUNCHERS`**：仓库内置，不写本文件。
- **本 JSON**：仅用户通过前端「浏览添加」或未来若支持手工编辑时的条目。
- **合并规则**：`merge_launchers()` = 拷贝内置 + `update(用户表)`；添加接口禁止用户键与内置键名忽略大小写重复。

### 2.5 备份与迁移

- 换机或重装时可复制本 JSON 到新机同路径；路径若失效，`launch_local_app` 会提示重新添加。
- 若需纳入版本控制，可自行去掉 `.gitignore`（当前仓库未强制忽略该 JSON，由团队策略决定）。

---

## 3. 安全与运维注意

- 仅应出现 **`exe:`** 前缀的可执行路径；若手工编辑混入其它字符串，`load_user_apps` 会过滤非 `exe:` 值。
- 多 worker 部署（如 gunicorn 多进程）时，文件写入无分布式锁；本功能面向**本机单用户**场景，一般单进程 Flask 即可。

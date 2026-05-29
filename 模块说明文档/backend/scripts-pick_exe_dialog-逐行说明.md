# `backend/scripts/pick_exe_dialog.py` — 逐行说明

本脚本**不作为 Flask 模块被 import**，而是由 `logic.user_apps.pick_exe_windows_blocking()` 通过 **`subprocess.run([sys.executable, 本脚本路径])`** 单独启动。这样 tkinter 图形界面运行在子进程内，避免与 Flask 主线程、异步模型冲突；选定的路径通过 **stdout** 回传给父进程。

---

| 行号 | 代码 | 说明 |
|------|------|------|
| 1 | `"""..."""` | 文档字符串：说明用途为独立子进程、打印路径到 stdout。 |
| 2 | `import sys` | 退出码与标准输出。 |
| 3 | （空行） |  |
| 4 | （空行） |  |
| 5 | `def main() -> None:` | 入口函数，无返回值有意义，副作用为写 stdout / 进程退出码。 |
| 6 | `try:` | 尝试导入 GUI 库。 |
| 7 | `import tkinter as tk` | Tk 根窗口类。 |
| 8 | `from tkinter import filedialog` | 系统风格文件选择对话框。 |
| 9 | `except ImportError:` | 精简版 Python 或未带 Tcl/Tk 时无 tkinter。 |
| 10 | `sys.exit(3)` | **约定退出码 3**：父进程 `user_apps.py` 据此判断「无法弹窗」，与「用户取消（stdout 空）」区分。 |
| 11 | `root = tk.Tk()` | 创建隐藏根窗口（filedialog 依赖 Tk 事件循环上下文）。 |
| 12 | `root.withdraw()` | 不显示空白主窗口，仅保留对话框。 |
| 13 | `try:` | 置顶属性在极少数环境可能抛 `TclError`。 |
| 14 | `root.attributes("-topmost", True)` | 对话框尽量浮于最前，避免被浏览器或其它窗口完全挡住。 |
| 15 | `except tk.TclError:` | 忽略置顶失败。 |
| 16 | `pass` | 空分支占位。 |
| 17 | `path = filedialog.askopenfilename(` | 阻塞直到用户选择或取消。 |
| 18 | `title="..."` | 对话框标题，提示用途。 |
| 19 | `filetypes=[("可执行文件", "*.exe"), ("所有文件", "*.*")]` | 默认筛选 exe；仍允许「所有文件」以防扩展名特殊。 |
| 20 | `)` | 结束 `askopenfilename` 调用。 |
| 21 | `try:` | 销毁根窗口。 |
| 22 | `root.destroy()` | 释放 Tk 资源。 |
| 23 | `except tk.TclError:` | 已销毁等情况忽略。 |
| 24 | `pass` |  |
| 25 | `sys.stdout.write((path or "").strip())` | 将路径（或空字符串）写入 stdout；**无换行**，父进程用 `strip()` 读取。 |
| 26 | `sys.stdout.flush()` | 确保缓冲区立即写出，父进程 `communicate` / `read` 不挂起。 |
| 27 | （空行） |  |
| 28 | （空行） |  |
| 29 | `if __name__ == "__main__":` | 仅在被直接执行时运行（被子进程 `python pick_exe_dialog.py` 满足）。 |
| 30 | `main()` | 调用上述逻辑。 |
| 31 | （文件末） | 正常结束退出码为 0；未走 `sys.exit(3)` 即表示 tkinter 可用。 |

---

## 与父进程的契约

1. **成功选择**：stdout 为**单行**绝对路径字符串（可含空格，已由 `strip()` 处理）；退出码 `0`。
2. **取消选择**：stdout 为空或仅空白；退出码 `0`。
3. **无 tkinter**：`sys.exit(3)`，父进程不解析 stdout 路径。

父进程随后对 stdout 内容调用 `validate_exe_path`，再次保证为真实 `.exe` 文件（Windows）。

---

## 依赖与环境

- Windows 桌面会话：无显示器/远程仅 SSH 时对话框无法使用，与 `user_apps_pick_exe` 返回的说明文案一致。
- Python 安装需包含 **Tcl/Tk**（Windows 官方安装包通常自带）。

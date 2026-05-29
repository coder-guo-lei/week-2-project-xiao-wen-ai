"""独立子进程：弹出系统「打开文件」对话框，把所选路径打印到 stdout（供 Flask 调用）。"""
import sys


def main() -> None:
    try:
        import tkinter as tk
        from tkinter import filedialog
    except ImportError:
        sys.exit(3)
    root = tk.Tk()
    root.withdraw()
    try:
        root.attributes("-topmost", True)
    except tk.TclError:
        pass
    path = filedialog.askopenfilename(
        title="选择要加入小文白名单的程序（.exe）",
        filetypes=[("可执行文件", "*.exe"), ("所有文件", "*.*")],
    )
    try:
        root.destroy()
    except tk.TclError:
        pass
    sys.stdout.write((path or "").strip())
    sys.stdout.flush()


if __name__ == "__main__":
    main()

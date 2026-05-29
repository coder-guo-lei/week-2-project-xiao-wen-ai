"""用户自定义「打开应用」白名单：持久化 JSON + 与 config.APP_LAUNCHERS 合并供 launch_local_app 使用。"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

from config import APP_LAUNCHERS, BASE_DIR

USER_APPS_PATH = BASE_DIR / "data" / "user_app_launchers.json"
_PICK_SCRIPT = BASE_DIR / "scripts" / "pick_exe_dialog.py"


def _ensure_data_dir() -> None:
    USER_APPS_PATH.parent.mkdir(parents=True, exist_ok=True)


def load_user_apps() -> dict[str, str]:
    """返回 { 显示名称: 'exe:绝对路径' }。"""
    _ensure_data_dir()
    if not USER_APPS_PATH.is_file():
        return {}
    try:
        raw = json.loads(USER_APPS_PATH.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            return {}
        out: dict[str, str] = {}
        for k, v in raw.items():
            if not isinstance(k, str) or not isinstance(v, str):
                continue
            key = k.strip()
            val = v.strip()
            if key and val.startswith("exe:"):
                out[key] = val
        return out
    except (OSError, json.JSONDecodeError):
        return {}


def save_user_apps(apps: dict[str, str]) -> None:
    _ensure_data_dir()
    USER_APPS_PATH.write_text(json.dumps(apps, ensure_ascii=False, indent=2), encoding="utf-8")


def merge_launchers() -> dict[str, str]:
    """内置白名单 + 用户条目（用户键与内置冲突时以用户为准，但添加接口会禁止覆盖内置）。"""
    merged = dict(APP_LAUNCHERS)
    merged.update(load_user_apps())
    return merged


def validate_exe_path(path: str) -> tuple[bool, str]:
    p = Path(path).expanduser()
    try:
        p = p.resolve()
    except OSError:
        return False, "路径无效"
    if not p.is_file():
        return False, "路径不存在或不是文件"
    if os.name == "nt" and p.suffix.lower() != ".exe":
        return False, "Windows 下仅支持 .exe 可执行文件"
    return True, str(p)


def validate_display_name(name: str) -> tuple[bool, str]:
    n = (name or "").strip()
    if not n or len(n) > 24:
        return False, "显示名称为 1～24 个字符"
    if any(c in n for c in ("/", "\\", ":", "<", ">", "|", '"')):
        return False, "名称不能包含路径或特殊符号"
    if not re.match(r"^[\w\u4e00-\u9fff\-\s·]+$", n):
        return False, "名称仅支持中文、字母、数字、下划线、空格、短横线、间隔号"
    return True, n


def add_user_app(name: str, exe_path: str) -> tuple[bool, str]:
    ok, path_or_err = validate_exe_path(exe_path)
    if not ok:
        return False, path_or_err
    path = path_or_err
    ok, name_clean = validate_display_name(name)
    if not ok:
        return False, name_clean
    if any(k.lower() == name_clean.lower() for k in APP_LAUNCHERS):
        return False, "该名称与系统内置应用重名，请换一个显示名称"
    apps = load_user_apps()
    if any(k.lower() == name_clean.lower() for k in apps):
        return False, "白名单中已有同名应用，可先移除再添加"
    apps[name_clean] = f"exe:{path}"
    save_user_apps(apps)
    return True, f"已添加「{name_clean}」。可以说：打开{name_clean}"


def remove_user_app(name: str) -> tuple[bool, str]:
    key = (name or "").strip()
    if not key:
        return False, "请提供要移除的名称"
    apps = load_user_apps()
    hit = None
    for k in apps:
        if k.lower() == key.lower():
            hit = k
            break
    if hit is None:
        return False, "白名单中没有该应用（仅可移除你自行添加的项）"
    del apps[hit]
    save_user_apps(apps)
    return True, f"已移除「{hit}」"


def pick_exe_windows_blocking() -> str | None:
    """Windows：子进程弹出原生选择框，返回绝对路径；取消或失败返回 None。"""
    if os.name != "nt":
        return None
    if not _PICK_SCRIPT.is_file():
        return None
    try:
        cp = subprocess.run(
            [sys.executable, str(_PICK_SCRIPT)],
            capture_output=True,
            text=True,
            timeout=600,
        )
    except subprocess.TimeoutExpired:
        return None
    if cp.returncode == 3:
        return None
    out = (cp.stdout or "").strip()
    if not out:
        return None
    ok, path = validate_exe_path(out)
    return path if ok else None


def user_apps_public_list() -> list[dict[str, str]]:
    """供前端展示：剥离 exe: 前缀。"""
    rows = []
    for name, cmd in sorted(load_user_apps().items(), key=lambda x: x[0].lower()):
        p = cmd[4:].strip() if cmd.startswith("exe:") else cmd
        rows.append({"name": name, "path": p})
    return rows

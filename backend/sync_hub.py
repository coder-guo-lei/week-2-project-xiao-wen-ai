"""多端状态 WebSocket 同步：日志、主题、用户偏好。"""

import json
import logging
import threading

from flask_sock import Sock

from logic.user_preferences import DEFAULT_PREFERENCES, normalize_preferences

logger = logging.getLogger(__name__)

sock = Sock()

DEFAULT_LOGS = ["✅ 小文AI助手已就绪"]
MAX_LOGS = 300
DEFAULT_THEME = "system"
VALID_THEMES = frozenset({"light", "dark", "system"})

_lock = threading.Lock()
_clients: set = set()
_sync_logs: list[str] = list(DEFAULT_LOGS)
_sync_theme: str = DEFAULT_THEME
_sync_preferences: dict = dict(DEFAULT_PREFERENCES)


def _send(ws, msg: dict) -> None:
    try:
        ws.send(json.dumps(msg, ensure_ascii=False))
    except Exception as exc:
        logger.debug("ws send failed: %s", exc)


def _broadcast(msg: dict, *, exclude=None) -> None:
    payload = json.dumps(msg, ensure_ascii=False)
    with _lock:
        dead = []
        for client in _clients:
            if client is exclude:
                continue
            try:
                client.send(payload)
            except Exception:
                dead.append(client)
        for client in dead:
            _clients.discard(client)


@sock.route("/ws/sync")
def sync_ws(ws):
    global _sync_theme, _sync_preferences
    with _lock:
        _clients.add(ws)
        logs_snapshot = list(_sync_logs)
        theme_snapshot = _sync_theme
        prefs_snapshot = dict(_sync_preferences)

    _send(ws, {
        "type": "SYNC_INIT",
        "payload": {
            "logs": logs_snapshot,
            "theme": theme_snapshot,
            "preferences": prefs_snapshot,
        },
    })

    try:
        while True:
            raw = ws.receive()
            if raw is None:
                break
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue

            msg_type = msg.get("type")
            payload = msg.get("payload")

            if msg_type == "LOG_APPEND" and isinstance(payload, str) and payload.strip():
                with _lock:
                    _sync_logs.append(payload)
                    if len(_sync_logs) > MAX_LOGS:
                        _sync_logs[:] = _sync_logs[-MAX_LOGS:]
                _broadcast({"type": "LOG_APPEND", "payload": payload}, exclude=ws)

            elif msg_type == "LOG_CLEAR":
                with _lock:
                    _sync_logs.clear()
                _broadcast({"type": "LOG_CLEAR"}, exclude=ws)

            elif msg_type == "THEME_SET" and isinstance(payload, str) and payload in VALID_THEMES:
                with _lock:
                    _sync_theme = payload
                _broadcast({"type": "THEME_SET", "payload": payload}, exclude=ws)

            elif msg_type == "PREF_SET" and isinstance(payload, dict):
                with _lock:
                    _sync_preferences = normalize_preferences(payload)
                _broadcast({
                    "type": "PREF_SET",
                    "payload": dict(_sync_preferences),
                }, exclude=ws)

    finally:
        with _lock:
            _clients.discard(ws)

"""对话智能化：滑动窗口 + 摘要压缩 + 状态机。"""

from __future__ import annotations

import logging
from typing import Any

import session
from config import (
    DIALOGUE_COMPRESS_ENABLED,
    DIALOGUE_COMPRESS_MIN_MESSAGES,
    DIALOGUE_STATE_HINTS,
    DIALOGUE_STORE_MESSAGES,
    DIALOGUE_SUMMARY_MAX_CHARS,
    DIALOGUE_WINDOW_MESSAGES,
    MAX_CHAT_MESSAGE_CHARS,
)

logger = logging.getLogger(__name__)

# ---------- 对话状态机 ----------
STATE_IDLE = "idle"
STATE_CHATTING = "chatting"
STATE_MUSIC = "music"
STATE_WEATHER = "weather"
STATE_FOOD = "food"
STATE_KNOWLEDGE = "knowledge"
STATE_IMAGE = "image"
STATE_TASK = "task"

_INTENT_TO_STATE: dict[str, str] = {
    "music": STATE_MUSIC,
    "music_nav": STATE_MUSIC,
    "weather": STATE_WEATHER,
    "local_food": STATE_FOOD,
    "knowledge": STATE_KNOWLEDGE,
    "image_generate": STATE_IMAGE,
    "image_lookup": STATE_IMAGE,
    "image_understanding": STATE_IMAGE,
    "chart": STATE_TASK,
    "app_launch": STATE_TASK,
    "web_open": STATE_TASK,
    "app_list": STATE_TASK,
    "chat": STATE_CHATTING,
}

_RESPONSE_TO_STATE: dict[str, str] = {
    "music": STATE_MUSIC,
    "music_control": STATE_MUSIC,
    "weather": STATE_WEATHER,
    "chat": STATE_CHATTING,
    "knowledge": STATE_KNOWLEDGE,
    "image": STATE_IMAGE,
    "image_pending": STATE_IMAGE,
    "web": STATE_TASK,
    "app": STATE_TASK,
    "chart": STATE_TASK,
    "goodbye": STATE_IDLE,
}


def _ensure_dialogue_session() -> None:
    if not hasattr(session, "DIALOGUE_STATE"):
        session.DIALOGUE_STATE = STATE_IDLE
    if not hasattr(session, "DIALOGUE_SUMMARY"):
        session.DIALOGUE_SUMMARY = ""
    if not hasattr(session, "DIALOGUE_TURN_COUNT"):
        session.DIALOGUE_TURN_COUNT = 0


def normalize_messages(history: list | None) -> list[dict[str, str]]:
    """清洗对话历史，只保留 user/assistant 文本。"""
    if not isinstance(history, list):
        return []
    out: list[dict[str, str]] = []
    for item in history:
        if not isinstance(item, dict):
            continue
        role = item.get("role")
        content = str(item.get("content") or "").strip()
        if role not in {"user", "assistant"} or not content:
            continue
        out.append({"role": role, "content": content[:MAX_CHAT_MESSAGE_CHARS]})
    return out


class DialogueManager:
    """进程内单例对话管理器（状态存 session）。"""

    def reset(self) -> None:
        _ensure_dialogue_session()
        session.DIALOGUE_STATE = STATE_IDLE
        session.DIALOGUE_SUMMARY = ""
        session.DIALOGUE_TURN_COUNT = 0
        session.CHAT_HISTORY = []

    @property
    def state(self) -> str:
        _ensure_dialogue_session()
        return session.DIALOGUE_STATE or STATE_IDLE

    @property
    def summary(self) -> str:
        _ensure_dialogue_session()
        return (session.DIALOGUE_SUMMARY or "").strip()

    def transition(self, intent: str | None = None, response_type: str | None = None) -> str:
        """根据意图与响应类型更新状态机，返回新状态。"""
        _ensure_dialogue_session()
        prev = session.DIALOGUE_STATE or STATE_IDLE

        if response_type == "goodbye":
            new_state = STATE_IDLE
        elif intent and intent in _INTENT_TO_STATE:
            mapped = _INTENT_TO_STATE[intent]
            if mapped != STATE_CHATTING:
                new_state = mapped
            elif prev in (STATE_MUSIC, STATE_WEATHER, STATE_FOOD, STATE_KNOWLEDGE, STATE_IMAGE, STATE_TASK):
                new_state = prev
            else:
                new_state = STATE_CHATTING
        elif response_type and response_type in _RESPONSE_TO_STATE:
            new_state = _RESPONSE_TO_STATE[response_type]
        else:
            new_state = prev if prev != STATE_IDLE else STATE_CHATTING

        session.DIALOGUE_STATE = new_state
        return new_state

    def sync_frontend_history(self, frontend_history: list | None) -> list[dict[str, str]]:
        """合并前端 history 与服务端存储，以较长者为准并截断到 STORE 上限。"""
        _ensure_dialogue_session()
        fe = normalize_messages(frontend_history)
        server = normalize_messages(session.CHAT_HISTORY)
        merged = fe if len(fe) >= len(server) else server
        if merged:
            session.CHAT_HISTORY = merged[-DIALOGUE_STORE_MESSAGES:]
        return list(session.CHAT_HISTORY)

    def resolve_history(self, frontend_history: list | None = None) -> list[dict[str, str]]:
        if frontend_history is not None:
            return self.sync_frontend_history(frontend_history)
        _ensure_dialogue_session()
        return list(session.CHAT_HISTORY)

    def record_turn(self, user_text: str, assistant_text: str) -> None:
        """追加一轮对话并维护滑动存储；超出阈值时触发摘要压缩。"""
        user_text = str(user_text or "").strip()
        assistant_text = str(assistant_text or "").strip()
        if not user_text or not assistant_text:
            return
        _ensure_dialogue_session()
        session.CHAT_HISTORY.extend([
            {"role": "user", "content": user_text[:MAX_CHAT_MESSAGE_CHARS]},
            {"role": "assistant", "content": assistant_text[:MAX_CHAT_MESSAGE_CHARS]},
        ])
        session.CHAT_HISTORY = session.CHAT_HISTORY[-DIALOGUE_STORE_MESSAGES:]
        session.DIALOGUE_TURN_COUNT = int(session.DIALOGUE_TURN_COUNT or 0) + 1
        if self.state == STATE_IDLE:
            session.DIALOGUE_STATE = STATE_CHATTING
        self._compress_if_needed()

    def build_context_messages(self, frontend_history: list | None = None) -> list[dict[str, str]]:
        """构建送入 LLM 的上下文：摘要块 + 滑动窗口内最近消息。"""
        history = self.resolve_history(frontend_history)
        self._compress_if_needed()
        history = session.CHAT_HISTORY[-DIALOGUE_STORE_MESSAGES:]
        window = history[-DIALOGUE_WINDOW_MESSAGES:]

        messages: list[dict[str, str]] = []
        summary = self.summary
        if summary:
            messages.append({
                "role": "system",
                "content": f"【此前对话摘要（供延续上下文，勿向用户复述摘要本身）】\n{summary[:DIALOGUE_SUMMARY_MAX_CHARS]}",
            })
        messages.extend(window)
        return messages

    def state_hint_for_system(self) -> str:
        """状态机提示：注入 system，帮助模型理解当前对话场景。"""
        if not DIALOGUE_STATE_HINTS:
            return ""
        hints = {
            STATE_IDLE: "",
            STATE_CHATTING: "当前为自由闲聊，可简短友好作答。",
            STATE_MUSIC: "用户刚涉及音乐播放/切歌，可能继续点歌、换语种或讨论歌曲。",
            STATE_WEATHER: "用户刚查过天气，可能追问出行、穿衣或同城对比。",
            STATE_FOOD: "用户刚问附近美食或饿了，可能继续追问口味、预算或具体店名。",
            STATE_KNOWLEDGE: "用户刚进行知识库问答，回答宜引用文档风格、条理清晰。",
            STATE_IMAGE: "用户刚涉及图片生成/搜图/识图，可能继续改提示词或追问结果。",
            STATE_TASK: "用户刚完成一项工具型任务，可能追问操作结果或同类需求。",
        }
        hint = hints.get(self.state, "")
        if not hint:
            return ""
        return f"【对话状态】{self.state}。{hint}"

    def context_label(self) -> str:
        """供 workflow 展示的人类可读上下文说明。"""
        parts = [f"窗口最近 {min(len(session.CHAT_HISTORY), DIALOGUE_WINDOW_MESSAGES)} 条"]
        if self.summary:
            parts.append("含历史摘要")
        if self.state != STATE_IDLE:
            parts.append(f"状态={self.state}")
        return "；".join(parts)

    def _compress_if_needed(self) -> None:
        if not DIALOGUE_COMPRESS_ENABLED:
            return
        _ensure_dialogue_session()
        history = session.CHAT_HISTORY
        if len(history) <= DIALOGUE_COMPRESS_MIN_MESSAGES:
            return
        keep = history[-DIALOGUE_WINDOW_MESSAGES:]
        older = history[:-DIALOGUE_WINDOW_MESSAGES]
        if not older:
            return

        new_summary = self._summarize_messages(older, session.DIALOGUE_SUMMARY or "")
        if new_summary:
            session.DIALOGUE_SUMMARY = new_summary[:DIALOGUE_SUMMARY_MAX_CHARS]
            session.CHAT_HISTORY = keep
            logger.info(
                "dialogue compressed %d msgs -> summary len=%d, keep=%d",
                len(older),
                len(session.DIALOGUE_SUMMARY),
                len(keep),
            )

    def _summarize_messages(self, messages: list[dict[str, str]], prior_summary: str) -> str | None:
        from logic.task_parser import openai_compat_chat_fallback

        lines = []
        if prior_summary:
            lines.append(f"已有摘要：{prior_summary[:800]}")
        lines.append("待压缩的新对话：")
        for m in messages[-40:]:
            role = "用户" if m["role"] == "user" else "小文"
            lines.append(f"{role}：{m['content'][:400]}")
        prompt = "\n".join(lines)
        out = openai_compat_chat_fallback(
            [
                {
                    "role": "system",
                    "content": (
                        "你是小文助手的对话记忆模块。将给定对话压缩为简洁中文摘要（150～350字），"
                        "保留：用户偏好、已讨论主题、关键事实、未完成话题。不要编造。只输出摘要正文。"
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )
        return out.strip() if out else prior_summary or None


_manager: DialogueManager | None = None


def get_dialogue_manager() -> DialogueManager:
    global _manager
    if _manager is None:
        _manager = DialogueManager()
    return _manager

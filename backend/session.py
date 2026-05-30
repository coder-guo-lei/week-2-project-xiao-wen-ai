"""进程内可变会话状态（模拟世界、聊天兜底上下文、知识库缓存、对话管理）。由 logic 模块读写。"""

WORLD_STATE = None
CHAT_HISTORY: list = []
KNOWLEDGE_SNIPPETS: list = []

# DialogueManager 状态机与摘要
DIALOGUE_STATE = "idle"
DIALOGUE_SUMMARY = ""
DIALOGUE_TURN_COUNT = 0
LAST_INTENT: str | None = None

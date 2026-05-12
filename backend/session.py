"""进程内可变会话状态（模拟世界、聊天兜底上下文、知识库缓存）。由 logic.task_parser 读写。"""

WORLD_STATE = None
CHAT_HISTORY: list = []
KNOWLEDGE_SNIPPETS: list = []

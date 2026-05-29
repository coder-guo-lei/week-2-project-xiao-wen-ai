# `backend/session.py` — 逐行说明

源文件仅进程内可变状态，由 `logic.task_parser` 读写；**非**多用户会话隔离（单机演示架构）。

| 行号 | 代码含义 |
|------|----------|
| 1 | 文档字符串：说明用途及读写方。 |
| 3 | `WORLD_STATE = None`：文字模拟世界当前状态字典；`None` 表示未进入世界模式。 |
| 4 | `CHAT_HISTORY: list = []`：服务端兜底的多轮对话缓存（与前端传来的 `history` 协同）。 |
| 5 | `KNOWLEDGE_SNIPPETS: list = []`：知识库检索片段缓存列表。 |

## 注意

- 多 worker 部署时每个进程有独立内存，此「会话」不会在进程间共享；若需多用户应改为 Redis/DB 会话存储。

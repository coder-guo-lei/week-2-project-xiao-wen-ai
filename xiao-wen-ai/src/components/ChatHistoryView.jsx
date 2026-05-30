/**
 * ChatHistoryView — 用户与小文的多轮对话记录（气泡列表）
 */
import { useEffect, useMemo, useRef } from 'react'
import { renderTextWithLinks } from '../utils/textWithLinks'
import { normalizeHistory } from '../utils/chatExport'
import './ChatHistoryView.css'

/** 合并持久化 history 与当前 reply（避免刷新前一帧不同步） */
function buildDisplayMessages(history, reply) {
  const list = normalizeHistory(history)
  const latest = String(reply ?? '').trim()
  if (!latest) return list

  const last = list[list.length - 1]
  if (last?.role === 'assistant' && String(last.content).trim() === latest) {
    return list
  }
  if (last?.role === 'assistant') {
    return [...list.slice(0, -1), { role: 'assistant', content: latest }]
  }
  if (last?.role === 'user') {
    return [...list, { role: 'assistant', content: latest }]
  }
  return [...list, { role: 'assistant', content: latest }]
}

export default function ChatHistoryView({ history, reply, maxRoundsHint = 6 }) {
  const scrollRef = useRef(null)
  const messages = useMemo(() => buildDisplayMessages(history, reply), [history, reply])
  const turnCount = useMemo(() => {
    let n = 0
    for (let i = 0; i < messages.length; i++) {
      if (messages[i].role === 'user') n += 1
    }
    return n
  }, [messages])

  useEffect(() => {
    const el = scrollRef.current
    if (!el) return
    el.scrollTop = el.scrollHeight
  }, [messages.length, reply])

  return (
    <div className="chv">
      <div className="chv-meta">
        <span>{messages.length > 0 ? `共 ${turnCount} 轮对话` : '暂无对话'}</span>
        {messages.length > 0 && (
          <span className="chv-meta-hint">本地保留最近 {maxRoundsHint} 轮</span>
        )}
      </div>
      <div className="chv-scroll" ref={scrollRef}>
        {messages.length === 0 ? (
          <div className="chv-empty">
            <p>还没有对话记录</p>
            <p className="chv-empty-sub">在上方输入指令开始与小文聊天，历史会显示在这里</p>
          </div>
        ) : (
          <ul className="chv-list">
            {messages.map((msg, index) => {
              const isUser = msg.role === 'user'
              return (
                <li
                  key={`${index}-${msg.role}-${String(msg.content).slice(0, 32)}`}
                  className={`chv-item chv-item--${msg.role}`}
                >
                  <div className="chv-item-inner">
                    <span className="chv-avatar" aria-hidden>
                      {isUser ? '你' : '小文'}
                    </span>
                    <div className="chv-bubble">
                      <span className="chv-role">{isUser ? '你' : '小文'}</span>
                      <div className="chv-content">{renderTextWithLinks(msg.content)}</div>
                    </div>
                  </div>
                </li>
              )
            })}
          </ul>
        )}
      </div>
    </div>
  )
}

import { useState, useEffect, useCallback } from 'react'
import { apiFetch } from '../apiBase'
import './ChatHistoryPanel.css'

export default function ChatHistoryPanel() {
  const [logs, setLogs] = useState([])
  const [sessions, setSessions] = useState([])
  const [activeSessionId, setActiveSessionId] = useState(null)
  const [page, setPage] = useState(1)
  const [hasMore, setHasMore] = useState(false)
  const [loading, setLoading] = useState(false)
  const [total, setTotal] = useState(0)

  const pageSize = 30

  const fetchLogs = useCallback(
    async (pageNum, sid, append = false) => {
      setLoading(true)
      try {
        const params = new URLSearchParams({ page: pageNum, pageSize })
        if (sid) params.set('sessionId', sid)
        const res = await apiFetch(`/api/logs?${params}`)
        const data = await res.json()
        if (append) {
          setLogs((prev) => [...prev, ...(data.logs || [])])
        } else {
          setLogs(data.logs || [])
        }
        setSessions(data.sessions || [])
        setTotal(data.total || 0)
        setHasMore((data.logs || []).length === pageSize)
        setPage(pageNum)
      } catch {
        setLogs([])
      } finally {
        setLoading(false)
      }
    },
    [pageSize]
  )

  // 首次加载 & 切换会话
  useEffect(() => {
    fetchLogs(1, activeSessionId)
  }, [activeSessionId, fetchLogs])

  const handleLoadMore = () => {
    if (hasMore && !loading) fetchLogs(page + 1, activeSessionId, true)
  }

  const formatTime = (ts) => {
    try {
      const d = new Date(ts)
      if (isNaN(d.getTime())) return ts
      const mm = String(d.getMonth() + 1).padStart(2, '0')
      const dd = String(d.getDate()).padStart(2, '0')
      const hh = String(d.getHours()).padStart(2, '0')
      const mi = String(d.getMinutes()).padStart(2, '0')
      return `${mm}-${dd} ${hh}:${mi}`
    } catch {
      return ts
    }
  }

  return (
    <div className="chp">
      <div className="chp-toolbar">
        <h3 className="chp-head">对话历史</h3>
      </div>

      {/* 会话筛选条 */}
      {sessions.length > 0 && (
        <div className="chp-sessions">
          <button
            className={`chp-session-btn ${!activeSessionId ? 'active' : ''}`}
            onClick={() => setActiveSessionId(null)}
          >
            全部
          </button>
          {sessions.map((s) => (
            <button
              key={s.session_id}
              className={`chp-session-btn ${activeSessionId === s.session_id ? 'active' : ''}`}
              onClick={() => setActiveSessionId(s.session_id)}
              title={`${s.turn_count} 轮 · ${formatTime(s.last_at)}`}
            >
              {s.session_id.length > 8 ? s.session_id.slice(0, 8) + '…' : s.session_id}
            </button>
          ))}
        </div>
      )}

      {/* 日志列表 */}
      <div className="chp-body">
        {loading && page === 1 && <div className="chp-loading">加载中…</div>}

        {!loading && logs.length === 0 && (
          <div className="chp-empty">暂无对话记录</div>
        )}

        {logs.map((log) => (
          <div key={log.id} className={`chp-item chp-${log.role}`}>
            <div className="chp-meta">
              <span className="chp-time">{formatTime(log.created_at)}</span>
              <span className="chp-role">{log.role === 'user' ? '你' : '小文'}</span>
              {log.intent && <span className="chp-intent">{log.intent}</span>}
            </div>
            <div className="chp-content">{log.content}</div>
          </div>
        ))}

        {hasMore && (
          <button className="chp-load-more" onClick={handleLoadMore} disabled={loading}>
            {loading ? '加载中…' : `加载更多（已显示 ${logs.length} / ${total}）`}
          </button>
        )}
      </div>
    </div>
  )
}

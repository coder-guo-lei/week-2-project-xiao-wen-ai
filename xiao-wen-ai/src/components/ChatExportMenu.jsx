/**
 * ChatExportMenu — 对话记录导出（Markdown / Word / PDF）
 */
import { useCallback, useState } from 'react'
import { exportChatHistory, normalizeHistory } from '../utils/chatExport'
import './ChatExportMenu.css'

const FORMATS = [
  { id: 'markdown', label: 'Markdown', hint: '.md' },
  { id: 'docx', label: 'Word', hint: '.docx' },
  { id: 'pdf', label: 'PDF', hint: '.pdf' },
]

export default function ChatExportMenu({ history }) {
  const [open, setOpen] = useState(false)
  const [busy, setBusy] = useState(null)
  const [error, setError] = useState('')

  const canExport = normalizeHistory(history).length > 0

  const handleExport = useCallback(
    async (format) => {
      if (!canExport || busy) return
      setError('')
      setBusy(format)
      setOpen(false)
      try {
        await exportChatHistory(format, history)
      } catch (e) {
        console.error(e)
        setError(e?.message || '导出失败，请稍后重试')
      } finally {
        setBusy(null)
      }
    },
    [busy, canExport, history],
  )

  return (
    <div className="cex">
      <button
        type="button"
        className="cex-trigger"
        onClick={() => setOpen((v) => !v)}
        disabled={!canExport || !!busy}
        aria-expanded={open}
        aria-haspopup="menu"
        title={canExport ? '导出对话记录' : '暂无对话记录'}
      >
        {busy ? '导出中…' : '导出记录'}
        <span className="cex-chevron" aria-hidden>
          {open ? '▴' : '▾'}
        </span>
      </button>
      {open && canExport && (
        <div className="cex-menu" role="menu">
          {FORMATS.map((f) => (
            <button
              key={f.id}
              type="button"
              role="menuitem"
              className="cex-item"
              onClick={() => handleExport(f.id)}
            >
              <span className="cex-item-label">{f.label}</span>
              <span className="cex-item-hint">{f.hint}</span>
            </button>
          ))}
        </div>
      )}
      {error && <p className="cex-error">{error}</p>}
    </div>
  )
}

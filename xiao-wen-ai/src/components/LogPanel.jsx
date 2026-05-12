/**
 * LogPanel.jsx — 运行日志面板
 *
 * 功能：
 *   - 逐条展示操作日志（识别到的指令、AI 回复、错误信息等）
 *   - 包含 ❌ 的条目以红色高亮显示
 *   - 每次新增日志后自动滚动到底部
 * Props：
 *   logs    {string[]} 日志文本数组，由父组件 App 维护
 *   onClear {fn=}      点击「清空日志」时回调（可选）
 */
import { useRef, useEffect } from 'react'
import './LogPanel.css'

export default function LogPanel({ logs, onClear }) {
  // 指向可滚动容器，用于在 logs 变化时把 scrollTop 设到底部
  const bodyRef = useRef(null)

  // 依赖 logs：每新增一条，用户无需手动滚到底即可看到最新日志
  useEffect(() => {
    const el = bodyRef.current
    if (el) el.scrollTop = el.scrollHeight
  }, [logs])

  return (
    <div className="lp">
      <div className="lp-toolbar">
        <h3 className="lp-head">📋 运行日志</h3>
        {typeof onClear === 'function' && (
          <button type="button" className="lp-clear" onClick={onClear}>
            清空日志
          </button>
        )}
      </div>
      {/* 列表区：每条一行，含 ❌ 的加 lp-err 样式 */}
      <div className="lp-body" ref={bodyRef}>
        {logs.length === 0 ? (
          <div className="lp-empty">暂无运行记录</div>
        ) : (
          logs.map((item, i) => (
            <div key={i} className={item.includes('❌') ? 'lp-err' : 'lp-ok'}>{item}</div>
          ))
        )}
      </div>
    </div>
  )
}

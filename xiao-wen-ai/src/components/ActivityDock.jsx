/**
 * ActivityDock — 底部活动日志区（IDE 终端式）
 * 默认收起为一条状态栏；展开后显示完整虚拟滚动日志。
 */
import LogPanel from './LogPanel'
import './ActivityDock.css'

export default function ActivityDock({ logs, open, onToggle, onClear }) {
  const lastLine = logs.length > 0 ? logs[logs.length - 1] : null
  const hasError = logs.some((line) => line.includes('❌'))

  return (
    <section
      className={`activity ${open ? 'activity--open' : 'activity--collapsed'}`}
      aria-label="运行日志"
    >
      {!open && (
        <button
          type="button"
          className="activity-bar"
          onClick={onToggle}
          aria-expanded={false}
        >
          <span className="activity-chevron" aria-hidden>▲</span>
          <span className="activity-title">运行日志</span>
          {lastLine ? (
            <span className={`activity-preview ${lastLine.includes('❌') ? 'activity-preview--err' : ''}`}>
              {lastLine}
            </span>
          ) : (
            <span className="activity-preview activity-preview--muted">暂无记录</span>
          )}
          <span className="activity-meta">
            {hasError && <span className="activity-flag">异常</span>}
            <span className="activity-count">{logs.length}</span>
          </span>
        </button>
      )}
      {open && (
        <div className="activity-body">
          <LogPanel
            logs={logs}
            onClear={onClear}
            onCollapse={onToggle}
            collapseLabel="收起"
            className="lp--dock"
          />
        </div>
      )}
    </section>
  )
}

/**
 * ActivityDock — 底部活动区（IDE 终端式）
 * 默认收起为状态栏；展开后显示运行日志（虚拟滚动）或云端对话历史。
 */
import LogPanel from './LogPanel'
import './ActivityDock.css'

export default function ActivityDock({
  logs,
  open,
  onToggle,
  onClear,
  dockTab = 'log',
  onDockTabChange,
  historyPanel = null,
}) {
  const lastLine = logs.length > 0 ? logs[logs.length - 1] : null
  const hasError = logs.some((line) => line.includes('❌'))
  const collapsedTitle = dockTab === 'history' ? '对话历史' : '运行日志'

  return (
    <section
      className={`activity ${open ? 'activity--open' : 'activity--collapsed'}`}
      aria-label={collapsedTitle}
    >
      {!open && (
        <button
          type="button"
          className="activity-bar"
          onClick={onToggle}
          aria-expanded={false}
        >
          <span className="activity-chevron" aria-hidden>▲</span>
          <span className="activity-title">{collapsedTitle}</span>
          {dockTab === 'log' && lastLine ? (
            <span className={`activity-preview ${lastLine.includes('❌') ? 'activity-preview--err' : ''}`}>
              {lastLine}
            </span>
          ) : (
            <span className="activity-preview activity-preview--muted">
              {dockTab === 'history' ? '点击查看云端对话记录' : '暂无记录'}
            </span>
          )}
          <span className="activity-meta">
            {hasError && dockTab === 'log' && <span className="activity-flag">异常</span>}
            {dockTab === 'log' && <span className="activity-count">{logs.length}</span>}
          </span>
        </button>
      )}
      {open && (
        <div className="activity-body">
          {historyPanel && (
            <div className="activity-tabs">
              <button
                type="button"
                className={`activity-tab ${dockTab === 'log' ? 'active' : ''}`}
                onClick={() => onDockTabChange?.('log')}
              >
                运行日志
              </button>
              <button
                type="button"
                className={`activity-tab ${dockTab === 'history' ? 'active' : ''}`}
                onClick={() => onDockTabChange?.('history')}
              >
                对话历史
              </button>
            </div>
          )}
          {dockTab === 'history' && historyPanel ? (
            <div className="activity-history">{historyPanel}</div>
          ) : (
            <LogPanel
              logs={logs}
              onClear={onClear}
              onCollapse={onToggle}
              collapseLabel="收起"
              className="lp--dock"
            />
          )}
        </div>
      )}
    </section>
  )
}

/**
 * LogPanel.jsx — 运行日志面板（虚拟滚动）
 *
 * 功能：
 *   - 仅渲染可视区域内的日志条目，支持万级日志流畅滚动
 *   - 自适应行高（measureElement 测量实际高度）
 *   - 含 ❌ 的条目以红色高亮显示
 *   - 每次新增日志后自动滚动到底部
 * Props：
 *   logs           {string[]} 日志文本数组，由父组件 App 维护
 *   onClear        {fn=}      点击「清空日志」时回调（可选）
 *   onCollapse     {fn=}      点击收起时回调（可选）
 *   collapseLabel  {string}   收起按钮文案，默认「收起」
 *   className      {string}   附加根节点 class
 */
import { useRef, useLayoutEffect } from 'react'
import { useVirtualizer } from '@tanstack/react-virtual'
import './LogPanel.css'

/** 单行估算高度：13px × line-height 1.75 */
const ESTIMATE_ROW_PX = 23
const OVERSCAN = 12

export default function LogPanel({ logs, onClear, onCollapse, collapseLabel = '收起', className = '' }) {
  const bodyRef = useRef(null)
  const prevCountRef = useRef(logs.length)

  const virtualizer = useVirtualizer({
    count: logs.length,
    getScrollElement: () => bodyRef.current,
    estimateSize: () => ESTIMATE_ROW_PX,
    overscan: OVERSCAN,
  })

  // 新增日志时滚到底部；清空时不强制滚动
  useLayoutEffect(() => {
    const prev = prevCountRef.current
    prevCountRef.current = logs.length
    if (logs.length === 0 || logs.length <= prev) return
    virtualizer.scrollToIndex(logs.length - 1, { align: 'end' })
  }, [logs, virtualizer])

  const rootClass = ['lp', className].filter(Boolean).join(' ')

  return (
    <div className={rootClass}>
      <div className="lp-toolbar">
        <h3 className="lp-head">📋 运行日志</h3>
        <div className="lp-toolbar-actions">
          {typeof onClear === 'function' && (
            <button type="button" className="lp-clear" onClick={onClear}>
              清空
            </button>
          )}
          {typeof onCollapse === 'function' && (
            <button type="button" className="lp-collapse" onClick={onCollapse}>
              {collapseLabel}
            </button>
          )}
        </div>
      </div>
      <div className="lp-body" ref={bodyRef}>
        {logs.length === 0 ? (
          <div className="lp-empty">暂无运行记录</div>
        ) : (
          <div
            className="lp-virtual-inner"
            style={{ height: virtualizer.getTotalSize() }}
          >
            {virtualizer.getVirtualItems().map((virtualRow) => {
              const text = logs[virtualRow.index]
              return (
                <div
                  key={virtualRow.key}
                  data-index={virtualRow.index}
                  ref={virtualizer.measureElement}
                  className={`lp-row ${text.includes('❌') ? 'lp-err' : 'lp-ok'}`}
                  style={{ transform: `translateY(${virtualRow.start}px)` }}
                >
                  {text}
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}

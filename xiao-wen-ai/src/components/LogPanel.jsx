/**

 * LogPanel.jsx — 运行日志面板（@tanstack/react-virtual 虚拟滚动 + 自适应行高）

 */

import { useRef, useEffect } from 'react'

import { useVirtualizer } from '@tanstack/react-virtual'

import './LogPanel.css'



export default function LogPanel({ logs, onClear, syncConnected, platformLabel }) {

  const bodyRef = useRef(null)

  const tailCountRef = useRef(logs.length)



  const virtualizer = useVirtualizer({

    count: logs.length,

    getScrollElement: () => bodyRef.current,

    estimateSize: () => 28,

    overscan: 10,

    measureElement: (el) => el.getBoundingClientRect().height,

  })



  useEffect(() => {

    const prev = tailCountRef.current

    tailCountRef.current = logs.length

    if (logs.length > prev && logs.length > 0) {

      virtualizer.scrollToIndex(logs.length - 1, { align: 'end' })

    }

  }, [logs.length, virtualizer])



  return (

    <div className="lp">

      <div className="lp-toolbar">

        <div className="lp-head-row">

          <h3 className="lp-head">📋 运行日志</h3>

          {typeof syncConnected === 'boolean' && (

            <span

              className={`lp-sync ${syncConnected ? 'lp-sync-on' : 'lp-sync-off'}`}

              title={syncConnected ? `多端同步已连接（${platformLabel || 'Web'}）` : '同步未连接，仅本页日志'}

            />

          )}

        </div>

        {typeof onClear === 'function' && (

          <button type="button" className="lp-clear" onClick={onClear}>

            清空日志

          </button>

        )}

      </div>

      <div className="lp-body" ref={bodyRef}>

        {logs.length === 0 ? (

          <div className="lp-empty">暂无运行记录</div>

        ) : (

          <div

            className="lp-virtual-inner"

            style={{ height: `${virtualizer.getTotalSize()}px` }}

          >

            {virtualizer.getVirtualItems().map((row) => {

              const item = logs[row.index]

              return (

                <div

                  key={row.key}

                  data-index={row.index}

                  ref={virtualizer.measureElement}

                  className={`lp-row ${item.includes('❌') ? 'lp-err' : 'lp-ok'}`}

                  style={{

                    position: 'absolute',

                    top: 0,

                    left: 0,

                    width: '100%',

                    transform: `translateY(${row.start}px)`,

                  }}

                >

                  {item}

                </div>

              )

            })}

          </div>

        )}

      </div>

    </div>

  )

}


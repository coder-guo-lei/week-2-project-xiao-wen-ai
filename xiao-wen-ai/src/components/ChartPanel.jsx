/**
 * ChartPanel.jsx — 数据可视化图表组件
 *
 * 功能：
 *   - 接收后端返回的 chartData，绘制折线图或柱状图
 *   - 支持上传 CSV / TXT / TSV / Excel 文件，让后端解析后重新生成图表
 *   - 展示数据摘要：数量、合计、最高值、最低值
 *   - 同时保留表格视图，方便用户核对原始数据
 *
 * 用到的东西和作用：
 *   - React useMemo：缓存坐标计算结果，避免每次渲染都重复计算
 *   - SVG：不用额外图表库，直接绘制坐标轴、网格线、折线、柱子和数据点
 *   - <title>：给柱子/点位提供悬浮提示，也提升可访问性
 *   - input[type=file] + FormData：把本地数据文件上传给后端 /api/generate-chart
 */
import './ChartPanel.css'

// 柱状图循环使用的配色，保持多柱数据有区分度。
const CHART_COLORS = ['#147a6e', '#0d9488', '#0891b2', '#16a34a', '#d97706', '#dc2626']

function formatNumber(value) {
  return Number(value).toLocaleString('zh-CN', { maximumFractionDigits: 2 })
}

function buildChartGeometry(points) {
  // 统一在 720×320 的 SVG 坐标系内计算，浏览器再按容器宽度等比例缩放。
  const width = 720
  const height = 320
  const padding = { top: 28, right: 26, bottom: 56, left: 58 }
  const values = points.map((item) => Number(item.value) || 0)
  const max = Math.max(...values, 0)
  const min = Math.min(...values, 0)
  const range = Math.max(max - Math.min(min, 0), 1)
  const baseline = height - padding.bottom
  const chartWidth = width - padding.left - padding.right
  const chartHeight = height - padding.top - padding.bottom

  const yOf = (value) => {
    // 把真实数值映射成 SVG 的 y 坐标；SVG y 轴向下增长，所以这里用 baseline 减去高度。
    const normalized = (value - Math.min(min, 0)) / range
    return baseline - normalized * chartHeight
  }

  const xOf = (index) => {
    // 折线图按数据数量平均分布 x 坐标，保证首尾贴近绘图区边界。
    if (points.length <= 1) return padding.left + chartWidth / 2
    return padding.left + (index / (points.length - 1)) * chartWidth
  }

  return { width, height, padding, baseline, chartWidth, chartHeight, max, min, yOf, xOf }
}

/** 柱状图：柱子水平位置与标签对齐（原先标签按折线 x 分布会错位） */
function computeBarLayout(geometry, points) {
  const n = points.length
  const barGap = n > 12 ? 6 : n > 8 ? 10 : 14
  const barWidth = Math.max(
    8,
    Math.min(52, (geometry.chartWidth - barGap * Math.max(0, n - 1)) / Math.max(n, 1)),
  )
  const total = barWidth * n + barGap * Math.max(0, n - 1)
  const offsetX = geometry.padding.left + Math.max(0, (geometry.chartWidth - total) / 2)
  const barLeft = (i) => offsetX + i * (barWidth + barGap)
  const barCenter = (i) => barLeft(i) + barWidth / 2
  const zeroY = geometry.yOf(0)
  return { barWidth, barGap, barLeft, barCenter, zeroY }
}

function truncateAxisLabel(label, pointsLen) {
  const s = String(label)
  const maxChars = pointsLen > 10 ? 5 : pointsLen > 7 ? 6 : 8
  return s.length > maxChars ? `${s.slice(0, maxChars)}…` : s
}

export default function ChartPanel({ data, onUpload, disabled }) {
  const points = Array.isArray(data?.points) ? data.points : []
  const geometry = buildChartGeometry(points)

  const handleFileChange = (event) => {
    const file = event.target.files?.[0]
    if (file) onUpload?.(file)
    event.target.value = ''
  }

  if (!data || points.length === 0) {
    return (
      <section className="chart-panel chart-panel--empty" aria-label="数据可视化图表">
        <div className="chart-head chart-head--empty">
          <div>
            <h3>数据图表</h3>
            <p>
              可直接说「帮我生成一份数据和柱状图」，系统会自动给出示例数据；也可输入「一月:120
              二月:180」这类数字，或上传 CSV / Excel。
            </p>
          </div>
          <label className={`chart-upload ${disabled ? 'is-disabled' : ''}`}>
            <input
              type="file"
              accept=".csv,.txt,.tsv,.xlsx,.xls"
              onChange={handleFileChange}
              disabled={disabled}
            />
            上传数据文件
          </label>
        </div>
      </section>
    )
  }

  const isLine = data.chartType === 'line'
  const polyline = points
    .map((item, index) => `${geometry.xOf(index)},${geometry.yOf(item.value)}`)
    .join(' ')
  const barLayout = computeBarLayout(geometry, points)

  return (
    <section className="chart-panel" aria-label="数据可视化图表">
      {/* 标题行 + 上传（label 包裹隐藏 input，样式做成按钮） */}
      <div className="chart-head">
        <div>
          <p className="chart-eyebrow">DATA VISUALIZATION</p>
          <h3>{data.title || '数据图表'}</h3>
          <span>
            {data.source || '文本数据'} · {isLine ? '折线图' : '柱状图'}
          </span>
        </div>
        <label className={`chart-upload ${disabled ? 'is-disabled' : ''}`}>
          <input
            type="file"
            accept=".csv,.txt,.tsv,.xlsx,.xls"
            onChange={handleFileChange}
            disabled={disabled}
          />
          上传数据文件
        </label>
      </div>

      {/* 后端 summary 与前端 points 兜底展示 */}
      <div className="chart-summary" aria-label="数据摘要">
        <div>
          <span>数据量</span>
          <strong>{data.summary?.count ?? points.length}</strong>
        </div>
        <div>
          <span>合计</span>
          <strong>
            {formatNumber(
              data.summary?.total ?? points.reduce((sum, item) => sum + Number(item.value || 0), 0),
            )}
          </strong>
        </div>
        <div>
          <span>最高</span>
          <strong>
            {data.summary?.maxLabel}: {formatNumber(data.summary?.maxValue ?? 0)}
          </strong>
        </div>
        <div>
          <span>最低</span>
          <strong>
            {data.summary?.minLabel}: {formatNumber(data.summary?.minValue ?? 0)}
          </strong>
        </div>
      </div>

      {/* SVG：网格 + 坐标轴 + 折线或柱子 + X 轴文字 */}
      <div
        className="chart-canvas"
        role="img"
        aria-label={`${data.title || '图表'}，共 ${points.length} 组数据`}
      >
        <svg
          viewBox={`0 0 ${geometry.width} ${geometry.height}`}
          preserveAspectRatio="xMidYMid meet"
        >
          <defs>
            <linearGradient id="chartLineGlow" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" stopColor="#3da89a" />
              <stop offset="50%" stopColor="#147a6e" />
              <stop offset="100%" stopColor="#0d5c54" />
            </linearGradient>
            <linearGradient id="chartBarGlow" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#5eead4" />
              <stop offset="100%" stopColor="#0f766e" />
            </linearGradient>
          </defs>

          {[0, 0.25, 0.5, 0.75, 1].map((tick) => {
            const y = geometry.padding.top + tick * geometry.chartHeight
            const span = geometry.max - Math.min(geometry.min, 0)
            const value = geometry.max - tick * span
            return (
              <g key={tick} className="chart-grid-row">
                <line
                  x1={geometry.padding.left}
                  y1={y}
                  x2={geometry.width - geometry.padding.right}
                  y2={y}
                />
                <text x={geometry.padding.left - 10} y={y + 4}>
                  {formatNumber(value)}
                </text>
              </g>
            )
          })}

          <line
            className="chart-axis"
            x1={geometry.padding.left}
            y1={barLayout.zeroY}
            x2={geometry.width - geometry.padding.right}
            y2={barLayout.zeroY}
          />
          <line
            className="chart-axis"
            x1={geometry.padding.left}
            y1={geometry.padding.top}
            x2={geometry.padding.left}
            y2={geometry.baseline}
          />

          {isLine ? (
            <g>
              <polyline className="chart-line-shadow" points={polyline} />
              <polyline className="chart-line" points={polyline} />
              {points.map((item, index) => (
                <g key={`${item.label}-${index}`} className="chart-point">
                  <circle cx={geometry.xOf(index)} cy={geometry.yOf(item.value)} r="5.5" />
                  <title>
                    {item.label}: {formatNumber(item.value)}
                  </title>
                </g>
              ))}
            </g>
          ) : (
            <g>
              {points.map((item, index) => {
                const x = barLayout.barLeft(index)
                const y = Math.min(geometry.yOf(item.value), barLayout.zeroY)
                const h = Math.max(Math.abs(barLayout.zeroY - geometry.yOf(item.value)), 2)
                return (
                  <g key={`${item.label}-${index}`} className="chart-bar">
                    <rect
                      x={x}
                      y={y}
                      width={barLayout.barWidth}
                      height={h}
                      rx="8"
                      fill={CHART_COLORS[index % CHART_COLORS.length]}
                    />
                    <title>
                      {item.label}: {formatNumber(item.value)}
                    </title>
                  </g>
                )
              })}
            </g>
          )}

          {points.map((item, index) => {
            const cx = isLine ? geometry.xOf(index) : barLayout.barCenter(index)
            return (
              <text
                key={`${item.label}-label-${index}`}
                className="chart-x-label"
                x={cx}
                y={geometry.height - 24}
              >
                {truncateAxisLabel(item.label, points.length)}
              </text>
            )
          })}
        </svg>
      </div>

      {/* 与图同源的表格，便于核对 */}
      <div className="chart-table-wrap">
        <table className="chart-table">
          <thead>
            <tr>
              <th>名称</th>
              <th>数值</th>
            </tr>
          </thead>
          <tbody>
            {points.map((item, index) => (
              <tr key={`${item.label}-row-${index}`}>
                <td>{item.label}</td>
                <td>{formatNumber(item.value)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}

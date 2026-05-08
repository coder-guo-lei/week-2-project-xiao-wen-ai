/**
 * WorkflowPanel.jsx — 任务执行流程（步骤条）
 *
 * 由后端 optional 字段 workflow 驱动：展示「接收文件 → 解析 → …」等步骤，
 * 用于图表、图片分析等需要多阶段反馈的场景。无步骤时不渲染。
 */
import './WorkflowPanel.css'

export default function WorkflowPanel({ steps = [] }) {
  // 非数组或空数组：不占布局，避免空白占位
  if (!Array.isArray(steps) || steps.length === 0) return null

  return (
    <section className="workflow-panel" aria-label="任务执行流程">
      <div className="workflow-panel__header">
        <span className="workflow-panel__eyebrow">AI Agent Trace</span>
        <strong>任务执行流程</strong>
      </div>
      <div className="workflow-panel__steps">
        {steps.map((step, index) => (
          <div className="workflow-step" key={`${step.title}-${index}`}>
            <div className="workflow-step__index">{index + 1}</div>
            <div className="workflow-step__body">
              <div className="workflow-step__title">{step.title}</div>
              <div className="workflow-step__detail">{step.detail}</div>
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}

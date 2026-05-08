/**
 * ModeBar.jsx — 当前模式提示条
 *
 * 后端会随每次指令返回 mode / modeLabel / worldState。
 * 前端用该组件告诉用户当前处于普通助手、音乐、图片生成或模拟世界模式，
 * 并在模拟世界模式下展示快捷动作，降低用户记忆指令成本。
 */
import './ModeBar.css'

export default function ModeBar({ mode, modeLabel, worldState, quickActions = [], onQuickAction }) {
  // 是否为文字模拟世界模式（与后端 mode === 'world' 对齐）
  const isWorld = mode === 'world'

  return (
    <div className={`mode-bar ${isWorld ? 'mode-bar--world' : ''}`}>
      {/* 左侧：状态点 + 主标题 + 副说明 */}
      <div className="mode-bar__main">
        <span className="mode-bar__dot" />
        <div>
          <div className="mode-bar__label">{modeLabel || '普通助手'}</div>
          <div className="mode-bar__desc">
            {isWorld && worldState
              ? `${worldState.theme}世界 · 种子 ${worldState.seed} · 输入“退出模拟”返回普通模式`
              : '可以聊天、查天气、播放音乐、生成图片或创建模拟世界'}
          </div>
        </div>
      </div>

      {/* 世界模式：渲染后端下发的快捷指令按钮，点击即当作一条 task 发送 */}
      {isWorld && quickActions.length > 0 && (
        <div className="mode-bar__actions">
          {quickActions.map((action) => (
            <button key={action} type="button" onClick={() => onQuickAction?.(action)}>
              {action}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

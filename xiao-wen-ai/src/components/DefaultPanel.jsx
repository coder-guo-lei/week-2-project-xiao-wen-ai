/**
 * DefaultPanel.jsx — 空状态引导面板
 *
 * 功能：右侧面板无内容时显示，向用户介绍可用指令类型。
 *   - 状态指示灯：动态显示"识别指令中 / 待机中 / 监听已关闭"
 *   - 示例卡片网格：天气 / 音乐 / 绘画 / 知识库 / 世界 / 摄像头肤质洞察等
 * Props：
 *   isCmdActive  {boolean} 语音识别进行中
 *   isWakeActive {boolean} 唤醒词监听开启中
 *   onExampleClick(example) — example 含 text / type；type 为 face_camera 时由 App 滚动到摄像头区块
 */
import './DefaultPanel.css'

export default function DefaultPanel({ isCmdActive, isWakeActive, onExampleClick }) {
  // 示例指令：多数交给 App.autoSendTask；face_camera 仅定位到肤质摄像头 UI
  const examples = [
    { icon: '🌤️', text: '保定天气怎么样？', type: 'weather' },
    { icon: '🎵', text: '随机播放一首歌', type: 'music' },
    { icon: '🎨', text: '画一只水墨风格的小猫', type: 'image' },
    { icon: '📚', text: '知识库：这个项目有哪些 AI 亮点？', type: 'knowledge' },
    { icon: '🗺️', text: '生成一个修仙世界,世界核心随机，我叫叶凡，出生在青岚山脚的破旧药庐', type: 'world' },
    { icon: '📷', text: '用摄像头看看肤质和气色，给护肤建议和精神状态参考', type: 'face_camera' },
  ]

  return (
    <div className="dp">
      {/* 根据语音 / 唤醒 Hook 状态显示当前麦克风相关状态 */}
      <div className="dp-status">
        <span className="dp-status-label">当前状态</span>
        {isCmdActive
          ? <span className="dp-dot dp-dot--red">识别指令中</span>
          : isWakeActive
            ? <span className="dp-dot dp-dot--green">待机中（喊「小文」或「小文小文」）</span>
            : <span className="dp-dot dp-dot--gray">监听已关闭</span>
        }
      </div>

      <h4 className="dp-heading">试试这些指令</h4>
      <div className="dp-grid">
        {examples.map((example) => (
          <button
            key={example.text}
            type="button"
            className="dp-card"
            onClick={() => onExampleClick?.(example)}
            title={example.type === 'face_camera' ? '定位到肤质与状态洞察（摄像头）' : `发送指令：${example.text}`}
          >
            <span className="dp-card-icon">{example.icon}</span>
            <span className="dp-card-text">"{example.text}"</span>
          </button>
        ))}
      </div>
      <p className="dp-hint">点击示例可直接发送（摄像头肤质示例会滚动到上方拍摄区），也可手动输入后按 Enter</p>
    </div>
  )
}

/**
 * DefaultPanel.jsx — 空状态引导面板
 *
 * 功能：右侧面板无内容时显示，向用户介绍可用指令类型。
 *   - 状态指示灯：动态显示"识别指令中 / 待机中 / 监听已关闭"
 *   - 示例卡片网格：天气 / 音乐 / 绘画 / 知识库 / 世界 / 摄像头肤质洞察等
 *   - 浏览电脑添加应用到白名单（Windows + 本机后端）：选 .exe 并起名后，可说「打开【名称】」
 * Props：
 *   isCmdActive  {boolean} 语音识别进行中
 *   isWakeActive {boolean} 唤醒词监听开启中
 *   onExampleClick(example) — example 含 text / type；type 为 face_camera 时由 App 滚动到摄像头区块
 *   userExePickSupported {boolean} 后端是否支持原生选 exe
 *   pickBrowseBusy {boolean} 正在等待系统选文件对话框
 *   userAppList {{ name, path }[]} 已添加白名单
 *   addAppDraft {{ path, suggestedName } | null} 选完 exe 后弹出确认层
 *   addAppNameInput / onAddAppNameChange 受控输入
 *   onBrowsePickExe / onCancelAddApp / onConfirmAddApp / onRemoveUserApp
 */
import './DefaultPanel.css'

export default function DefaultPanel({
  isCmdActive,
  isWakeActive,
  onExampleClick,
  userExePickSupported = true,
  pickBrowseBusy = false,
  userAppList = [],
  addAppDraft = null,
  addAppNameInput = '',
  onAddAppNameChange,
  onBrowsePickExe,
  onCancelAddApp,
  onConfirmAddApp,
  onRemoveUserApp,
}) {
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
      <div className="dp-status">
        <span className="dp-status-label">当前状态</span>
        {isCmdActive
          ? <span className="dp-dot dp-dot--red">识别指令中</span>
          : isWakeActive
            ? <span className="dp-dot dp-dot--green">待机中（喊「小文」或「小文小文」）</span>
            : <span className="dp-dot dp-dot--gray">监听已关闭</span>
        }
      </div>

      {userExePickSupported && (
        <div className="dp-add-app">
          <button
            type="button"
            className="dp-add-app-btn"
            disabled={pickBrowseBusy}
            onClick={() => onBrowsePickExe?.()}
          >
            {pickBrowseBusy ? '正在等待你选择程序…' : '📂 浏览电脑，添加应用到白名单'}
          </button>
          <p className="dp-add-app-hint">
            点击后会弹出系统文件框，选中本机 .exe 并起一个好记的名字，之后直接说「打开【名字】」即可启动。
          </p>
          {userAppList.length > 0 && (
            <ul className="dp-user-apps">
              {userAppList.map((row) => (
                <li key={row.name} className="dp-user-apps-item">
                  <span className="dp-user-apps-name" title={row.path}>{row.name}</span>
                  <button
                    type="button"
                    className="dp-user-apps-remove"
                    onClick={() => onRemoveUserApp?.(row.name)}
                    aria-label={`从白名单移除 ${row.name}`}
                  >
                    移除
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {addAppDraft && (
        <div
          className="dp-modal-overlay"
          role="presentation"
          onClick={(e) => {
            if (e.target === e.currentTarget) onCancelAddApp?.()
          }}
        >
          <div className="dp-modal" role="dialog" aria-modal="true" aria-labelledby="dp-modal-title" onClick={(e) => e.stopPropagation()}>
            <h4 id="dp-modal-title" className="dp-modal-title">确认加入白名单</h4>
            <p className="dp-modal-path" title={addAppDraft.path}>{addAppDraft.path}</p>
            <label className="dp-modal-label" htmlFor="dp-add-app-name">对小文说的名称（例如：原神、剪映）</label>
            <input
              id="dp-add-app-name"
              className="dp-modal-input"
              value={addAppNameInput}
              onChange={(e) => onAddAppNameChange?.(e.target.value)}
              maxLength={24}
              autoComplete="off"
            />
            <div className="dp-modal-actions">
              <button type="button" className="dp-modal-btn dp-modal-btn--ghost" onClick={() => onCancelAddApp?.()}>
                取消
              </button>
              <button type="button" className="dp-modal-btn dp-modal-btn--primary" onClick={() => onConfirmAddApp?.()}>
                确认添加
              </button>
            </div>
          </div>
        </div>
      )}

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

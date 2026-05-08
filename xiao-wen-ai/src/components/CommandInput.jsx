/**
 * CommandInput.jsx — 指令输入区
 *
 * 功能：
 *   - 多行文本框，Enter 发送指令，Shift+Enter 换行
 *   - 「语音」按钮：触发一次性语音识别
 *   - 「唤醒」按钮：开启/关闭持续监听「小文 / 小文小文」唤醒词
 *   - 「发送」按钮：手动提交当前文本框内容
 * Props：
 *   task         {string}   当前输入文本
 *   setTask      {fn}       更新输入文本
 *   onSend       {fn}       提交指令回调
 *   isCmdActive  {boolean}  语音识别进行中（禁用发送与历史点击）
 *   startCmd     {fn}       触发单次语音识别
 *   stopCmd      {fn}       终止当前语音识别，且丢弃已识别但未提交的内容
 *   toggleWake   {fn}       切换唤醒词监听
 *   isWakeActive {boolean}  唤醒监听是否开启
 *   isSending    {boolean}  后端请求进行中，用于防重复提交
 *   commandHistory {string[]} 本地保存的常用指令历史
 *   onHistoryClick {fn}     点击历史指令后直接发送
 */
import { useRef, useEffect } from 'react'
import './CommandInput.css'

export default function CommandInput({
  task,
  setTask,
  onSend,
  isCmdActive,
  isSending,
  startCmd,
  stopCmd,
  toggleWake,
  isWakeActive,
  commandHistory = [],
  onHistoryClick,
}) {
  const textareaRef = useRef(null) // 受控多行输入，用于程序性 focus()
  const prevSendingRef = useRef(isSending) // 上一帧是否在发送，用于边沿检测「发送刚结束」
  const prevCmdActiveRef = useRef(isCmdActive) // 上一帧是否在语音识别，用于检测「语音刚结束」

  const canEdit = !isSending // 发送中禁止改文本，避免与请求体不一致
  const canSubmit = !isCmdActive && !isSending // 语音聆听或发送中不允许再次提交
  // 聆听指令时仍允许关闭唤醒（否则只能先「终止语音」才能关）
  const canToggleWake = !isSending

  const handleKeyDown = (e) => {
    if (!canSubmit) return
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault() // 阻止默认换行
      onSend(task)
    }
  }

  /** 进入页面后焦点在输入框，对话发送完成或语音结束后自动回到输入框，减少来回点击 */
  useEffect(() => {
    textareaRef.current?.focus()
  }, [])

  /** 检测 isSending / isCmdActive 从 true→false，用 rAF 再 focus，避免与 DOM 更新抢帧 */
  useEffect(() => {
    const sendJustEnded = prevSendingRef.current && !isSending
    const voiceJustEnded = prevCmdActiveRef.current && !isCmdActive
    prevSendingRef.current = isSending
    prevCmdActiveRef.current = isCmdActive

    if (!sendJustEnded && !voiceJustEnded) return
    if (isSending || isCmdActive) return
    const id = requestAnimationFrame(() => {
      textareaRef.current?.focus()
    })
    return () => cancelAnimationFrame(id)
  }, [isSending, isCmdActive])

  return (
    <div className="ci">
      <textarea
        ref={textareaRef}
        value={task}
        onChange={(e) => setTask(e.target.value)}
        onKeyDown={handleKeyDown}
        disabled={!canEdit}
        placeholder="请输入指令（Enter 发送，Shift+Enter 换行）"
        className="ci-textarea"
        aria-label="指令输入"
      />
      <div className="ci-actions">
        <button
          type="button"
          onClick={isCmdActive ? stopCmd : startCmd}
          disabled={isSending}
          className={`ci-btn ci-btn--voice ${isCmdActive ? 'is-recording' : ''}`}
        >
          {isCmdActive ? '⏹️ 终止语音' : '🎤 语音'}
        </button>
        <button type="button" onClick={toggleWake} disabled={!canToggleWake} className={`ci-btn ci-btn--wake ${isWakeActive ? 'is-on' : ''}`}>
          {isWakeActive ? '⏹ 关闭唤醒' : '⚪ 唤醒'}
        </button>
        <button onClick={() => onSend(task)} disabled={!canSubmit || !task.trim()} className="ci-btn ci-btn--send">
          {isSending ? '发送中…' : '发送'}
        </button>
      </div>
      {commandHistory.length > 0 && (
        <div className="ci-history" aria-label="常用指令历史">
          <span>常用：</span>
          {commandHistory.slice(0, 5).map((item) => (
            <button key={item} type="button" onClick={() => onHistoryClick?.(item)} disabled={!canSubmit}>
              {item}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

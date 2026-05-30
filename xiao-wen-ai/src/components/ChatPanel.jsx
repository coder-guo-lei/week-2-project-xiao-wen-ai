/**
 * ChatPanel.jsx — 对话面板：历史记录 + 最新回复朗读/复制
 */
import { useCallback, useEffect, useRef, useState } from 'react'
import { cleanupTtsAudio, getTtsVoiceFromStorage, playXfyunTts, VOICE_PREF_KEY } from '../utils/xfyunTts'
import ChatExportMenu from './ChatExportMenu'
import ChatHistoryView from './ChatHistoryView'
import './ChatPanel.css'

const VOICE_LABEL = {
  female: '女声 · 默认（超拟人：聆小璇 / 经典：小燕）',
  female_jiuxu: '女声 · 许久 / 聆玉昭',
}

const MAX_ROUNDS_HINT = 6

export default function ChatPanel({ reply, history = [], onClearHistory }) {
  const [voiceType, setVoiceType] = useState(() => getTtsVoiceFromStorage())
  const [isSpeaking, setIsSpeaking] = useState(false)
  const [copyDone, setCopyDone] = useState(false)
  const [ttsError, setTtsError] = useState('')
  const copyTimerRef = useRef(null)
  const ttsAudioRef = useRef(null)
  const ttsObjectUrlRef = useRef(null)

  const stopSpeaking = useCallback(() => {
    cleanupTtsAudio(ttsAudioRef, ttsObjectUrlRef)
    setIsSpeaking(false)
  }, [])

  useEffect(() => {
    try {
      localStorage.setItem(VOICE_PREF_KEY, voiceType)
    } catch { /* ignore */ }
  }, [voiceType])

  useEffect(() => {
    cleanupTtsAudio(ttsAudioRef, ttsObjectUrlRef)
    queueMicrotask(() => {
      setIsSpeaking(false)
      setTtsError('')
    })
  }, [reply])

  useEffect(() => () => {
    if (copyTimerRef.current) window.clearTimeout(copyTimerRef.current)
    cleanupTtsAudio(ttsAudioRef, ttsObjectUrlRef)
  }, [])

  const trimmed = String(reply || '').trim()

  const copyFullReply = useCallback(async () => {
    if (!trimmed) return
    try {
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(trimmed)
      } else {
        const ta = document.createElement('textarea')
        ta.value = trimmed
        ta.setAttribute('readonly', '')
        ta.style.position = 'fixed'
        ta.style.left = '-9999px'
        document.body.appendChild(ta)
        ta.select()
        document.execCommand('copy')
        document.body.removeChild(ta)
      }
      setCopyDone(true)
      if (copyTimerRef.current) window.clearTimeout(copyTimerRef.current)
      copyTimerRef.current = window.setTimeout(() => setCopyDone(false), 2000)
    } catch {
      setCopyDone(false)
    }
  }, [trimmed])

  const speakReply = useCallback(async () => {
    if (!trimmed) return
    stopSpeaking()
    setTtsError('')
    setIsSpeaking(true)
    try {
      await playXfyunTts(trimmed, ttsAudioRef, ttsObjectUrlRef, { voice: voiceType })
    } catch (e) {
      console.error(e)
      setTtsError(e?.message || '朗读失败：请确认后端已启动且已配置讯飞密钥')
    } finally {
      setIsSpeaking(false)
    }
  }, [trimmed, voiceType, stopSpeaking])

  const hasHistory = history.length > 0 || trimmed

  return (
    <div className="cp">
      <div className="cp-head">
        <div className="cp-head-main">
          <span className="cp-head-icon">💬</span>
          <span>对话记录</span>
        </div>
        <div className="cp-head-actions">
          {typeof onClearHistory === 'function' && hasHistory && (
            <button
              type="button"
              className="cp-clear-btn"
              onClick={onClearHistory}
              title="清空本地对话记录"
            >
              清空
            </button>
          )}
          <ChatExportMenu history={history} />
        </div>
      </div>

      <ChatHistoryView
        history={history}
        reply={reply}
        maxRoundsHint={MAX_ROUNDS_HINT}
      />

      <div className={`cp-latest ${isSpeaking ? 'cp-latest--speaking' : ''}`}>
        <div className="cp-latest-head">
          <span>最新回复</span>
          <div className="cp-latest-actions">
            <button
              type="button"
              className="cp-copy-btn"
              onClick={copyFullReply}
              disabled={!trimmed}
              title="复制小文最新回复"
            >
              {copyDone ? '已复制' : '复制'}
            </button>
          </div>
        </div>

        <div className="cp-tts">
          <div className="cp-tts-label">
            <span>🔊 朗读最新回复</span>
            <small className="cp-tts-engine">讯飞 TTS · {VOICE_LABEL[voiceType] || VOICE_LABEL.female}</small>
          </div>
          <div className="cp-tts-actions">
            <select
              value={voiceType}
              onChange={(e) => setVoiceType(e.target.value)}
              className="cp-tts-select"
              disabled={isSpeaking}
            >
              <option value="female">女声 · 默认</option>
              <option value="female_jiuxu">女声 · 许久 / 玉昭</option>
            </select>
            <button
              type="button"
              className={`cp-tts-btn cp-tts-btn--primary ${isSpeaking ? 'is-speaking' : ''}`}
              onClick={speakReply}
              disabled={!trimmed}
            >
              {isSpeaking ? '朗读中…' : '开始朗读'}
            </button>
            <button
              type="button"
              className="cp-tts-btn"
              onClick={stopSpeaking}
              disabled={!isSpeaking}
            >
              停止
            </button>
          </div>
          {ttsError && <p className="cp-tts-tip cp-tts-tip--error">{ttsError}</p>}
        </div>
      </div>
    </div>
  )
}

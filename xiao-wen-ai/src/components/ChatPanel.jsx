/**
 * ChatPanel.jsx — 对话回复面板
 *
 * - 「朗读回复」：POST /api/tts（后端讯飞 WebSocket TTS，默认 WAV）
 */
import { useCallback, useEffect, useRef, useState } from 'react'
import { cleanupTtsAudio, getTtsVoiceFromStorage, playXfyunTts, VOICE_PREF_KEY } from '../utils/xfyunTts'
import './ChatPanel.css'

const VOICE_LABEL = {
  female: '女声 · 默认（超拟人：聆小璇 / 经典：小燕）',
  female_jiuxu: '女声 · 许久 / 聆玉昭',
}

/** split 带捕获组时，偶数位片段为 URL；勿对 /g 正则反复 .test()，否则会因 lastIndex 漏匹配。 */
function renderTextWithLinks(text) {
  const urlRegex = /(https?:\/\/[^\s，。！？；、]+)/g
  const parts = text.split(urlRegex)
  return parts.map((part, index) => {
    if (/^https?:\/\//.test(part)) {
      return (
        <a key={`${part}-${index}`} href={part} target="_blank" rel="noreferrer">
          {part}
        </a>
      )
    }
    return part
  })
}

export default function ChatPanel({ reply }) {
  const [voiceType, setVoiceType] = useState(() => getTtsVoiceFromStorage())

  const [isSpeaking, setIsSpeaking] = useState(false)
  const [copyDone, setCopyDone] = useState(false)
  const [ttsError, setTtsError] = useState('')
  const bodyRef = useRef(null)
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

  const copyFullReply = useCallback(async () => {
    const text = String(reply || '').trim()
    if (!text) return
    try {
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(text)
      } else {
        const ta = document.createElement('textarea')
        ta.value = text
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
  }, [reply])

  const speakReply = useCallback(async () => {
    const text = String(reply || '').trim()
    if (!text) return

    stopSpeaking()
    setTtsError('')
    setIsSpeaking(true)

    try {
      await playXfyunTts(text, ttsAudioRef, ttsObjectUrlRef, { voice: voiceType })
    } catch (e) {
      console.error(e)
      setTtsError(e?.message || '朗读失败：请确认后端已启动且已配置讯飞密钥')
    } finally {
      setIsSpeaking(false)
    }
  }, [reply, voiceType, stopSpeaking])

  const trimmed = String(reply || '').trim()

  return (
    <div className="cp">
      <div className="cp-head">
        <span className="cp-head-icon">💬</span>
        <span>小文回复</span>
      </div>
      <div className={`cp-body ${isSpeaking ? 'cp-body--speaking' : ''}`} ref={bodyRef}>
        {trimmed ? (
          <span className="cp-segment">{renderTextWithLinks(reply)}</span>
        ) : (
          '（暂无内容）'
        )}
      </div>

      <div className="cp-copy-row">
        <button
          type="button"
          className="cp-copy-btn"
          onClick={copyFullReply}
          disabled={!trimmed}
          title="复制当前小文回复的完整纯文本"
        >
          {copyDone ? '已复制' : '复制全文'}
        </button>
      </div>

      <div className="cp-tts">
        <div className="cp-tts-label">
          <span>🔊 朗读回复</span>
          <small className="cp-tts-engine">讯飞 TTS · {VOICE_LABEL[voiceType] || VOICE_LABEL.female}</small>
        </div>
        <div className="cp-tts-actions">
          <select
            value={voiceType}
            onChange={(e) => setVoiceType(e.target.value)}
            className="cp-tts-select"
            disabled={isSpeaking}
            title="后端若配置超拟人 wss，下列映射为 x5 发音人；否则为在线合成经典音库"
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
        <p className="cp-tts-tip">
          超拟人需在控制台「发音人授权管理」领取发音人；11200 表示当前 vcn 未授权。也可在请求里直接传控制台给出的 vcn。
        </p>
      </div>
    </div>
  )
}

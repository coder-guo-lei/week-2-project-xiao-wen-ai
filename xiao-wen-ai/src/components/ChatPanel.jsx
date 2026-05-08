/**
 * ChatPanel.jsx — 对话回复面板
 *
 * 功能：
 *   - 展示小文 AI 对闲聊类指令（笑话、故事、问答等）的文字回复
 *   - 在回复下方提供「复制全文」与朗读控制，朗读可选择男音 / 女音
 *   - 朗读时按句子高亮当前读到的位置
 *   - 使用浏览器 Web Speech API，音色由系统/浏览器可用中文语音决定
 * Props：
 *   reply {string} — 后端返回的对话文本，支持换行（pre-wrap）
 */
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import './ChatPanel.css'

/** localStorage 键：用户上次选的朗读性别（女音 / 男音） */
const VOICE_PREF_KEY = 'xiaowen_tts_voice_type'

/**
 * 从浏览器提供的语音列表里挑一个尽量匹配「中文 + 男/女」的 Voice。
 * @param {SpeechSynthesisVoice[]} voices - speechSynthesis.getVoices()
 * @param {'male'|'female'} voiceType - 界面下拉框当前值
 */
function pickChineseVoice(voices, voiceType) {
  // 优先 lang/name 含 zh、cmn、yue 的语音；没有则退回全列表
  const chineseVoices = voices.filter((voice) => /zh|cmn|yue/i.test(voice.lang || voice.name))
  const candidates = chineseVoices.length ? chineseVoices : voices

  const femaleHints = ['female', 'woman', 'xiaoxiao', 'xiaoyi', 'xiaobei', 'huihui', 'tingting', 'yaoyao', 'hanhan', '女']
  const maleHints = ['male', 'man', 'yunxi', 'yunyang', 'kangkang', 'xiaogang', '男']
  const hints = voiceType === 'male' ? maleHints : femaleHints

  return candidates.find((voice) => hints.some((hint) => voice.name.toLowerCase().includes(hint))) || candidates[0] || null
}

/**
 * 按中文标点把整段 reply 切成「句块」，用于朗读 onboundary 时高亮对应 span。
 * @param {string} text
 */
function splitReplyToSegments(text) {
  if (!text) return []
  const segments = []
  const regex = /[^。！？!?；;\n]+[。！？!?；;]?|\n+/g
  let match

  while ((match = regex.exec(text)) !== null) {
    segments.push({
      text: match[0],
      start: match.index,
      end: match.index + match[0].length,
    })
  }

  return segments.length ? segments : [{ text, start: 0, end: text.length }]
}

/** 根据朗读事件的 charIndex 落在哪一段，返回段下标 */
function findActiveSegmentIndex(segments, charIndex) {
  if (!segments.length || charIndex < 0) return -1
  const exact = segments.findIndex((segment) => charIndex >= segment.start && charIndex < segment.end)
  return exact >= 0 ? exact : segments.length - 1
}

/**
 * 把纯文本里的 http(s) 链接切成 React 片段，链接渲染为 <a>，其余为文本节点。
 * 注意：正则 lastIndex 在 split+test 组合下需谨慎；此处每段独立 test。
 */
function renderTextWithLinks(text) {
  const urlRegex = /(https?:\/\/[^\s，。！？；、]+)/g
  const parts = text.split(urlRegex)
  return parts.map((part, index) => {
    if (urlRegex.test(part)) {
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
  // ---------- 状态：朗读音色、可用语音列表、是否正在读、当前高亮句、复制成功提示 ----------
  const [voiceType, setVoiceType] = useState(() => {
    try {
      return localStorage.getItem(VOICE_PREF_KEY) || 'female'
    } catch {
      return 'female'
    }
  })

  const [voices, setVoices] = useState([])
  const [isSpeaking, setIsSpeaking] = useState(false)
  const [activeSegmentIndex, setActiveSegmentIndex] = useState(-1)
  const [copyDone, setCopyDone] = useState(false)
  const bodyRef = useRef(null) // 可滚动正文容器，用于朗读时自动滚到当前句
  const activeSegmentRef = useRef(null) // 当前高亮句对应的 span，用于 scrollIntoView 计算
  const copyTimerRef = useRef(null) // 「已复制」2 秒后恢复的定时器 id

  const canSpeak = typeof window !== 'undefined' && 'speechSynthesis' in window // 是否支持 Web Speech 朗读
  const selectedVoice = useMemo(() => pickChineseVoice(voices, voiceType), [voices, voiceType])
  const replySegments = useMemo(() => splitReplyToSegments(reply || ''), [reply])

  // 挂载时拉取语音列表；部分浏览器异步加载 voices，需监听 onvoiceschanged
  useEffect(() => {
    if (!canSpeak) return undefined

    const loadVoices = () => setVoices(window.speechSynthesis.getVoices())
    loadVoices()
    window.speechSynthesis.onvoiceschanged = loadVoices

    return () => {
      window.speechSynthesis.cancel()
      window.speechSynthesis.onvoiceschanged = null
    }
  }, [canSpeak])

  const stopSpeaking = useCallback(() => {
    if (!canSpeak) return
    window.speechSynthesis.cancel()
    setIsSpeaking(false)
    setActiveSegmentIndex(-1)
  }, [canSpeak])

  useEffect(() => {
    try {
      localStorage.setItem(VOICE_PREF_KEY, voiceType)
    } catch { /* ignore */ }
  }, [voiceType])

  // 朗读过程中：当前句滚进可视区域，避免长文时高亮句在视口外
  useEffect(() => {
    if (!isSpeaking || !bodyRef.current || !activeSegmentRef.current) return

    const body = bodyRef.current
    const active = activeSegmentRef.current
    const activeTop = active.offsetTop
    const activeBottom = activeTop + active.offsetHeight
    const visibleTop = body.scrollTop
    const visibleBottom = visibleTop + body.clientHeight

    if (activeTop < visibleTop + 12) {
      body.scrollTop = Math.max(activeTop - 18, 0)
    } else if (activeBottom > visibleBottom - 12) {
      body.scrollTop = activeBottom - body.clientHeight + 18
    }
  }, [activeSegmentIndex, isSpeaking])

  // 换一段新 reply 时：停掉上一轮朗读并重置高亮（避免旧 utterance 回调写状态）
  useEffect(() => {
    if (canSpeak) window.speechSynthesis.cancel()
    const resetTimer = window.setTimeout(() => {
      setIsSpeaking(false)
      setActiveSegmentIndex(-1)
    }, 0)
    return () => window.clearTimeout(resetTimer)
  }, [reply, canSpeak])

  // 卸载时清掉「已复制」定时器，防止内存泄漏
  useEffect(() => () => {
    if (copyTimerRef.current) window.clearTimeout(copyTimerRef.current)
  }, [])

  /** 复制后端返回的原始字符串（含换行）；无 Clipboard API 时用隐藏 textarea 兜底 */
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

  /** 用 SpeechSynthesisUtterance 朗读整段 reply；onboundary 驱动句级高亮 */
  const speakReply = () => {
    if (!canSpeak || !reply?.trim()) return

    window.speechSynthesis.cancel()
    setActiveSegmentIndex(0)

    const utterance = new SpeechSynthesisUtterance(reply)
    utterance.lang = 'zh-CN'
    utterance.rate = 1
    utterance.pitch = voiceType === 'male' ? 0.85 : 1.12
    utterance.volume = 1
    if (selectedVoice) utterance.voice = selectedVoice

    utterance.onboundary = (event) => {
      const index = findActiveSegmentIndex(replySegments, event.charIndex)
      if (index >= 0) setActiveSegmentIndex(index)
    }
    utterance.onend = () => {
      setIsSpeaking(false)
      setActiveSegmentIndex(-1)
    }
    utterance.onerror = () => {
      setIsSpeaking(false)
      setActiveSegmentIndex(-1)
    }

    setIsSpeaking(true)
    window.speechSynthesis.speak(utterance)
  }

  return (
    <div className="cp">
      {/* 标题栏 */}
      <div className="cp-head">
        <span className="cp-head-icon">💬</span>
        <span>小文回复</span>
      </div>
      {/* 正文：pre-wrap 保留换行；每句一个 span 便于高亮 */}
      <div className={`cp-body ${isSpeaking ? 'cp-body--speaking' : ''}`} ref={bodyRef}>
        {replySegments.length ? replySegments.map((segment, index) => (
          <span
            key={`${segment.start}-${segment.end}`}
            ref={index === activeSegmentIndex ? activeSegmentRef : null}
            className={`cp-segment ${index === activeSegmentIndex ? 'is-active' : ''} ${isSpeaking && index < activeSegmentIndex ? 'is-read' : ''}`}
          >
            {renderTextWithLinks(segment.text)}
          </span>
        )) : '（暂无内容）'}
      </div>

      {/* 复制整段 API 文本，与界面内链接渲染无关 */}
      <div className="cp-copy-row">
        <button
          type="button"
          className="cp-copy-btn"
          onClick={copyFullReply}
          disabled={!reply?.trim()}
          title="复制当前小文回复的完整纯文本"
        >
          {copyDone ? '已复制' : '复制全文'}
        </button>
      </div>

      {/* 朗读：音色下拉 + 开始/停止 */}
      <div className="cp-tts">
        <div className="cp-tts-label">
          <span>🔊 朗读回复</span>
          {selectedVoice && <small>{selectedVoice.name}</small>}
        </div>
        <div className="cp-tts-actions">
          <select
            value={voiceType}
            onChange={(e) => setVoiceType(e.target.value)}
            className="cp-tts-select"
            disabled={!canSpeak}
            title="选择朗读音色"
          >
            <option value="female">女音</option>
            <option value="male">男音</option>
          </select>
          <button
            type="button"
            className={`cp-tts-btn cp-tts-btn--primary ${isSpeaking ? 'is-speaking' : ''}`}
            onClick={speakReply}
            disabled={!canSpeak || !reply?.trim()}
          >
            {isSpeaking ? '重新朗读' : '开始朗读'}
          </button>
          <button
            type="button"
            className="cp-tts-btn"
            onClick={stopSpeaking}
            disabled={!canSpeak || !isSpeaking}
          >
            停止
          </button>
        </div>
        {!canSpeak && <p className="cp-tts-tip">当前浏览器不支持语音朗读，请使用 Chrome 或 Edge。</p>}
      </div>
    </div>
  )
}

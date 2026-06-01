/**
 * 讯飞 TTS 前端封装：`POST /api/tts`（ChatPanel、SelectionToolbar 共用）。
 * `voice` 传 vcn（如 x4_xiaoyan）或旧版预设键；音色偏好存 localStorage。
 */
import { apiFetch, apiUrl } from '../apiBase.js'
import { normalizeTtsVoice } from './ttsVoices.js'

export const TTS_API = apiUrl('/api/tts')
export const VOICE_PREF_KEY = 'xiaowen_tts_voice_type'

export function cleanupTtsAudio(ttsAudioRef, ttsObjectUrlRef) {
  const audio = ttsAudioRef?.current
  if (audio) {
    audio.pause()
    audio.src = ''
    audio.onended = null
    audio.onerror = null
    ttsAudioRef.current = null
  }
  const url = ttsObjectUrlRef?.current
  if (url) {
    URL.revokeObjectURL(url)
    ttsObjectUrlRef.current = null
  }
}

/** @returns {string} 朗读 vcn（优先同步偏好 / localStorage，交由后端 resolve_xfyun_vcn） */
export function getTtsVoiceFromStorage() {
  try {
    const raw = localStorage.getItem('xiaowen_user_preferences')
    if (raw) {
      const p = JSON.parse(raw)
      if (p.ttsVoice) return normalizeTtsVoice(p.ttsVoice)
    }
    let t = localStorage.getItem(VOICE_PREF_KEY)
    if (t === 'male') {
      t = 'x4_xiaoyan'
      try {
        localStorage.setItem(VOICE_PREF_KEY, t)
      } catch { /* ignore */ }
    }
    if (t) return normalizeTtsVoice(t)
    return 'x4_xiaoyan'
  } catch {
    return 'x4_xiaoyan'
  }
}

/**
 * @param {string} text
 * @param {React.MutableRefObject<HTMLAudioElement|null>} ttsAudioRef
 * @param {React.MutableRefObject<string|null>} ttsObjectUrlRef
 * @param {{ voice?: string }} [options] — 不传则用 localStorage 音色偏好
 * @returns {Promise<void>} 播放结束 resolve
 */
export async function playXfyunTts(text, ttsAudioRef, ttsObjectUrlRef, options = {}) {
  const trimmed = String(text || '').trim()
  if (!trimmed) {
    throw new Error('无朗读文本')
  }
  cleanupTtsAudio(ttsAudioRef, ttsObjectUrlRef)

  const voice = normalizeTtsVoice(options.voice || getTtsVoiceFromStorage())
  const res = await apiFetch('/api/tts', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text: trimmed, voice }),
    cache: 'no-store',
  })

  const ct = res.headers.get('Content-Type') || ''
  if (!res.ok) {
    let msg = `请求失败（HTTP ${res.status}）`
    if (ct.includes('application/json')) {
      const errJson = await res.json().catch(() => ({}))
      if (errJson.reply) msg = errJson.reply
    }
    throw new Error(msg)
  }

  if (ct.includes('application/json')) {
    const maybeJson = await res.json().catch(() => null)
    throw new Error(maybeJson?.reply || '朗读接口返回 JSON 异常')
  }

  // 5173 → 5001 跨域时部分浏览器不暴露 Content-Type，mime 为空则默认 WAV（与后端默认一致）
  let mime = (ct.split(';')[0] || '').trim()
  if (!mime.startsWith('audio/')) {
    mime = 'audio/wav'
  }
  const buf = await res.arrayBuffer()
  const blob = new Blob([buf], { type: mime })
  const objectUrl = URL.createObjectURL(blob)
  ttsObjectUrlRef.current = objectUrl

  const audio = new Audio(objectUrl)
  ttsAudioRef.current = audio

  return new Promise((resolve, reject) => {
    audio.onended = () => {
      URL.revokeObjectURL(objectUrl)
      ttsObjectUrlRef.current = null
      ttsAudioRef.current = null
      resolve()
    }
    audio.onerror = () => {
      URL.revokeObjectURL(objectUrl)
      ttsObjectUrlRef.current = null
      ttsAudioRef.current = null
      reject(new Error('音频播放失败'))
    }
    audio.play().catch(reject)
  })
}

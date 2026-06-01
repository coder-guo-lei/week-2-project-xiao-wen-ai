/**
 * 讯飞 TTS 前端封装：`POST /api/tts`（ChatPanel、SelectionToolbar 共用）。
 * `voice` 传音色预设键（female / female_jiuxu）或由后端解析的 vcn；音色偏好存 localStorage。
 */
import { apiFetch, apiUrl } from '../apiBase.js'

export const TTS_API = apiUrl('/api/tts')
export const VOICE_PREF_KEY = 'xiaowen_tts_voice_type'

/** 后端识别：female / female_jiuxu；具体 vcn 由后端按「在线合成 / 超拟人」自动映射 */
const TTS_VOICE_KEYS = new Set(['female', 'female_jiuxu'])

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

/** @returns {string} 朗读音色键（优先用户偏好 Context / localStorage） */
export function getTtsVoiceFromStorage() {
  try {
    const raw = localStorage.getItem('xiaowen_user_preferences')
    if (raw) {
      const p = JSON.parse(raw)
      if (TTS_VOICE_KEYS.has(p.ttsVoice)) return p.ttsVoice
    }
    let t = localStorage.getItem(VOICE_PREF_KEY) || 'female'
    if (t === 'male') {
      t = 'female'
      try {
        localStorage.setItem(VOICE_PREF_KEY, 'female')
      } catch { /* ignore */ }
    }
    return TTS_VOICE_KEYS.has(t) ? t : 'female'
  } catch {
    return 'female'
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

  const voice = options.voice || getTtsVoiceFromStorage()
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

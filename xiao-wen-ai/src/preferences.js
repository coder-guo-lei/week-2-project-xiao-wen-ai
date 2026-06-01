/**
 * 用户偏好：结构定义、持久化键、规范化（与后端 user_preferences 对齐）。
 */
import { storage } from './platform'

export const PREFS_STORAGE_KEY = 'xiaowen_user_preferences'
export const LEGACY_VOICE_KEY = 'xiaowen_tts_voice_type'

export const DEFAULT_PREFERENCES = {
  replyStyle: 'concise',
  ttsVoice: 'female',
  userNickname: '',
  assistantTone: 'friendly',
}

const VALID = {
  replyStyle: new Set(['concise', 'detailed']),
  ttsVoice: new Set(['female', 'female_jiuxu']),
  assistantTone: new Set(['friendly', 'professional']),
}

export function normalizePreferences(raw) {
  const base = { ...DEFAULT_PREFERENCES }
  if (!raw || typeof raw !== 'object') return base
  if (VALID.replyStyle.has(raw.replyStyle)) base.replyStyle = raw.replyStyle
  if (VALID.ttsVoice.has(raw.ttsVoice)) base.ttsVoice = raw.ttsVoice
  if (VALID.assistantTone.has(raw.assistantTone)) base.assistantTone = raw.assistantTone
  if (typeof raw.userNickname === 'string') {
    base.userNickname = raw.userNickname.trim().slice(0, 32)
  }
  return base
}

export function loadPreferences() {
  try {
    const parsed = JSON.parse(storage.get(PREFS_STORAGE_KEY) || '{}')
    const prefs = normalizePreferences(parsed)
    const legacyVoice = storage.get(LEGACY_VOICE_KEY)
    if (legacyVoice && VALID.ttsVoice.has(legacyVoice) && !parsed.ttsVoice) {
      prefs.ttsVoice = legacyVoice
    }
    return prefs
  } catch {
    return { ...DEFAULT_PREFERENCES }
  }
}

export function savePreferences(prefs) {
  const next = normalizePreferences(prefs)
  storage.set(PREFS_STORAGE_KEY, JSON.stringify(next))
  try {
    localStorage.setItem(LEGACY_VOICE_KEY, next.ttsVoice)
  } catch { /* ignore */ }
  return next
}

export const REPLY_STYLE_LABELS = {
  concise: '简洁（几句话）',
  detailed: '详细（适当展开）',
}

export const TONE_LABELS = {
  friendly: '亲切',
  professional: '专业',
}

export const TTS_VOICE_LABELS = {
  female: '女声 · 默认',
  female_jiuxu: '女声 · 许久 / 玉昭',
}

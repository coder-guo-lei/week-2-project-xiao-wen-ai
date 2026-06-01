/**
 * 后端偏好 tts_voice → 前端 localStorage 音色键映射
 */
import { VOICE_PREF_KEY } from './xfyunTts.js'
import { normalizeTtsVoice } from './ttsVoices.js'

export function syncTtsVoicePref(ttsVoice) {
  const mapped = normalizeTtsVoice(ttsVoice)
  try {
    localStorage.setItem(VOICE_PREF_KEY, mapped)
  } catch { /* ignore */ }
  return mapped
}

/** 是否尚未填写任何个性化偏好（用于首次引导） */
export function isPreferencesEmpty(prefs) {
  if (!prefs || typeof prefs !== 'object') return true
  const textKeys = ['display_name', 'role', 'interests']
  return textKeys.every((k) => !(prefs[k] || '').trim())
}

export function guideDismissKey(userId) {
  return `xiaowen-prefs-guide-seen-${userId}`
}

export function isGuideDismissed(userId) {
  if (!userId) return true
  try {
    return localStorage.getItem(guideDismissKey(userId)) === '1'
  } catch {
    return false
  }
}

export function dismissGuide(userId) {
  if (!userId) return
  try {
    localStorage.setItem(guideDismissKey(userId), '1')
  } catch { /* ignore */ }
}

export function markJustRegistered(userId) {
  if (!userId) return
  try {
    sessionStorage.setItem('xiaowen-just-registered', String(userId))
  } catch { /* ignore */ }
}

export function consumeJustRegistered(userId) {
  if (!userId) return false
  try {
    const v = sessionStorage.getItem('xiaowen-just-registered')
    if (v === String(userId)) {
      sessionStorage.removeItem('xiaowen-just-registered')
      return true
    }
  } catch { /* ignore */ }
  return false
}

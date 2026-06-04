/**
 * 后端 API 基址。
 * - Web 开发：默认 ''，走 Vite 代理
 * - Capacitor App：用 .env.capacitor 的 VITE_API_URL，或 Android 模拟器默认 10.0.2.2:5001
 */
import { Capacitor } from '@capacitor/core'

const _fromEnv = import.meta.env.VITE_API_URL ?? import.meta.env.VITE_API_BASE

function nativeApiFallback() {
  if (Capacitor.getPlatform() === 'android') return 'http://10.0.2.2:5001'
  return 'http://127.0.0.1:5001'
}

export const API_BASE =
  _fromEnv != null && String(_fromEnv).trim() !== ''
    ? String(_fromEnv).trim().replace(/\/$/, '')
    : Capacitor.isNativePlatform()
      ? nativeApiFallback()
      : import.meta.env.DEV
        ? ''
        : 'http://127.0.0.1:5001'

export function apiUrl(path) {
  const p = path.startsWith('/') ? path : `/${path}`
  if (!API_BASE) return p
  return `${API_BASE.replace(/\/$/, '')}${p}`
}

export async function apiFetch(path, options = {}) {
  const token = localStorage.getItem('xiaowen-token')
  const headers = { ...options.headers }
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }
  const res = await fetch(apiUrl(path), { ...options, headers })
  if (res.status === 401 && !path.includes('/api/auth/')) {
    window.dispatchEvent(new CustomEvent('xiaowen-auth-expired'))
  }
  return res
}

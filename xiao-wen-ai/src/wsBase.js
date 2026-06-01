/**
 * WebSocket 基址。
 * - Web 开发：直连 127.0.0.1:5001
 * - Capacitor：VITE_WS_URL 或从 VITE_API_URL 推导；Android 模拟器默认 ws://10.0.2.2:5001
 */
import { Capacitor } from '@capacitor/core'

function nativeWsFallback() {
  if (Capacitor.getPlatform() === 'android') return 'ws://10.0.2.2:5001'
  return 'ws://127.0.0.1:5001'
}

export function wsUrl(path = '/ws/sync') {
  const p = path.startsWith('/') ? path : `/${path}`
  const fromEnv = import.meta.env.VITE_WS_URL
  if (fromEnv != null && String(fromEnv).trim() !== '') {
    return `${String(fromEnv).trim().replace(/\/$/, '')}${p}`
  }
  if (Capacitor.isNativePlatform()) {
    const api = import.meta.env.VITE_API_URL ?? import.meta.env.VITE_API_BASE
    if (api != null && String(api).trim() !== '') {
      const base = String(api).trim().replace(/\/$/, '').replace(/^http/i, 'ws')
      return `${base}${p}`
    }
    return `${nativeWsFallback()}${p}`
  }
  if (import.meta.env.DEV) {
    return `ws://127.0.0.1:5001${p}`
  }
  const api = import.meta.env.VITE_API_URL ?? import.meta.env.VITE_API_BASE
  if (api != null && String(api).trim() !== '') {
    const base = String(api).trim().replace(/\/$/, '').replace(/^http/i, 'ws')
    return `${base}${p}`
  }
  return `ws://127.0.0.1:5001${p}`
}

/**
 * 后端 API 基址。
 * - 开发：默认 ''，请求 /api/* 走 Vite 代理到 5001（见 vite.config.js）
 * - 生产：默认直连本机 5001；部署到其它机器时设 VITE_API_URL 或 VITE_API_BASE（二者等价，任填其一）
 */
const _fromEnv = import.meta.env.VITE_API_URL ?? import.meta.env.VITE_API_BASE
export const API_BASE = (_fromEnv != null && String(_fromEnv).trim() !== '')
  ? String(_fromEnv).trim().replace(/\/$/, '')
  : (import.meta.env.DEV ? '' : 'http://127.0.0.1:5001')

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

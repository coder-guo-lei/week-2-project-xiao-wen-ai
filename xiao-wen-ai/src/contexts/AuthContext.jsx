import { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { apiFetch } from '../apiBase'
import { markJustRegistered } from '../utils/preferenceSync'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [token, setToken] = useState(() => localStorage.getItem('xiaowen-token'))
  const [loading, setLoading] = useState(true)

  const logout = useCallback(() => {
    localStorage.removeItem('xiaowen-token')
    setToken(null)
    setUser(null)
  }, [])

  useEffect(() => {
    if (!token) {
      setUser(null)
      setLoading(false)
      return
    }
    setLoading(true)
    apiFetch('/api/auth/me')
      .then((res) => {
        if (res.status === 401) throw new Error('unauthorized')
        return res.json()
      })
      .then((data) => {
        if (data.user) setUser(data.user)
        else logout()
      })
      .catch(() => logout())
      .finally(() => setLoading(false))
  }, [token, logout])

  useEffect(() => {
    const onExpired = () => logout()
    window.addEventListener('xiaowen-auth-expired', onExpired)
    return () => window.removeEventListener('xiaowen-auth-expired', onExpired)
  }, [logout])

  const login = useCallback(async (username, password) => {
    const res = await apiFetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    })
    const data = await res.json()
    if (!res.ok || data.error) return { success: false, error: data.error || '登录失败' }
    if (data.token) {
      localStorage.setItem('xiaowen-token', data.token)
      setToken(data.token)
      setUser(data.user)
      return { success: true }
    }
    return { success: false, error: '未知错误' }
  }, [])

  const register = useCallback(async (username, password, displayName) => {
    const res = await apiFetch('/api/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password, displayName }),
    })
    const data = await res.json()
    if (!res.ok || data.error) return { success: false, error: data.error || '注册失败' }
    if (data.token) {
      localStorage.setItem('xiaowen-token', data.token)
      setToken(data.token)
      setUser(data.user)
      markJustRegistered(data.user.id)
      return { success: true, isNewUser: true }
    }
    return { success: false, error: '未知错误' }
  }, [])

  return (
    <AuthContext.Provider value={{ user, token, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}

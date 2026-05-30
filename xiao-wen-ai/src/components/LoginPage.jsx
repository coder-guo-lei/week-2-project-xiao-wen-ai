import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import LoginParticleBg from './LoginParticleBg'
import './LoginPage.css'

export default function LoginPage() {
  const navigate = useNavigate()
  const { login, register } = useAuth()
  const [isRegister, setIsRegister] = useState(false)
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [displayName, setDisplayName] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setSubmitting(true)

    const result = isRegister
      ? await register(username, password, displayName)
      : await login(username, password)

    setSubmitting(false)
    if (!result.success) {
      setError(result.error)
      return
    }
    navigate('/', { replace: true })
  }

  return (
    <div className="login-page">
      <LoginParticleBg className="login-particle-bg" />
      <div className="login-card">
        <div className="login-header">
          <div className="login-logo-icon">W</div>
          <h1>小文智能助手</h1>
          <p>你的桌面 AI 伙伴</p>
        </div>

        <form onSubmit={handleSubmit} className="login-form">
          {error && <div className="login-error">{error}</div>}

          <input
            type="text"
            placeholder="用户名"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoFocus
          />
          <input
            type="password"
            placeholder="密码"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />

          {isRegister && (
            <input
              type="text"
              placeholder="显示名称（可选）"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
            />
          )}

          <button type="submit" disabled={submitting}>
            {submitting ? '处理中...' : isRegister ? '注册' : '登录'}
          </button>
        </form>

        <div className="login-switch">
          {isRegister ? '已有账号？' : '没有账号？'}
          <button type="button" onClick={() => { setIsRegister(!isRegister); setError('') }}>
            {isRegister ? '去登录' : '去注册'}
          </button>
        </div>
      </div>
    </div>
  )
}

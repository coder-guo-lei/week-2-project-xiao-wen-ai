/**
 * SettingsPanel.jsx — 个人偏好设置弹窗
 *
 * 6 项偏好：称呼、职业/角色、兴趣领域、回复风格、回复长度、TTS 音色。
 * 读取 /api/preferences，保存到 /api/preferences (PUT)。
 * 保存后关窗，下一次对话生效。
 */
import { useState, useEffect } from 'react'
import { apiFetch } from '../apiBase'
import { usePreferences } from '../contexts/PreferencesContext'
import { syncTtsVoicePref } from '../utils/preferenceSync'
import './SettingsPanel.css'

const FIELDS = [
  { key: 'display_name', label: '称呼', type: 'text', placeholder: '让小文怎么称呼你' },
  { key: 'role', label: '职业 / 角色', type: 'text', placeholder: '如：前端工程师、学生' },
  { key: 'interests', label: '兴趣领域', type: 'text', placeholder: '如：编程、摄影、音乐' },
  {
    key: 'language_style', label: '回复风格', type: 'select',
    options: [
      { value: 'casual', label: '轻松随意' },
      { value: 'formal', label: '正式专业' },
      { value: 'concise', label: '简洁精炼' },
    ],
  },
  {
    key: 'response_length', label: '回复长度', type: 'select',
    options: [
      { value: 'short', label: '简短' },
      { value: 'medium', label: '适中' },
      { value: 'long', label: '详细' },
    ],
  },
  {
    key: 'tts_voice', label: 'TTS 音色', type: 'select',
    options: [
      { value: 'default', label: '默认' },
      { value: 'gentle_female', label: '温柔女声' },
      { value: 'steady_male', label: '沉稳男声' },
    ],
  },
]

export default function SettingsPanel({ onClose }) {
  const { preferences, refreshPreferences } = usePreferences()
  const [prefs, setPrefs] = useState({})
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState('')

  useEffect(() => {
    if (preferences) {
      setPrefs(preferences)
      return
    }
    apiFetch('/api/preferences')
      .then((r) => r.json())
      .then((d) => setPrefs(d.preferences || {}))
      .catch(() => setMessage('加载失败'))
  }, [preferences])

  const handleChange = (key, value) => {
    setPrefs(prev => ({ ...prev, [key]: value }))
  }

  const handleSave = async () => {
    setSaving(true)
    setMessage('')
    try {
      const res = await apiFetch('/api/preferences', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(prefs),
      })
      if (!res.ok) throw new Error('save failed')
      syncTtsVoicePref(prefs.tts_voice)
      await refreshPreferences()
      setMessage('保存成功')
      setTimeout(() => onClose?.(), 600)
    } catch {
      setMessage('保存失败')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="settings-overlay" onClick={onClose}>
      <div className="settings-panel" onClick={e => e.stopPropagation()}>
        <div className="settings-header">
          <h3>个人偏好设置</h3>
          <p>这些设置将影响小文的回复风格，下次对话生效。</p>
        </div>

        <div className="settings-body">
          {FIELDS.map(field => (
            <div className="settings-field" key={field.key}>
              <label htmlFor={`pref-${field.key}`}>{field.label}</label>
              {field.type === 'text' ? (
                <input
                  id={`pref-${field.key}`}
                  type="text"
                  value={prefs[field.key] || ''}
                  onChange={e => handleChange(field.key, e.target.value)}
                  placeholder={field.placeholder}
                />
              ) : (
                <select
                  id={`pref-${field.key}`}
                  value={prefs[field.key] || field.options[0].value}
                  onChange={e => handleChange(field.key, e.target.value)}
                >
                  {field.options.map(opt => (
                    <option key={opt.value} value={opt.value}>{opt.label}</option>
                  ))}
                </select>
              )}
            </div>
          ))}
        </div>

        {message && (
          <div className={`settings-message${message === '保存成功' ? ' settings-message--ok' : ''}`}>
            {message}
          </div>
        )}

        <div className="settings-footer">
          <button onClick={onClose} className="btn-ghost">取消</button>
          <button onClick={handleSave} disabled={saving} className="btn-primary">
            {saving ? '保存中…' : '保存偏好'}
          </button>
        </div>
      </div>
    </div>
  )
}

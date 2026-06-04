/**
 * SettingsPanel.jsx — 个人偏好设置弹窗
 */
import { useState, useEffect } from 'react'
import { apiFetch } from '../apiBase'
import { usePreferences } from '../contexts/PreferencesContext'
import { syncTtsVoicePref } from '../utils/preferenceSync'
import TtsVoiceDualPicker from './TtsVoiceDualPicker'
import './SettingsPanel.css'

const TEXT_FIELDS = [
  { key: 'display_name', label: '称呼', placeholder: '让小文怎么称呼你' },
  { key: 'role', label: '职业 / 角色', placeholder: '如：前端工程师、学生' },
  { key: 'interests', label: '兴趣领域', placeholder: '如：编程、摄影、音乐' },
]

const SELECT_FIELDS = [
  {
    key: 'language_style',
    label: '回复风格',
    options: [
      { value: 'casual', label: '轻松随意' },
      { value: 'formal', label: '正式专业' },
      { value: 'concise', label: '简洁精炼' },
    ],
  },
  {
    key: 'response_length',
    label: '回复长度',
    options: [
      { value: 'short', label: '简短' },
      { value: 'medium', label: '适中' },
      { value: 'long', label: '详细' },
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
    setPrefs((prev) => ({ ...prev, [key]: value }))
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
      <div className="settings-panel" onClick={(e) => e.stopPropagation()}>
        <div className="settings-header">
          <h3>个人偏好设置</h3>
          <p>这些设置将影响小文的回复风格与朗读音色，下次对话生效。</p>
        </div>

        <div className="settings-body">
          {TEXT_FIELDS.map((field) => (
            <div className="settings-field" key={field.key}>
              <label htmlFor={`pref-${field.key}`}>{field.label}</label>
              <input
                id={`pref-${field.key}`}
                type="text"
                value={prefs[field.key] || ''}
                onChange={(e) => handleChange(field.key, e.target.value)}
                placeholder={field.placeholder}
              />
            </div>
          ))}
          {SELECT_FIELDS.map((field) => (
            <div className="settings-field" key={field.key}>
              <label htmlFor={`pref-${field.key}`}>{field.label}</label>
              <select
                id={`pref-${field.key}`}
                value={prefs[field.key] || field.options[0].value}
                onChange={(e) => handleChange(field.key, e.target.value)}
              >
                {field.options.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>
          ))}
          <div className="settings-field settings-field--tts">
            <label>TTS 朗读音色</label>
            <TtsVoiceDualPicker
              value={prefs.tts_voice || 'x4_xiaoyan'}
              onChange={(vcn) => handleChange('tts_voice', vcn)}
              disabled={saving}
            />
          </div>
        </div>

        {message && (
          <div
            className={`settings-message${message === '保存成功' ? ' settings-message--ok' : ''}`}
          >
            {message}
          </div>
        )}

        <div className="settings-footer">
          <button onClick={onClose} className="btn-ghost">
            取消
          </button>
          <button onClick={handleSave} disabled={saving} className="btn-primary">
            {saving ? '保存中…' : '保存偏好'}
          </button>
        </div>
      </div>
    </div>
  )
}

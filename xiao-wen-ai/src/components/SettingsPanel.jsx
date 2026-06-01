/**
 * 个人偏好设置面板 + 根据历史自动推荐（用户确认后写入）
 */
import { useMemo, useState } from 'react'
import { usePreferences } from '../context/PreferenceContext'
import {
  REPLY_STYLE_LABELS,
  TONE_LABELS,
  TTS_VOICE_LABELS,
} from '../preferences'
import {
  getActionableRecommendations,
  recommendPreferences,
  recommendationFingerprint,
} from '../utils/preferenceRecommend'
import { storage } from '../platform'
import './SettingsPanel.css'

const DISMISS_KEY = 'xiaowen_pref_reco_dismissed_fp'

function valueLabel(field, value) {
  if (field === 'replyStyle') return REPLY_STYLE_LABELS[value] || value
  if (field === 'assistantTone') return TONE_LABELS[value] || value
  if (field === 'ttsVoice') return TTS_VOICE_LABELS[value] || value
  return value
}

export default function SettingsPanel({
  open,
  onClose,
  commandHistory = [],
  chatHistory = [],
}) {
  const { preferences, setPreferences } = usePreferences()
  const [dismissedFp, setDismissedFp] = useState(() => storage.get(DISMISS_KEY) || '')

  const recoResult = useMemo(
    () => recommendPreferences({ commandHistory, chatHistory }),
    [commandHistory, chatHistory],
  )

  const actionable = useMemo(
    () => getActionableRecommendations(preferences, recoResult),
    [preferences, recoResult],
  )

  const fp = recommendationFingerprint(actionable)
  const showReco = actionable.length > 0 && fp !== dismissedFp

  const applyRecommendation = (item) => {
    setPreferences({ [item.field]: item.value })
  }

  const applyAllRecommendations = () => {
    const patch = Object.fromEntries(actionable.map((i) => [i.field, i.value]))
    setPreferences(patch)
    setDismissedFp(fp)
    storage.set(DISMISS_KEY, fp)
  }

  const dismissRecommendations = () => {
    setDismissedFp(fp)
    storage.set(DISMISS_KEY, fp)
  }

  if (!open) return null

  return (
    <div className="sp-overlay" role="presentation" onClick={onClose}>
      <div
        className="sp-panel"
        role="dialog"
        aria-labelledby="sp-title"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="sp-head">
          <h2 id="sp-title">⚙️ 个人偏好</h2>
          <button type="button" className="sp-close" onClick={onClose} aria-label="关闭">
            ✕
          </button>
        </header>
        <p className="sp-hint">以下选项会写入对话系统提示，并同步到其它已连接端。</p>

        {showReco && (
          <section className="sp-reco" aria-label="根据历史推荐">
            <h3 className="sp-reco-title">📊 根据历史推荐</h3>
            <p className="sp-reco-meta">
              已分析 {recoResult.sampleSize} 条本地记录（指令 + 对话），采纳后将注入系统提示。
            </p>
            <ul className="sp-reco-list">
              {actionable.map((item) => (
                <li key={item.field} className="sp-reco-item">
                  <div className="sp-reco-item-text">
                    <strong>{item.label}</strong>
                    <span> → {valueLabel(item.field, item.value)}</span>
                    <p className="sp-reco-reason">{item.reason}</p>
                  </div>
                  <button
                    type="button"
                    className="sp-reco-apply-one"
                    onClick={() => applyRecommendation(item)}
                  >
                    采纳
                  </button>
                </li>
              ))}
            </ul>
            <div className="sp-reco-actions">
              <button type="button" className="sp-reco-apply-all" onClick={applyAllRecommendations}>
                全部采纳
              </button>
              <button type="button" className="sp-reco-dismiss" onClick={dismissRecommendations}>
                暂不提示
              </button>
            </div>
          </section>
        )}

        {!recoResult.hasEnoughData && (
          <p className="sp-reco-empty">多使用几次小文（至少 3 条指令或对话）后，将自动生成偏好推荐。</p>
        )}

        <label className="sp-field">
          <span className="sp-label">回复风格</span>
          <select
            value={preferences.replyStyle}
            onChange={(e) => setPreferences({ replyStyle: e.target.value })}
          >
            {Object.entries(REPLY_STYLE_LABELS).map(([k, label]) => (
              <option key={k} value={k}>{label}</option>
            ))}
          </select>
        </label>

        <label className="sp-field">
          <span className="sp-label">助手语气</span>
          <select
            value={preferences.assistantTone}
            onChange={(e) => setPreferences({ assistantTone: e.target.value })}
          >
            {Object.entries(TONE_LABELS).map(([k, label]) => (
              <option key={k} value={k}>{label}</option>
            ))}
          </select>
        </label>

        <label className="sp-field">
          <span className="sp-label">称呼（可选）</span>
          <input
            type="text"
            maxLength={32}
            placeholder="例如：小明"
            value={preferences.userNickname}
            onChange={(e) => setPreferences({ userNickname: e.target.value })}
          />
        </label>

        <label className="sp-field">
          <span className="sp-label">朗读音色</span>
          <select
            value={preferences.ttsVoice}
            onChange={(e) => setPreferences({ ttsVoice: e.target.value })}
          >
            {Object.entries(TTS_VOICE_LABELS).map(([k, label]) => (
              <option key={k} value={k}>{label}</option>
            ))}
          </select>
        </label>
      </div>
    </div>
  )
}

/** 供 App 顶栏显示推荐角标 */
export function hasVisibleRecommendations(preferences, commandHistory, chatHistory) {
  const actionable = getActionableRecommendations(
    preferences,
    recommendPreferences({ commandHistory, chatHistory }),
  )
  const fp = recommendationFingerprint(actionable)
  if (actionable.length === 0) return false
  try {
    return fp !== storage.get(DISMISS_KEY)
  } catch {
    return true
  }
}

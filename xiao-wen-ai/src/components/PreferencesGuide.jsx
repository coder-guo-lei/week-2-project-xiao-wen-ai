import { dismissGuide } from '../utils/preferenceSync'
import { useAuth } from '../contexts/AuthContext'
import './PreferencesGuide.css'

export default function PreferencesGuide({ onSetup, onDismiss }) {
  const { user } = useAuth()
  const name = user?.displayName || user?.username || '朋友'

  const handleDismiss = () => {
    dismissGuide(user?.id)
    onDismiss?.()
  }

  const handleSetup = () => {
    dismissGuide(user?.id)
    onSetup?.()
  }

  return (
    <div className="pref-guide-overlay" role="dialog" aria-modal="true" aria-labelledby="pref-guide-title">
      <div className="pref-guide-card">
        <div className="pref-guide-icon">✨</div>
        <h3 id="pref-guide-title">欢迎，{name}！</h3>
        <p>
          花 30 秒设置称呼和回复风格，小文会按你的习惯来聊天。
          <br />
          也可稍后在右上角齿轮里随时修改。
        </p>
        <div className="pref-guide-actions">
          <button type="button" className="pref-guide-btn pref-guide-btn--primary" onClick={handleSetup}>
            去设置偏好
          </button>
          <button type="button" className="pref-guide-btn pref-guide-btn--ghost" onClick={handleDismiss}>
            稍后再说
          </button>
        </div>
      </div>
    </div>
  )
}

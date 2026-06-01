/**
 * 主题切换：浅色 / 深色 / 跟随系统
 */
import { useTheme } from '../context/ThemeContext'
import './ThemeToggle.css'

const OPTIONS = [
  { value: 'light', label: '浅色', icon: '☀️' },
  { value: 'dark', label: '深色', icon: '🌙' },
  { value: 'system', label: '系统', icon: '💻' },
]

export default function ThemeToggle() {
  const { mode, setMode } = useTheme()

  return (
    <div className="theme-toggle" role="group" aria-label="主题模式">
      {OPTIONS.map((opt) => (
        <button
          key={opt.value}
          type="button"
          className={`theme-toggle-btn ${mode === opt.value ? 'is-active' : ''}`}
          aria-pressed={mode === opt.value}
          title={opt.label}
          onClick={() => setMode(opt.value)}
        >
          <span className="theme-toggle-icon" aria-hidden>{opt.icon}</span>
          <span className="theme-toggle-label">{opt.label}</span>
        </button>
      ))}
    </div>
  )
}

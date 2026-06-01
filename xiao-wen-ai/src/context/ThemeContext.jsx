/**
 * 主题 Context：light / dark / system 三模式，持久化到 storage，支持多端 WS 同步。
 */
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from 'react'
import { storage } from '../platform'

const THEME_KEY = 'xiaowen-theme-mode'
const VALID_MODES = new Set(['light', 'dark', 'system'])

const ThemeContext = createContext(null)
const themeListeners = new Set()

function readStoredMode() {
  const saved = storage.get(THEME_KEY)
  return VALID_MODES.has(saved) ? saved : 'system'
}

function applyThemeToDom(mode) {
  const root = document.documentElement
  if (mode === 'system') root.removeAttribute('data-theme')
  else root.setAttribute('data-theme', mode)
}

function getSystemDark() {
  if (typeof window === 'undefined') return false
  return window.matchMedia('(prefers-color-scheme: dark)').matches
}

/** 订阅用户主动切换主题（用于 WebSocket 广播，非 fromSync） */
export function onThemeChange(listener) {
  themeListeners.add(listener)
  return () => themeListeners.delete(listener)
}

export function ThemeProvider({ children }) {
  const [mode, setModeState] = useState(readStoredMode)
  const [systemDark, setSystemDark] = useState(getSystemDark)

  const resolved = mode === 'system' ? (systemDark ? 'dark' : 'light') : mode

  useEffect(() => {
    applyThemeToDom(mode)
    storage.set(THEME_KEY, mode)
  }, [mode])

  useEffect(() => {
    applyThemeToDom(mode)
  }, [mode, systemDark])

  useEffect(() => {
    const mq = window.matchMedia('(prefers-color-scheme: dark)')
    const onChange = (e) => setSystemDark(e.matches)
    mq.addEventListener('change', onChange)
    return () => mq.removeEventListener('change', onChange)
  }, [])

  const setMode = useCallback((next, { fromSync = false } = {}) => {
    if (!VALID_MODES.has(next)) return
    setModeState(next)
    if (!fromSync) themeListeners.forEach((fn) => fn(next))
  }, [])

  const setModeFromSync = useCallback((next) => {
    setMode(next, { fromSync: true })
  }, [setMode])

  const value = useMemo(
    () => ({ mode, resolved, setMode, setModeFromSync }),
    [mode, resolved, setMode, setModeFromSync],
  )

  return (
    <ThemeContext.Provider value={value}>
      {children}
    </ThemeContext.Provider>
  )
}

export function useTheme() {
  const ctx = useContext(ThemeContext)
  if (!ctx) throw new Error('useTheme must be used within ThemeProvider')
  return ctx
}

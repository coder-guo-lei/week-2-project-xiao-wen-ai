/**
 * 用户偏好 Context：设置面板数据源，持久化，支持 WebSocket 多端同步。
 */
import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
} from 'react'
import {
  loadPreferences,
  normalizePreferences,
  savePreferences,
} from '../preferences'

const PreferenceContext = createContext(null)
const prefListeners = new Set()

export function onPreferencesChange(listener) {
  prefListeners.add(listener)
  return () => prefListeners.delete(listener)
}

export function PreferenceProvider({ children }) {
  const [preferences, setPreferencesState] = useState(loadPreferences)

  const setPreferences = useCallback((patch, { fromSync = false } = {}) => {
    setPreferencesState((prev) => {
      const next = savePreferences({ ...prev, ...patch })
      if (!fromSync) prefListeners.forEach((fn) => fn(next))
      return next
    })
  }, [])

  const setPreferencesFromSync = useCallback((raw) => {
    setPreferencesState(savePreferences(normalizePreferences(raw)))
  }, [])

  const value = useMemo(
    () => ({ preferences, setPreferences, setPreferencesFromSync }),
    [preferences, setPreferences, setPreferencesFromSync],
  )

  return (
    <PreferenceContext.Provider value={value}>
      {children}
    </PreferenceContext.Provider>
  )
}

export function usePreferences() {
  const ctx = useContext(PreferenceContext)
  if (!ctx) throw new Error('usePreferences must be used within PreferenceProvider')
  return ctx
}

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { apiFetch } from '../apiBase'
import { useAuth } from './AuthContext'
import {
  consumeJustRegistered,
  isGuideDismissed,
  isPreferencesEmpty,
  syncTtsVoicePref,
} from '../utils/preferenceSync'

const PreferencesContext = createContext(null)

export function PreferencesProvider({ children }) {
  const { user, token } = useAuth()
  const [preferences, setPreferences] = useState(null)
  const [ready, setReady] = useState(false)
  const [shouldShowGuide, setShouldShowGuide] = useState(false)

  const refreshPreferences = useCallback(async () => {
    if (!token) {
      setPreferences(null)
      setReady(true)
      return null
    }
    setReady(false)
    try {
      const res = await apiFetch('/api/preferences')
      const data = await res.json()
      const prefs = data.preferences || {}
      setPreferences(prefs)
      syncTtsVoicePref(prefs.tts_voice)
      return prefs
    } catch {
      setPreferences(null)
      return null
    } finally {
      setReady(true)
    }
  }, [token])

  useEffect(() => {
    refreshPreferences()
  }, [refreshPreferences])

  useEffect(() => {
    if (!user?.id || !ready || !preferences) {
      setShouldShowGuide(false)
      return
    }
    if (isGuideDismissed(user.id)) {
      setShouldShowGuide(false)
      return
    }
    const justRegistered = consumeJustRegistered(user.id)
    setShouldShowGuide(justRegistered || isPreferencesEmpty(preferences))
  }, [user?.id, ready, preferences])

  const value = useMemo(
    () => ({
      preferences,
      ready,
      shouldShowGuide,
      refreshPreferences,
      syncTtsVoicePref,
    }),
    [preferences, ready, shouldShowGuide, refreshPreferences],
  )

  return (
    <PreferencesContext.Provider value={value}>
      {children}
    </PreferencesContext.Provider>
  )
}

export function usePreferences() {
  const ctx = useContext(PreferencesContext)
  if (!ctx) throw new Error('usePreferences must be used within PreferencesProvider')
  return ctx
}

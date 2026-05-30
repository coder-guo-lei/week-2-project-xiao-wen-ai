import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from './contexts/AuthContext'
import { PreferencesProvider } from './contexts/PreferencesContext'
import LoginPage from './components/LoginPage'
import ProtectedRoute from './components/ProtectedRoute'
import App from './App'

export default function AppRouter() {
  const { user, loading } = useAuth()

  if (loading) {
    return <div className="app-loading">加载中...</div>
  }

  return (
    <Routes>
      <Route
        path="/login"
        element={user ? <Navigate to="/" replace /> : <LoginPage />}
      />
      <Route
        path="/*"
        element={
          <ProtectedRoute>
            <PreferencesProvider>
              <App />
            </PreferencesProvider>
          </ProtectedRoute>
        }
      />
    </Routes>
  )
}

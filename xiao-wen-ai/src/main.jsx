/**
 * 前端入口：把 React 根组件挂到 index.html 里的 <div id="root">。
 */
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import { ThemeProvider } from './context/ThemeContext'
import { PreferenceProvider } from './context/PreferenceContext'
import App from './App.jsx'

if (import.meta.env.PROD && import.meta.env.MODE !== 'capacitor') {
  import('virtual:pwa-register').then(({ registerSW }) => {
    registerSW({ immediate: true })
  })
}

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <ThemeProvider>
      <PreferenceProvider>
        <App />
      </PreferenceProvider>
    </ThemeProvider>
  </StrictMode>,
)

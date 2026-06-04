import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const isCapacitor = mode === 'capacitor'

  return {
    base: isCapacitor ? './' : '/',
    plugins: [
      react(),
      !isCapacitor &&
        VitePWA({
          registerType: 'autoUpdate',
          includeAssets: ['favicon.svg'],
          manifest: {
            name: '小文智能语音助手',
            short_name: '小文',
            description: '智能语音助手 — 对话、天气、音乐、图表等多模态交互',
            theme_color: '#3d8a80',
            background_color: '#f0ebe3',
            display: 'standalone',
            lang: 'zh-CN',
            start_url: '/',
            icons: [
              {
                src: '/favicon.svg',
                sizes: 'any',
                type: 'image/svg+xml',
                purpose: 'any',
              },
              {
                src: '/favicon.svg',
                sizes: 'any',
                type: 'image/svg+xml',
                purpose: 'maskable',
              },
            ],
          },
          workbox: {
            globPatterns: ['**/*.{js,css,html,ico,svg,woff2}'],
            navigateFallback: '/index.html',
            runtimeCaching: [
              {
                urlPattern: /^\/api\/.*/i,
                handler: 'NetworkOnly',
              },
            ],
          },
        }),
    ].filter(Boolean),
    server: {
      proxy: {
        '/api': {
          target: 'http://127.0.0.1:5001',
          changeOrigin: true,
        },
      },
    },
  }
})

/**
 * ImagePreview.jsx — AI 绘画结果展示
 *
 * 功能：
 *   - 生成中：旋转动画 + 实时计时
 *   - 生成完成：展示图片；点击图片放大查看；支持下载
 */
import { useCallback, useEffect, useState } from 'react'
import './ImagePreview.css'

function safeFilenameFromPrompt(text) {
  const base = (text || 'xiaowen-image').slice(0, 80).replace(/[/\\?%*:|"<>]/g, '_').trim() || 'xiaowen-image'
  return base
}

export default function ImagePreview({ imageUrl, prompt, generating = false, elapsed = 0 }) {
  const [lightboxOpen, setLightboxOpen] = useState(false)

  const closeLightbox = useCallback(() => setLightboxOpen(false), [])

  useEffect(() => {
    if (!lightboxOpen) return
    const onKey = (e) => {
      if (e.key === 'Escape') closeLightbox()
    }
    window.addEventListener('keydown', onKey)
    const prev = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      window.removeEventListener('keydown', onKey)
      document.body.style.overflow = prev
    }
  }, [lightboxOpen, closeLightbox])

  const handleDownload = useCallback(async () => {
    const name = `${safeFilenameFromPrompt(prompt)}.png`
    try {
      const res = await fetch(imageUrl, { mode: 'cors' })
      if (!res.ok) throw new Error('fetch failed')
      const blob = await res.blob()
      const ext = blob.type?.split('/')[1]
      const finalName = ext && ext !== 'octet-stream' ? `${safeFilenameFromPrompt(prompt)}.${ext.split('+')[0]}` : name
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = finalName
      a.rel = 'noopener'
      a.click()
      URL.revokeObjectURL(url)
    } catch {
      const a = document.createElement('a')
      a.href = imageUrl
      a.target = '_blank'
      a.rel = 'noopener noreferrer'
      a.click()
    }
  }, [imageUrl, prompt])

  if (generating) {
    return (
      <div className="ip ip--loading">
        <div className="ip-spinner" aria-label="生成中" />
        <p className="ip-loading-title">🎨 正在生成图片…</p>
        <p className="ip-loading-desc">{prompt}</p>
        <p className="ip-loading-timer">已等待 {elapsed} 秒</p>
        <p className="ip-loading-hint">Turbo 模型通常 10–30 秒内完成</p>
      </div>
    )
  }

  return (
    <div className="ip">
      <div className="ip-header">
        <p className="ip-title">🎨 {prompt || 'AI 生成图片'}</p>
        <div className="ip-actions">
          <button type="button" className="ip-btn" onClick={() => setLightboxOpen(true)}>
            放大查看
          </button>
          <button type="button" className="ip-btn ip-btn--primary" onClick={handleDownload}>
            下载
          </button>
        </div>
      </div>
      <div className="ip-frame ip-frame--interactive">
        <button
          type="button"
          className="ip-zoom-hit"
          onClick={() => setLightboxOpen(true)}
          aria-label="点击查看大图"
        >
          <img src={imageUrl} alt={prompt} className="ip-img" />
          <span className="ip-zoom-hint">点击查看大图</span>
        </button>
      </div>

      {lightboxOpen && (
        <div
          className="ip-lightbox"
          role="dialog"
          aria-modal="true"
          aria-label="大图预览"
          onClick={closeLightbox}
        >
          <button type="button" className="ip-lightbox-close" onClick={closeLightbox} aria-label="关闭">
            ×
          </button>
          <button type="button" className="ip-lightbox-download" onClick={(e) => { e.stopPropagation(); handleDownload() }}>
            下载图片
          </button>
          <div className="ip-lightbox-inner" onClick={(e) => e.stopPropagation()}>
            <img src={imageUrl} alt={prompt} className="ip-lightbox-img" />
          </div>
        </div>
      )}
    </div>
  )
}

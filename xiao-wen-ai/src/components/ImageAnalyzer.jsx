/**
 * ImageAnalyzer.jsx — 本地上传 / 拖拽 / 粘贴图片，送后端视觉理解
 *
 * Props:
 *   onAnalyze(file, question) — 由 App 调用 /api/analyze-image
 *   disabled — 请求进行中，禁止重复提交
 */
import { useCallback, useEffect, useRef, useState } from 'react'
import './ImageAnalyzer.css'

export default function ImageAnalyzer({ onAnalyze, disabled = false }) {
  const inputRef = useRef(null) // 隐藏 file input，由按钮 click() 触发
  const [preview, setPreview] = useState('') // blob: URL，用于本地预览
  const [dragging, setDragging] = useState(false) // 拖拽悬停时高亮边框
  const [question, setQuestion] = useState('') // 可选追问，一并 POST 给后端

  const submitFile = useCallback(
    (file) => {
      if (!file || disabled) return
      if (!file.type?.startsWith('image/')) return // 只接受图片 MIME
      const url = URL.createObjectURL(file)
      setPreview((old) => {
        if (old) URL.revokeObjectURL(old) // 释放上一张预览，避免内存泄漏
        return url
      })
      onAnalyze?.(file, question)
    },
    [disabled, onAnalyze, question],
  )

  // 全局粘贴：从剪贴板里找第一张图片文件（用户 Ctrl+V）
  const handlePaste = useCallback(
    (event) => {
      const file = Array.from(event.clipboardData?.files || []).find((item) =>
        item.type.startsWith('image/'),
      )
      if (file) submitFile(file)
    },
    [submitFile],
  )

  useEffect(() => {
    window.addEventListener('paste', handlePaste)
    return () => window.removeEventListener('paste', handlePaste)
  }, [handlePaste])

  // 卸载或 preview 变化前释放 blob URL
  useEffect(
    () => () => {
      if (preview) URL.revokeObjectURL(preview)
    },
    [preview],
  )

  return (
    <section
      className={`image-analyzer ${dragging ? 'image-analyzer--dragging' : ''}`}
      onDragOver={(event) => {
        event.preventDefault() // 允许 drop
        setDragging(true)
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={(event) => {
        event.preventDefault()
        setDragging(false)
        submitFile(
          Array.from(event.dataTransfer.files || []).find((item) => item.type.startsWith('image/')),
        )
      }}
    >
      <div className="image-analyzer__main">
        <div className="image-analyzer__icon">🖼️</div>
        <div>
          <h4>图片理解</h4>
          <p>支持点击上传、拖拽图片到这里，或直接复制图片后按 Ctrl + V。</p>
        </div>
      </div>

      {preview && <img className="image-analyzer__preview" src={preview} alt="待分析图片预览" />}

      <textarea
        className="image-analyzer__question"
        value={question}
        onChange={(event) => setQuestion(event.target.value)}
        placeholder="可选：想让小文重点分析什么？例如：提取文字、生成文案、判断场景..."
        rows={2}
      />

      <div className="image-analyzer__actions">
        <button type="button" disabled={disabled} onClick={() => inputRef.current?.click()}>
          {disabled ? '分析中...' : '选择本地图片'}
        </button>
        <span>也可以拖拽 / 粘贴图片</span>
      </div>

      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        hidden
        onChange={(event) => submitFile(event.target.files?.[0])}
      />
    </section>
  )
}

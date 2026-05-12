/**
 * FaceWellnessCamera — 前置摄像头抓拍人像，送后端 face_wellness 视觉分析
 *
 * Props:
 *   onAnalyze(file, question, options) — App 内转发到 /api/analyze-image，options.kind === 'face_wellness'
 *   disabled — 请求进行中
 */
import { useCallback, useEffect, useRef, useState } from 'react'
import './FaceWellnessCamera.css'

export default function FaceWellnessCamera({ onAnalyze, disabled = false }) {
  const videoRef = useRef(null)
  const streamRef = useRef(null)
  const [cameraOn, setCameraOn] = useState(false)
  const [hint, setHint] = useState('')
  const [note, setNote] = useState('')

  const stopCamera = useCallback(() => {
    streamRef.current?.getTracks().forEach((t) => t.stop())
    streamRef.current = null
    const v = videoRef.current
    if (v) v.srcObject = null
    setCameraOn(false)
  }, [])

  const startCamera = useCallback(async () => {
    setHint('')
    if (!navigator.mediaDevices?.getUserMedia) {
      setHint('当前环境不支持摄像头（需要 HTTPS 或 localhost）。')
      return
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: 'user',
          width: { ideal: 1280 },
          height: { ideal: 720 },
        },
        audio: false,
      })
      streamRef.current = stream
      const v = videoRef.current
      if (v) {
        v.srcObject = stream
        await v.play().catch(() => {})
      }
      setCameraOn(true)
    } catch {
      setHint('无法打开摄像头，请在浏览器设置中允许本站使用摄像头。')
    }
  }, [])

  useEffect(() => () => stopCamera(), [stopCamera])

  const captureAndAnalyze = useCallback(() => {
    if (disabled) return
    const v = videoRef.current
    if (!v || !v.videoWidth || !cameraOn) {
      setHint('请先开启摄像头并正对镜头，再抓拍分析。')
      return
    }
    const canvas = document.createElement('canvas')
    canvas.width = v.videoWidth
    canvas.height = v.videoHeight
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    ctx.drawImage(v, 0, 0)
    canvas.toBlob(
      (blob) => {
        if (!blob) {
          setHint('抓拍失败，请重试。')
          return
        }
        const file = new File([blob], 'camera-face.jpg', { type: 'image/jpeg' })
        onAnalyze?.(file, note.trim(), { kind: 'face_wellness' })
      },
      'image/jpeg',
      0.92,
    )
  }, [cameraOn, disabled, note, onAnalyze])

  return (
    <section id="face-wellness-anchor" className="face-camera">
      <div className="face-camera__main">
        <div className="face-camera__icon">📷</div>
        <div>
          <h4>肤质与状态洞察</h4>
          <p>
            开启摄像头后抓拍正面人像，小文会从肤质、气色与神态氛围等角度给出护理参考与生活建议。
            <span className="face-camera__disclaimer"> 结果仅供日常参考，不构成医疗或心理咨询。</span>
          </p>
        </div>
      </div>

      <div className="face-camera__video-wrap">
        <video
          ref={videoRef}
          className="face-camera__video"
          playsInline
          muted
          aria-label="摄像头预览"
        />
        {!cameraOn && (
          <div className="face-camera__placeholder">预览区域（开启摄像头后显示画面）</div>
        )}
      </div>

      {hint && <p className="face-camera__hint">{hint}</p>}

      <textarea
        className="face-camera__note"
        value={note}
        onChange={(e) => setNote(e.target.value)}
        placeholder="可选：补充说明（例如：最近熬夜多、换季敏感、想了解防晒步骤…）"
        rows={2}
        disabled={disabled}
      />

      <div className="face-camera__actions">
        {!cameraOn ? (
          <button type="button" disabled={disabled} onClick={startCamera}>
            开启摄像头
          </button>
        ) : (
          <>
            <button type="button" disabled={disabled} onClick={captureAndAnalyze}>
              {disabled ? '分析中…' : '抓拍并分析'}
            </button>
            <button type="button" className="face-camera__btn-secondary" disabled={disabled} onClick={stopCamera}>
              关闭摄像头
            </button>
          </>
        )}
      </div>
    </section>
  )
}

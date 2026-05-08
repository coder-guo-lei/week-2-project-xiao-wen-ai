/**
 * ImagePreview.jsx — AI 绘画结果展示
 *
 * 功能：
 *   - 生成中：显示旋转动画 + 实时计时（已等待 Xs）
 *   - 生成完成：展示图片，标题为生成时使用的 prompt
 * Props：
 *   imageUrl   {string}  图片 URL（生成完成后传入）
 *   prompt     {string}  描述文字，显示为标题
 *   generating {boolean} 是否正在生成中
 *   elapsed    {number}  已等待秒数
 */
import './ImagePreview.css'

export default function ImagePreview({ imageUrl, prompt, generating = false, elapsed = 0 }) {
  // 生成中：不展示 img，避免空 src；用计时与文案提示用户等待
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

  // 已完成：展示远程或 base64 图片地址
  return (
    <div className="ip">
      <p className="ip-title">🎨 {prompt || 'AI 生成图片'}</p>
      <div className="ip-frame">
        <img src={imageUrl} alt={prompt} className="ip-img" />
      </div>
    </div>
  )
}

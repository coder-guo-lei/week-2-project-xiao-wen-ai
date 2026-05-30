/**
 * SelectionToolbar.jsx — 划词工具条
 *
 * 选中文字后悬浮：翻译、读原文、读译文。翻译走后端；朗读与回复区一致，走讯飞 /api/tts。
 */
import { useCallback, useEffect, useRef, useState } from 'react'
import { apiFetch } from '../apiBase.js'
import { cleanupTtsAudio, playXfyunTts } from '../utils/xfyunTts'
import './SelectionToolbar.css'

const MAX_SELECTED_TEXT = 2000

function detectTargetLang(text) {
  return /[\u4e00-\u9fff]/.test(text) ? 'en' : 'zh'
}

function getSelectionPosition(selection) {
  if (!selection.rangeCount) return null
  const range = selection.getRangeAt(0)
  const rect = range.getBoundingClientRect()
  if (!rect.width && !rect.height) return null

  return {
    x: rect.left + rect.width / 2 + window.scrollX,
    y: rect.top + window.scrollY,
  }
}

export default function SelectionToolbar() {
  const [selectedText, setSelectedText] = useState('')
  const [position, setPosition] = useState(null)
  const [translation, setTranslation] = useState('')
  const [isTranslating, setIsTranslating] = useState(false)
  const [isSpeaking, setIsSpeaking] = useState(false)
  const [ttsErr, setTtsErr] = useState('')
  const [copyTip, setCopyTip] = useState('')
  const toolbarRef = useRef(null)
  const ttsAudioRef = useRef(null)
  const ttsObjectUrlRef = useRef(null)

  const hideToolbar = useCallback(() => {
    setSelectedText('')
    setPosition(null)
    setTranslation('')
    setIsTranslating(false)
    setCopyTip('')
    setTtsErr('')
    cleanupTtsAudio(ttsAudioRef, ttsObjectUrlRef)
    setIsSpeaking(false)
  }, [])

  useEffect(() => {
    const handleSelectionChange = () => {
      const selection = window.getSelection()
      const text = selection?.toString().trim() || ''

      if (!selection || !text || text.length < 1) {
        hideToolbar()
        return
      }

      const activeElement = document.activeElement
      const isEditable = activeElement?.matches?.('input, textarea, [contenteditable="true"]')
      if (isEditable) return

      const nextPosition = getSelectionPosition(selection)
      if (!nextPosition) return

      setSelectedText(text.slice(0, MAX_SELECTED_TEXT))
      setPosition(nextPosition)
      setTranslation('')
      setIsTranslating(false)
      setCopyTip('')
      setTtsErr('')
    }

    const handlePointerDown = (event) => {
      if (toolbarRef.current?.contains(event.target)) return
      const selection = window.getSelection()
      if (!selection?.toString().trim()) hideToolbar()
    }

    document.addEventListener('selectionchange', handleSelectionChange)
    document.addEventListener('pointerdown', handlePointerDown)

    return () => {
      document.removeEventListener('selectionchange', handleSelectionChange)
      document.removeEventListener('pointerdown', handlePointerDown)
      cleanupTtsAudio(ttsAudioRef, ttsObjectUrlRef)
    }
  }, [hideToolbar])

  const translateText = async (targetLang = detectTargetLang(selectedText)) => {
    if (!selectedText) return
    setIsTranslating(true)
    setTranslation('')

    try {
      const response = await apiFetch('/api/translate-selection', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: selectedText, targetLang }),
      })
      const data = await response.json()
      setTranslation(data.translation || '翻译失败，请稍后重试。')
    } catch {
      setTranslation('翻译失败：请确认 Python 后端服务已启动。')
    } finally {
      setIsTranslating(false)
    }
  }

  const stopSpeaking = useCallback(() => {
    cleanupTtsAudio(ttsAudioRef, ttsObjectUrlRef)
    setIsSpeaking(false)
  }, [])

  /** 与聊天区「朗读回复」相同：讯飞 TTS，音色随回复区男女偏好（localStorage） */
  const speakText = useCallback(async (text = selectedText) => {
    const raw = text !== undefined ? text : selectedText
    const t = String(raw || '').trim()
    if (!t) return

    stopSpeaking()
    setTtsErr('')
    setIsSpeaking(true)
    try {
      await playXfyunTts(t, ttsAudioRef, ttsObjectUrlRef)
    } catch (e) {
      console.error(e)
      setTtsErr(e?.message || '朗读失败')
    } finally {
      setIsSpeaking(false)
    }
  }, [selectedText, stopSpeaking])

  const copyTranslation = async () => {
    if (!translation) return
    try {
      await navigator.clipboard.writeText(translation)
      setCopyTip('已复制')
      window.setTimeout(() => setCopyTip(''), 1200)
    } catch {
      setCopyTip('复制失败')
    }
  }

  if (!selectedText || !position) return null

  return (
    <div
      ref={toolbarRef}
      className="selection-toolbar"
      style={{ left: position.x, top: Math.max(position.y - 12, 12) }}
    >
      <div className="selection-toolbar__actions">
        <button type="button" onClick={() => translateText('zh')} disabled={isTranslating}>
          转中文
        </button>
        <button type="button" onClick={() => translateText('en')} disabled={isTranslating}>
          转英文
        </button>
        <button type="button" onClick={() => speakText()} disabled={isSpeaking}>
          读原文
        </button>
        <button type="button" onClick={stopSpeaking} disabled={!isSpeaking}>
          停止
        </button>
      </div>

      {ttsErr && <div className="selection-toolbar__err">{ttsErr}</div>}

      {(isTranslating || translation) && (
        <div className="selection-toolbar__result">
          {isTranslating ? '正在翻译...' : translation}
          {translation && !isTranslating && (
            <div className="selection-toolbar__result-actions">
              <button type="button" onClick={() => speakText(translation)}>
                读译文
              </button>
              <button type="button" onClick={copyTranslation}>
                复制译文
              </button>
              {copyTip && <span>{copyTip}</span>}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

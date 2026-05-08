/**
 * SelectionToolbar.jsx — 划词工具条
 *
 * 用户在回复区或页面其它非输入区域选中文字后，自动弹出悬浮工具条。
 * 支持中英翻译、读原文、读译文和复制译文。翻译请求走后端，朗读走浏览器 TTS。
 */
import { useCallback, useEffect, useRef, useState } from 'react'
import './SelectionToolbar.css'

/** 划词过长时截断，避免翻译请求体过大 */
const MAX_SELECTED_TEXT = 2000

/** 含汉字则默认「译成英文」，否则「译成中文」 */
function detectTargetLang(text) {
  return /[\u4e00-\u9fff]/.test(text) ? 'en' : 'zh'
}

/** 取选区中心点的文档坐标，用于悬浮条 position:absolute */
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

/** TTS utterance.lang：中文内容用 zh-CN，否则 en-US */
function getSpeechLang(text) {
  return /[\u4e00-\u9fff]/.test(text) ? 'zh-CN' : 'en-US'
}

export default function SelectionToolbar() {
  const [selectedText, setSelectedText] = useState('')
  const [position, setPosition] = useState(null)
  const [translation, setTranslation] = useState('')
  const [isTranslating, setIsTranslating] = useState(false)
  const [isSpeaking, setIsSpeaking] = useState(false)
  const [copyTip, setCopyTip] = useState('')
  const toolbarRef = useRef(null) // 用于判断点击是否点在工具条内（不关闭）

  /** 清空选区相关状态，隐藏浮条 */
  const hideToolbar = useCallback(() => {
    setSelectedText('')
    setPosition(null)
    setTranslation('')
    setIsTranslating(false)
    setCopyTip('')
  }, [])

  // selectionchange：同步选中文本；pointerdown：点外部且无选区时收起
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
      window.speechSynthesis?.cancel()
    }
  }, [hideToolbar])

  /** POST /api/translate-selection，结果写入 translation */
  const translateText = async (targetLang = detectTargetLang(selectedText)) => {
    if (!selectedText) return
    setIsTranslating(true)
    setTranslation('')

    try {
      const response = await fetch('http://127.0.0.1:5001/api/translate-selection', {
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

  /** 浏览器 speechSynthesis 朗读任意字符串 */
  const speakText = (text = selectedText) => {
    if (!text || !('speechSynthesis' in window)) return
    window.speechSynthesis.cancel()

    const utterance = new SpeechSynthesisUtterance(text)
    utterance.lang = getSpeechLang(text)
    utterance.rate = 1
    utterance.pitch = 1
    utterance.onend = () => setIsSpeaking(false)
    utterance.onerror = () => setIsSpeaking(false)

    setIsSpeaking(true)
    window.speechSynthesis.speak(utterance)
  }

  const stopSpeaking = () => {
    if (!('speechSynthesis' in window)) return
    window.speechSynthesis.cancel()
    setIsSpeaking(false)
  }

  /** 把译文写入系统剪贴板 */
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

/**
 * useVoiceRecognition.js — 语音识别 Hook
 *
 * 封装两路 Web Speech API 识别器：
 *   1. 唤醒识别器（continuous）：持续监听，检测到唤醒词后触发指令识别
 *   2. 指令识别器（单次）：识别一句话后调用 onResult 回调并将结果传给 App
 *
 * 返回：
 *   isWakeActive        {boolean} 用户是否开启唤醒模式
 *   isCmdActive         {boolean} 指令识别进行中
 *   startCmdRecognition {fn}      手动触发一次指令识别
 *   stopCmdRecognition  {fn}      终止当前指令识别，并丢弃本次识别结果
 *   toggleWakeMode      {fn}      开启/关闭唤醒词持续监听
 *
 * 指令聆听：getUserMedia 在整段识别期间保持轨道打开；约 5 秒内识别不到任何语音则自动停止并提示。
 *
 * 源码结构（自上而下）：同音唤醒字典与正则 → 文本归一化/匹配 → 创建 Recognition 实例的工具函数
 * → 唤醒 continuous 监听与错误恢复 → 单次指令识别与无输入超时 → Hook 状态与对外 API。
 */
import { useState, useEffect, useRef, useCallback } from 'react'

/** 唤醒监听遇到这些 error 可尝试自动重启（权限未拒） */
const RECOVERABLE_WAKE_ERRORS = new Set(['aborted', 'no-speech', 'network'])
/** 用户拒麦等：不再自动重试，由 addLog 提示 */
const FATAL_WAKE_ERRORS = new Set(['not-allowed', 'service-not-allowed', 'audio-capture'])

/** 单次指令聆听：若识别引擎始终没有收到有效人声，自动停止（秒） */
const CMD_NO_INPUT_SEC = 5

/** 先占用麦克风再启动语音识别，避免立即释放轨道导致 Chrome 拾音失败 */
const CMD_AUDIO_CONSTRAINTS = {
  echoCancellation: true,
  noiseSuppression: true,
  autoGainControl: true,
}

/** ASR 常把「小文」写成这些形式（顺序长的放前面优先匹配叠词） */
const WAKE_NAMES = ['小文', '晓文', '筱文', '小雯', '小闻', '笑文', '效文', '小温', '孝文']
const WAKE_NAME_ALT = WAKE_NAMES.map((s) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|')

const RE_WAKE_DUP_STRIP = new RegExp(`^(?:${WAKE_NAME_ALT}){2}`)
const RE_WAKE_GREET_STRIP = new RegExp(`^(?:你好|嗨|嘿|哎|喂|呃|啊|嗯)+(?:${WAKE_NAME_ALT})`)
const RE_WAKE_NAME_STRIP = new RegExp(`^(?:${WAKE_NAME_ALT})`)
const RE_INTERIM_DUP_ONLY = new RegExp(`^(?:${WAKE_NAME_ALT}){2}$`)

/** 去掉空白与常见标点，便于匹配 ASR 输出 */
function normalizeWakeText(raw) {
  return String(raw || '')
    .replace(/\s+/g, '')
    .replace(/[，。！？、…·]/g, '')
}

/**
 * 是否命中唤醒词：支持「小文小文」、单次「小文」及常见同音/口语形式（识别引擎易把「小文」写成「晓文」等）
 */
function matchesWakePhrase(raw) {
  const t = normalizeWakeText(raw)
  if (!t) return false

  const dup = new RegExp(`(?:${WAKE_NAME_ALT}){2}`)
  if (dup.test(t)) return true
  if (t.includes('小文小文') || t.includes('晓文晓文')) return true

  // 以称呼开头：用户常说「小文，天气」「小文打开…」
  if (new RegExp(`^(?:${WAKE_NAME_ALT})`).test(t)) return true

  // 打招呼 + 称呼：你好小文、嗨小文、嘿小文等
  if (new RegExp(`^(?:你好|嗨|嘿|哎|喂|呃|啊|嗯)+(?:${WAKE_NAME_ALT})`).test(t)) return true

  // 整句很短且仅为称呼（避免长句里误含「小文」误触发）
  if (t.length <= 5 && new RegExp(`^(?:${WAKE_NAME_ALT})$`).test(t)) return true
  if (t.length <= 6 && new RegExp(`^(?:嗨|嘿)(?:${WAKE_NAME_ALT})$`).test(t)) return true
  if (t.length <= 8 && new RegExp(`^你好(?:${WAKE_NAME_ALT})$`).test(t)) return true

  return false
}

/**
 * 仅当「整句就是叠词称呼」时允许用 interim 命中唤醒：叠词说完 ASR 即可定型，比等 final 更快；
 * 不包含「以小文开头 + 指令」类句子，避免 interim 截断后半句。
 */
function matchesInterimWakeOnly(norm) {
  if (!norm || norm.length > 10) return false
  return RE_INTERIM_DUP_ONLY.test(norm)
}

/**
 * 从已归一化的文本里去掉唤醒称呼，得到可执行的指令片段。
 * 解决「小文打开抖音」整句只在唤醒通道出现一次、指令识别新开时已无声的问题。
 */
function stripWakePrefix(normalized) {
  let t = String(normalized || '')
  if (!t) return ''
  t = t.replace(RE_WAKE_DUP_STRIP, '')
  t = t.replace(RE_WAKE_GREET_STRIP, '')
  t = t.replace(RE_WAKE_NAME_STRIP, '')
  return t.trim()
}

export default function useVoiceRecognition({ onResult, addLog }) {
  const [isWakeActive, setIsWakeActive] = useState(false)
  const [isCmdActive, setIsCmdActive] = useState(false)

  const onResultRef = useRef(onResult)

  const SpeechRecognitionRef = useRef(null)
  const wakeRecRef = useRef(null)
  const cmdRecRef = useRef(null)
  const wakeWantedRef = useRef(false)
  const wakeRunningRef = useRef(false)
  const cmdRunningRef = useRef(false)
  const cancelCmdRef = useRef(false)
  const suppressWakeRestartRef = useRef(false)
  const wakeRestartTimerRef = useRef(null)
  const cmdStartTimerRef = useRef(null)
  const cmdStartPendingRef = useRef(false)
  const safeStartWakeRef = useRef(null)
  const wakeFireTsRef = useRef(0)
  /** 已成功拿过麦克风时降低预延迟（仍会为本次聆听单独占用轨道直至结束） */
  const micWarmRef = useRef(false)
  /** 指令聆听期间保持打开的 getUserMedia 流，不在 start 前立即 stop */
  const cmdMicStreamRef = useRef(null)
  const cmdNoInputTimerRef = useRef(null)

  const clearWakeRestartTimer = useCallback(() => {
    clearTimeout(wakeRestartTimerRef.current)
    wakeRestartTimerRef.current = null
  }, [])

  const clearCmdStartTimer = useCallback(() => {
    clearTimeout(cmdStartTimerRef.current)
    cmdStartTimerRef.current = null
  }, [])

  const clearCmdNoInputTimer = useCallback(() => {
    clearTimeout(cmdNoInputTimerRef.current)
    cmdNoInputTimerRef.current = null
  }, [])

  const releaseCmdMicStream = useCallback(() => {
    try {
      cmdMicStreamRef.current?.getTracks?.().forEach((t) => t.stop())
    } catch { /* ignore */ }
    cmdMicStreamRef.current = null
  }, [])

  const stopWakeRecognition = useCallback((suppressRestart = true) => {
    clearWakeRestartTimer()
    suppressWakeRestartRef.current = suppressRestart
    try { wakeRecRef.current?.stop() } catch { /* ignore */ }
    wakeRunningRef.current = false
  }, [clearWakeRestartTimer])

  const scheduleWakeRestart = useCallback((delay = 700) => {
    clearWakeRestartTimer()
    if (!wakeWantedRef.current || cmdRunningRef.current || suppressWakeRestartRef.current) return
    wakeRestartTimerRef.current = setTimeout(() => {
      safeStartWakeRef.current?.()
    }, delay)
  }, [clearWakeRestartTimer])

  useEffect(() => {
    onResultRef.current = onResult
  }, [onResult])

  const createCommandRecognition = useCallback(() => {
    const SpeechRecognition = SpeechRecognitionRef.current
    if (!SpeechRecognition) return null

    const rec = new SpeechRecognition()
    rec.lang = 'zh-CN'
    rec.continuous = false
    /** 有人声就开始重置「无输入」计时；仅最终结果提交指令 */
    rec.interimResults = true
    rec.maxAlternatives = 5

    rec.onresult = (event) => {
      for (let i = event.resultIndex || 0; i < event.results.length; i += 1) {
        const row = event.results[i]
        const text = row?.[0]?.transcript?.trim() || ''
        if (text) clearCmdNoInputTimer()
        if (!row.isFinal) continue

        cmdRunningRef.current = false
        cmdRecRef.current = null
        setIsCmdActive(false)
        suppressWakeRestartRef.current = false
        clearCmdNoInputTimer()

        if (cancelCmdRef.current) {
          cancelCmdRef.current = false
          scheduleWakeRestart(500)
          return
        }

        if (text) onResultRef.current?.(text)
        else addLog('⏱️ 未识别到有效语句，请重新点击语音再说一次')
        scheduleWakeRestart(600)
        return
      }
    }

    rec.onend = () => {
      clearCmdNoInputTimer()
      releaseCmdMicStream()
      cmdRunningRef.current = false
      cmdRecRef.current = null
      setIsCmdActive(false)
      suppressWakeRestartRef.current = false

      if (cancelCmdRef.current) {
        cancelCmdRef.current = false
        scheduleWakeRestart(500)
      }
    }

    rec.onerror = (event) => {
      clearCmdNoInputTimer()
      releaseCmdMicStream()
      const err = event?.error || ''

      /** 无输入超时等场景已先清状态再 abort，避免重复写日志与重复恢复唤醒 */
      if (err === 'aborted' && !cmdRunningRef.current && !cmdRecRef.current) {
        return
      }

      cmdRunningRef.current = false
      cmdRecRef.current = null
      setIsCmdActive(false)
      suppressWakeRestartRef.current = false

      if (cancelCmdRef.current || err === 'aborted') {
        cancelCmdRef.current = false
        scheduleWakeRestart(500)
        return
      }

      if (err === 'no-speech') {
        addLog('⏱️ 未检测到语音，请检查麦克风音量或默认输入设备后重试')
        scheduleWakeRestart(500)
        return
      }

      if (err === 'not-allowed' || err === 'service-not-allowed') {
        addLog('❌ 麦克风权限被拒绝，请在浏览器地址栏左侧点击锁图标 → 允许麦克风访问')
        micWarmRef.current = false
        wakeWantedRef.current = false
        setIsWakeActive(false)
        return
      }

      if (err === 'audio-capture') {
        addLog('❌ 未检测到麦克风，请检查麦克风是否已连接')
        micWarmRef.current = false
        wakeWantedRef.current = false
        setIsWakeActive(false)
        return
      }

      addLog(`❌ 语音识别失败${err ? `：${err}` : ''}`)
      scheduleWakeRestart(550)
    }

    return rec
  }, [addLog, clearCmdNoInputTimer, releaseCmdMicStream, scheduleWakeRestart])

  const startCmdRecognition = useCallback(() => {
    if (cmdRunningRef.current || cmdStartPendingRef.current) return
    clearCmdStartTimer()
    clearCmdNoInputTimer()
    releaseCmdMicStream()
    cancelCmdRef.current = false
    suppressWakeRestartRef.current = true
    stopWakeRecognition(true)

    cmdStartPendingRef.current = true
    const prepDelay = micWarmRef.current ? 90 : 220
    cmdStartTimerRef.current = setTimeout(() => {
      cmdStartPendingRef.current = false

      if (!SpeechRecognitionRef.current) {
        suppressWakeRestartRef.current = false
        addLog('❌ 浏览器不支持语音识别，请使用 Chrome / Edge')
        return
      }

      if (!navigator.mediaDevices?.getUserMedia) {
        suppressWakeRestartRef.current = false
        addLog('❌ 当前环境无法访问麦克风')
        return
      }

      navigator.mediaDevices.getUserMedia({ audio: CMD_AUDIO_CONSTRAINTS })
        .then((stream) => {
          cmdMicStreamRef.current = stream
          micWarmRef.current = true

          const rec = createCommandRecognition()
          if (!rec) {
            releaseCmdMicStream()
            suppressWakeRestartRef.current = false
            addLog('❌ 浏览器不支持语音识别，请使用 Chrome / Edge')
            return
          }

          cmdRecRef.current = rec
          cmdRunningRef.current = true
          setIsCmdActive(true)
          addLog(`🎙️ 正在聆听（${CMD_NO_INPUT_SEC} 秒内无语音将自动停止）；请对准麦克风说话，也可点「终止语音」提前结束`)

          try {
            rec.start()
            clearCmdNoInputTimer()
            cmdNoInputTimerRef.current = setTimeout(() => {
              cmdNoInputTimerRef.current = null
              if (!cmdRunningRef.current || cancelCmdRef.current) return
              const oldRec = cmdRecRef.current
              addLog(`⏱️ ${CMD_NO_INPUT_SEC} 秒内未检测到语音，已停止聆听。请靠近麦克风、调高输入音量，或在系统声音设置里选择正确的默认麦克风`)
              cmdRunningRef.current = false
              cmdRecRef.current = null
              setIsCmdActive(false)
              suppressWakeRestartRef.current = false
              releaseCmdMicStream()
              scheduleWakeRestart(600)
              try {
                oldRec?.abort()
              } catch {
                try {
                  oldRec?.stop()
                } catch { /* ignore */ }
              }
            }, CMD_NO_INPUT_SEC * 1000)
          } catch {
            cmdRunningRef.current = false
            cmdRecRef.current = null
            setIsCmdActive(false)
            releaseCmdMicStream()
            clearCmdNoInputTimer()
            suppressWakeRestartRef.current = false
            addLog('❌ 语音识别启动失败，请等待 1 秒后再试')
            scheduleWakeRestart(700)
          }
        })
        .catch(() => {
          suppressWakeRestartRef.current = false
          micWarmRef.current = false
          addLog('❌ 麦克风权限被拒绝，请在浏览器地址栏左侧点击锁图标 → 允许麦克风访问')
          wakeWantedRef.current = false
          setIsWakeActive(false)
        })
    }, prepDelay)
  }, [addLog, clearCmdNoInputTimer, clearCmdStartTimer, createCommandRecognition, releaseCmdMicStream, scheduleWakeRestart, stopWakeRecognition])

  const stopCmdRecognition = useCallback(() => {
    clearCmdStartTimer()
    clearCmdNoInputTimer()
    cmdStartPendingRef.current = false
    cancelCmdRef.current = true

    if (!cmdRunningRef.current && !cmdRecRef.current) {
      releaseCmdMicStream()
      setIsCmdActive(false)
      suppressWakeRestartRef.current = false
      scheduleWakeRestart(600)
      return
    }

    cmdRunningRef.current = false
    setIsCmdActive(false)
    addLog('⏹️ 已终止语音识别')

    try {
      cmdRecRef.current?.abort()
    } catch {
      try { cmdRecRef.current?.stop() } catch { /* ignore */ }
    }
    cmdRecRef.current = null
    releaseCmdMicStream()
    suppressWakeRestartRef.current = false
    scheduleWakeRestart(600)
  }, [addLog, clearCmdNoInputTimer, clearCmdStartTimer, releaseCmdMicStream, scheduleWakeRestart])

  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
    SpeechRecognitionRef.current = SpeechRecognition || null

    if (!SpeechRecognition) {
      addLog('❌ 浏览器不支持语音识别，请使用 Chrome / Edge')
      return undefined
    }

    const wakeRec = new SpeechRecognition()
    wakeRec.lang = 'zh-CN'
    wakeRec.continuous = true
    wakeRec.interimResults = true
    wakeRec.maxAlternatives = 5

    safeStartWakeRef.current = () => {
      if (!wakeWantedRef.current || cmdRunningRef.current || wakeRunningRef.current || suppressWakeRestartRef.current) return
      try {
        wakeRec.start()
        wakeRunningRef.current = true
        micWarmRef.current = true
      } catch {
        wakeRunningRef.current = false
        if (wakeWantedRef.current) scheduleWakeRestart(900)
      }
    }

    wakeRec.onresult = (event) => {
      if (cmdRunningRef.current || cmdStartPendingRef.current) return
      const now = Date.now()
      if (now - wakeFireTsRef.current < 280) return

      for (let i = event.resultIndex || 0; i < event.results.length; i += 1) {
        const result = event.results[i]
        const nAlt = result?.length ?? 1
        for (let a = 0; a < nAlt; a += 1) {
          const text = result?.[a]?.transcript?.trim() || ''
          const norm = normalizeWakeText(text)
          const interimOk = result?.isFinal || matchesInterimWakeOnly(norm)
          // 默认只用 final：避免「小文打开…」在 interim 阶段误触发；叠词「小文小文」允许 interim 提前触发
          if (!interimOk) continue
          if (!matchesWakePhrase(text)) continue
          const remainder = stripWakePrefix(norm)

          wakeFireTsRef.current = now
          suppressWakeRestartRef.current = true
          stopWakeRecognition(true)

          if (remainder) {
            addLog('🎉 唤醒成功，正在处理指令')
            setTimeout(() => {
              onResultRef.current?.(remainder)
              suppressWakeRestartRef.current = false
              if (wakeWantedRef.current) scheduleWakeRestart(550)
            }, 60)
          } else {
            addLog('🎉 唤醒成功！请说出指令')
            setTimeout(() => startCmdRecognition(), 320)
          }
          return
        }
      }
    }

    wakeRec.onend = () => {
      wakeRunningRef.current = false
      scheduleWakeRestart(550)
    }

    wakeRec.onerror = (event) => {
      const err = event?.error || ''
      wakeRunningRef.current = false

      if (FATAL_WAKE_ERRORS.has(err)) {
        if (err === 'not-allowed' || err === 'service-not-allowed' || err === 'audio-capture') {
          micWarmRef.current = false
        }
        wakeWantedRef.current = false
        setIsWakeActive(false)
        if (err === 'not-allowed' || err === 'service-not-allowed') {
          addLog('⚠️ 麦克风权限被拒绝，请在浏览器地址栏左侧点击锁图标 → 允许麦克风访问')
        } else if (err === 'audio-capture') {
          addLog('⚠️ 未检测到麦克风，请检查麦克风是否已连接')
        } else {
          addLog(`⚠️ 唤醒监听已停止${err ? `：${err}` : ''}`)
        }
        return
      }

      if (RECOVERABLE_WAKE_ERRORS.has(err) || !err) {
        scheduleWakeRestart(900)
        return
      }

      addLog(`⚠️ 唤醒监听异常${err ? `：${err}` : ''}，正在尝试恢复`)
      scheduleWakeRestart(1200)
    }

    wakeRecRef.current = wakeRec

    return () => {
      clearWakeRestartTimer()
      clearCmdStartTimer()
      clearCmdNoInputTimer()
      releaseCmdMicStream()
      cmdStartPendingRef.current = false
      wakeWantedRef.current = false
      suppressWakeRestartRef.current = true
      try { wakeRec.stop() } catch { /* ignore */ }
      try { cmdRecRef.current?.stop() } catch { /* ignore */ }
      wakeRunningRef.current = false
      cmdRunningRef.current = false
      wakeRecRef.current = null
      cmdRecRef.current = null
      safeStartWakeRef.current = null
      SpeechRecognitionRef.current = null
    }
  }, [addLog, clearCmdNoInputTimer, clearCmdStartTimer, clearWakeRestartTimer, releaseCmdMicStream, scheduleWakeRestart, startCmdRecognition, stopWakeRecognition])

  const toggleWakeMode = useCallback(() => {
    // 关闭唤醒：始终允许（即使正在聆听指令），避免界面卡住无法退出
    if (wakeWantedRef.current) {
      wakeWantedRef.current = false
      setIsWakeActive(false)
      stopCmdRecognition()
      stopWakeRecognition(true)
      setTimeout(() => { suppressWakeRestartRef.current = false }, 350)
      addLog('⚪ 唤醒监听已关闭')
      return
    }

    // 开启唤醒：避免与当前一次性语音识别叠加重叠
    if (cmdRunningRef.current || cmdStartPendingRef.current) {
      addLog('⚠️ 请先结束当前语音识别（点「终止语音」），再开启唤醒')
      return
    }

    if (!SpeechRecognitionRef.current) {
      addLog('❌ 浏览器不支持语音识别，请使用 Chrome / Edge')
      return
    }

    wakeWantedRef.current = true
    suppressWakeRestartRef.current = false
    setIsWakeActive(true)
    addLog('🟢 唤醒监听已开启：说「小文小文」响应最快；也可以说「小文」后直接讲指令')
    scheduleWakeRestart(120)
  }, [addLog, scheduleWakeRestart, stopCmdRecognition, stopWakeRecognition])

  return { isWakeActive, isCmdActive, startCmdRecognition, stopCmdRecognition, toggleWakeMode }
}

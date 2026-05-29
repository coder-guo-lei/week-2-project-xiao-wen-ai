/**
 * App.jsx — 根组件 / 应用编排层
 *
 * 职责：
 *   - 持有全局 UI 状态（当前展示类型、天气数据、图片、对话内容、模式栏等）
 *   - 调用 useMusicPlayer / useVoiceRecognition 两个 Hook
 *   - 向后端 /api/send-task 发送指令，根据返回 type / mode / resetUI 切换界面
 *   - 处理“再见小文”：先展示告别回复，再延迟回到初始默认面板
 *
 * 子组件：CommandInput、ModeBar、WorkflowPanel、左侧反馈区（DefaultPanel / Chat / Weather / Music / Image / Chart 等）、
 * ImageAnalyzer、FaceWellnessCamera、SelectionToolbar、右侧 LogPanel、吉祥物 XiaowenBot
 */
import { useState, useCallback, useEffect, useRef } from 'react'
import './App.css'

import CommandInput from './components/CommandInput'
import LogPanel from './components/LogPanel'
import MusicPlayer from './components/MusicPlayer'
import WeatherCard from './components/WeatherCard'
import ChatPanel from './components/ChatPanel'
import ImagePreview from './components/ImagePreview'
import DefaultPanel from './components/DefaultPanel'
import SelectionToolbar from './components/SelectionToolbar'
import ModeBar from './components/ModeBar'
import WorkflowPanel from './components/WorkflowPanel'
import ImageAnalyzer from './components/ImageAnalyzer'
import FaceWellnessCamera from './components/FaceWellnessCamera'
import ChartPanel from './components/ChartPanel'
import XiaowenBot from './components/XiaowenBot'

import useMusicPlayer from './hooks/useMusicPlayer'
import useVoiceRecognition from './hooks/useVoiceRecognition'
import { apiUrl } from './apiBase'

// ---------- 与 localStorage 同步的键名、列表长度上限 ----------
const COMMAND_HISTORY_KEY = 'xiaowen_command_history'
const CHAT_HISTORY_KEY = 'xiaowen_chat_history'
const MAX_COMMAND_HISTORY = 8
const MAX_CHAT_HISTORY = 12
/** 文生图轮询最长等待（毫秒）；略大于后端 IMAGE_TASK_TIMEOUT（默认 120s），避免无限轮询 */
const IMAGE_POLL_MAX_MS = 130_000

const LAST_LOC_KEY = 'xiaowen_last_client_location_v1'

/** 上次成功定位（会话内），getCurrentPosition 超时或拒权时可兜底 */
function readCachedClientLocation(maxAgeMs = 15 * 60 * 1000) {
  try {
    const raw = sessionStorage.getItem(LAST_LOC_KEY)
    if (!raw) return null
    const o = JSON.parse(raw)
    if (o == null || typeof o.lat !== 'number' || typeof o.lng !== 'number' || typeof o.t !== 'number') return null
    if (Date.now() - o.t > maxAgeMs) return null
    return { lat: o.lat, lng: o.lng, accuracy: o.accuracy }
  } catch {
    return null
  }
}

function writeCachedClientLocation(loc) {
  if (!loc || typeof loc.lat !== 'number' || typeof loc.lng !== 'number') return
  try {
    sessionStorage.setItem(LAST_LOC_KEY, JSON.stringify({ lat: loc.lat, lng: loc.lng, accuracy: loc.accuracy, t: Date.now() }))
  } catch { /* ignore */ }
}

/**
 * 浏览器定位（WGS84），供后端逆地理 / 当地天气 / 附近美食。
 * 适当延长等待；失败或超时后用会话内缓存兜底，减少「未带 location → 后端默认北京」的情况。
 */
function fetchClientLocation(timeoutMs = 6500) {
  if (typeof navigator === 'undefined' || !navigator.geolocation) {
    return Promise.resolve(readCachedClientLocation())
  }
  return new Promise((resolve) => {
    const fallback = () => readCachedClientLocation()
    const finish = (v) => {
      clearTimeout(tid)
      if (v) writeCachedClientLocation(v)
      resolve(v || fallback())
    }
    const tid = setTimeout(() => finish(null), timeoutMs)
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        finish({
          lat: pos.coords.latitude,
          lng: pos.coords.longitude,
          accuracy: pos.coords.accuracy,
        })
      },
      () => finish(null),
      {
        enableHighAccuracy: true,
        timeout: Math.max(4000, timeoutMs - 500),
        maximumAge: 120_000,
      },
    )
  })
}

function App() {
  // ---------- 输入与日志 ----------
  const [task, setTask] = useState('') // 与 CommandInput 受控绑定；发送成功后会清空
  const [logList, setLogList] = useState(['✅ 小文AI助手已就绪']) // 右侧 LogPanel 数据源
  // ---------- 左栏主展示区：根据 contentType 切换子组件 ----------
  const [contentType, setContentType] = useState('default')
  const [chatReply, setChatReply] = useState('') // ChatPanel 展示的纯文本
  const [chatHistory, setChatHistory] = useState(() => {
    try {
      const parsed = JSON.parse(localStorage.getItem(CHAT_HISTORY_KEY) || '[]')
      return Array.isArray(parsed) ? parsed.slice(-MAX_CHAT_HISTORY) : []
    } catch {
      return []
    }
  })
  const [weatherData, setWeatherData] = useState(null) // WeatherCard
  const [imageUrl, setImageUrl] = useState('') // 生成完成后的图片地址
  const [imagePrompt, setImagePrompt] = useState('') // 图片标题 / 生成中提示文案
  const [imageGenerating, setImageGenerating] = useState(false)
  const [imageElapsed, setImageElapsed] = useState(0) // 生成已等待秒数
  const [isSending, setIsSending] = useState(false) // 锁住重复点击发送
  const [mode, setMode] = useState('normal') // 后端业务 mode，传给 ModeBar
  const [modeLabel, setModeLabel] = useState('普通助手')
  const [worldState, setWorldState] = useState(null) // 模拟世界：主题、种子等
  const [quickActions, setQuickActions] = useState([]) // 世界模式快捷按钮文案列表
  const [workflowSteps, setWorkflowSteps] = useState([]) // WorkflowPanel 步骤
  const [isAnalyzingImage, setIsAnalyzingImage] = useState(false)
  const [chartData, setChartData] = useState(null) // ChartPanel 的 points 等
  const [isGeneratingChart, setIsGeneratingChart] = useState(false)
  const [commandHistory, setCommandHistory] = useState(() => {
    try {
      const parsed = JSON.parse(localStorage.getItem(COMMAND_HISTORY_KEY) || '[]')
      return Array.isArray(parsed) ? parsed.slice(0, MAX_COMMAND_HISTORY) : []
    } catch {
      return []
    }
  })
  const pollTimerRef = useRef(null) // 图片状态轮询 setInterval 句柄
  const elapsedTimerRef = useRef(null) // 每秒 +1 已等待时间
  const imagePollDeadlineRef = useRef(null) // 轮询绝对超时时间点（时间戳）
  const feedbackRef = useRef(null) // 「智慧助手空间」标题，用于 send 后 scrollIntoView

  const [userAppList, setUserAppList] = useState([])
  /** 后端 Windows 时可为 true，用于显示「浏览添加」按钮 */
  const [userExePickSupported, setUserExePickSupported] = useState(true)
  const [pickBrowseBusy, setPickBrowseBusy] = useState(false)
  /** 选完 exe 待用户确认名称：{ path, suggestedName } */
  const [addAppDraft, setAddAppDraft] = useState(null)
  const [addAppNameInput, setAddAppNameInput] = useState('')

  const music = useMusicPlayer() // 音乐播放状态与 <audio> ref 均在 Hook 内

  /** 追加一条右侧日志 */
  const addLog = useCallback((text) => {
    setLogList((prev) => [...prev, text])
  }, [])

  /** 清空右侧运行日志（手动按钮或语音识别成功即将发送指令时调用） */
  const clearLogList = useCallback(() => {
    setLogList([])
  }, [])

  /** 去重后把指令插到历史最前，并写入 localStorage */
  const rememberCommand = useCallback((cmdText) => {
    const trimmed = cmdText.trim()
    if (!trimmed) return
    setCommandHistory((prev) => {
      const next = [trimmed, ...prev.filter((item) => item !== trimmed)].slice(0, MAX_COMMAND_HISTORY)
      try { localStorage.setItem(COMMAND_HISTORY_KEY, JSON.stringify(next)) } catch { /* ignore */ }
      return next
    })
  }, [])

  /** 多轮对话：追加 user/assistant 各一条，截断长度并持久化 */
  const updateChatHistory = useCallback((userText, assistantText) => {
    const userContent = userText.trim()
    const assistantContent = (assistantText || '').trim()
    if (!userContent || !assistantContent) return

    setChatHistory((prev) => {
      const next = [
        ...prev,
        { role: 'user', content: userContent },
        { role: 'assistant', content: assistantContent },
      ].slice(-MAX_CHAT_HISTORY)
      try { localStorage.setItem(CHAT_HISTORY_KEY, JSON.stringify(next)) } catch { /* ignore */ }
      return next
    })
  }, [])

  /** 告别 resetUI 等场景：清空多轮上下文 */
  const clearChatHistory = useCallback(() => {
    setChatHistory([])
    try { localStorage.removeItem(CHAT_HISTORY_KEY) } catch { /* ignore */ }
  }, [])

  /** 清空天气/图/聊天/图表/音乐等「内容态」，不切 contentType（由调用方决定） */
  const resetAllContent = useCallback(() => {
    setWeatherData(null)
    setImageUrl('')
    setImagePrompt('')
    setImageGenerating(false)
    setImageElapsed(0)
    clearInterval(pollTimerRef.current)
    clearInterval(elapsedTimerRef.current)
    setChatReply('')
    setChartData(null)
    music.reset()
  }, [music])

  /** 回到默认左栏：DefaultPanel + 双图表面板入口等 */
  const returnToInitialView = useCallback(() => {
    resetAllContent()
    setContentType('default')
    setMode('normal')
    setModeLabel('普通助手')
    setWorldState(null)
    setQuickActions([])
    setWorkflowSteps([])
  }, [resetAllContent])

  // “再见小文”会先展示后端的告别语，再调用 returnToInitialView，避免用户看不到回应。

  /** DashScope 异步文生图：定时 GET /api/image-status/:taskId 直到成功/失败/超时 */
  const startImagePolling = useCallback((taskId) => {
    setImageGenerating(true)
    setImageElapsed(0)
    setContentType('image')
    imagePollDeadlineRef.current = Date.now() + IMAGE_POLL_MAX_MS

    elapsedTimerRef.current = setInterval(() => {
      setImageElapsed((s) => s + 1)
    }, 1000)

    pollTimerRef.current = setInterval(async () => {
      try {
        if (imagePollDeadlineRef.current != null && Date.now() > imagePollDeadlineRef.current) {
          clearInterval(pollTimerRef.current)
          clearInterval(elapsedTimerRef.current)
          setImageGenerating(false)
          setImagePrompt('生成超时，请稍后重试')
          addLog('❌ 图片生成超时（请检查网络或稍后重试）')
          imagePollDeadlineRef.current = null
          return
        }
        const r = await fetch(apiUrl(`/api/image-status/${taskId}`))
        const d = await r.json()
        if (d.status === 'succeeded' && d.imageUrl) {
          clearInterval(pollTimerRef.current)
          clearInterval(elapsedTimerRef.current)
          imagePollDeadlineRef.current = null
          setImageUrl(d.imageUrl)
          setImageGenerating(false)
          addLog('🎨 图片生成完成！')
        } else if (d.status === 'failed') {
          clearInterval(pollTimerRef.current)
          clearInterval(elapsedTimerRef.current)
          imagePollDeadlineRef.current = null
          setImageGenerating(false)
          setImagePrompt('生成失败，请重试')
          addLog('❌ 图片生成失败')
        }
      } catch {
        clearInterval(pollTimerRef.current)
        clearInterval(elapsedTimerRef.current)
        imagePollDeadlineRef.current = null
        setImageGenerating(false)
        addLog('❌ 查询图片状态失败')
      }
    }, 1500)
  }, [addLog])

  // 卸载根组件时务必清定时器，避免 StrictMode 双挂载或热更新泄漏
  useEffect(() => () => {
    clearInterval(pollTimerRef.current)
    clearInterval(elapsedTimerRef.current)
  }, [])

  const refreshUserApps = useCallback(async () => {
    try {
      const r = await fetch(apiUrl('/api/user-apps'))
      const d = await r.json()
      if (d.code === 200 && Array.isArray(d.apps)) setUserAppList(d.apps)
    } catch { /* ignore */ }
  }, [])

  useEffect(() => {
    refreshUserApps()
    fetch(apiUrl('/api/capabilities'))
      .then((res) => res.json())
      .then((d) => {
        if (typeof d.userExePick === 'boolean') setUserExePickSupported(d.userExePick)
      })
      .catch(() => {})
  }, [refreshUserApps])

  /**
   * 核心：POST /api/send-task，按返回 type 切换界面与副作用。
   * 语音/示例按钮/历史点击最终都走到这里。
   */
  const autoSendTask = useCallback(async (cmdText) => {
    if (!cmdText.trim() || isSending) return
    setIsSending(true)
    setTask(cmdText)
    rememberCommand(cmdText)
    addLog(`📝 识别指令：${cmdText}`)

    try {
      const location = await fetchClientLocation(7000)
      const payload = { task: cmdText, history: chatHistory }
      if (location) payload.location = location

      const res = await fetch(apiUrl('/api/send-task'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      const data = await res.json()
      const apiErr =
        !res.ok || (typeof data.code === 'number' && data.code !== 200)
      if (apiErr) {
        const msg = data.reply || `请求失败（HTTP ${res.status}）`
        addLog(`❌ ${msg}`)
        setChatReply(msg)
        setContentType('chat')
        setTask('')
        setIsSending(false)
        return
      }
      addLog(`🤖 小文回复：${data.reply}`)
      setMode(data.mode || 'normal')
      setModeLabel(data.modeLabel || '普通助手')
      setWorldState(data.worldState || null)
      setQuickActions(data.quickActions || [])
      setWorkflowSteps(Array.isArray(data.workflow) ? data.workflow : [])
      resetAllContent()

      if (data.resetUI) {
        clearChatHistory()
        setChatReply(data.reply ?? '')
        setContentType('chat')
        window.setTimeout(() => {
          returnToInitialView()
        }, 1800)
      } else if (data.extraData) {
        setWeatherData(data.extraData)
        setContentType('weather')
      } else if (data.type === 'chart' && data.chartData) {
        // 后端已把文本数据解析成 chartData，前端只负责切换到图表组件并渲染。
        setChartData(data.chartData)
        setContentType('chart')
      } else if (data.type === 'chat' || data.type === 'app') {
        setChatReply(data.reply ?? '')
        if (data.type === 'chat') updateChatHistory(cmdText, data.reply ?? '')
        setContentType('chat')
      } else if (data.type === 'image_pending' && data.taskId) {
        // 异步图片：立即显示生成中状态，后台轮询
        setImagePrompt(data.prompt || 'AI生成图片')
        setImageUrl('')
        startImagePolling(data.taskId)
      } else if (data.imageUrl) {
        setImageUrl(data.imageUrl)
        setImagePrompt(data.prompt || 'AI生成图片')
        setContentType('image')
      } else if (data.type === 'music' && data.previewUrl) {
        const title = data.songName || '未知歌曲'
        music.enqueueTrack(data.previewUrl, title, {
          provider: data.musicProvider || 'audio',
          qishuiUrl: data.qishuiUrl || '',
          qishuiEmbedUrl: data.qishuiEmbedUrl || '',
        })
        setContentType('music')
      } else if (data.type === 'music_control' && data.musicAction) {
        let switched = false
        if (data.musicAction === 'next') switched = music.playNext()
        else if (data.musicAction === 'prev') switched = music.playPrevious()
        if (!switched) {
          addLog('⚠️ 播放列表为空，请先说「随便放首歌」或点一首再试「换一首」。')
        }
        setContentType('music')
      } else if (data.type === 'web') {
        const url = String(data.previewUrl || '').trim()
        const replyHead = String(data.reply || '').trim()
        const lines = []
        if (replyHead) lines.push(replyHead)
        if (url && /^https?:\/\//i.test(url)) {
          let opened = null
          try {
            opened = window.open(url, '_blank', 'noopener,noreferrer')
          } catch {
            /* 部分环境禁止脚本打开窗口 */
          }
          lines.push(`链接：${url}`)
          lines.push(
            opened
              ? '（已尝试在新标签页打开；若无页面请检查是否被拦截或稍候再点上方链接。）'
              : '（未打开新标签页：语音/发送后请求是异步的，浏览器常会拦截自动弹窗。请点击上方蓝色链接打开。）',
          )
        } else if (url) {
          lines.push(`链接：${url}`)
        }
        setChatReply(lines.join('\n'))
        setContentType('chat')
      } else {
        setContentType('default')
      }

      // 指令处理完后，将视口跳转到反馈区标题处
      setTimeout(() => {
        feedbackRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' })
      }, 100)

    } catch (err) {
      addLog('❌ 错误：请启动Python后端服务！')
      console.error(err)
      setMode('normal')
      setModeLabel('后端未连接')
      setWorldState(null)
      setQuickActions([])
      setWorkflowSteps([])
      resetAllContent()
    }
    setTask('')
    setIsSending(false)
  }, [addLog, returnToInitialView, resetAllContent, music, startImagePolling, isSending, rememberCommand, chatHistory, updateChatHistory, clearChatHistory])

  /** DefaultPanel 快捷示例：摄像头肤质入口滚动定位，不走后端 */
  const handleDefaultExample = useCallback((example) => {
    if (!example?.text) return
    if (example.type === 'face_camera') {
      addLog('📷 已定位「肤质与状态洞察」：请开启摄像头并点击「抓拍并分析」')
      setContentType('default')
      requestAnimationFrame(() => {
        document.getElementById('face-wellness-anchor')?.scrollIntoView({ behavior: 'smooth', block: 'center' })
      })
      return
    }
    autoSendTask(example.text)
  }, [addLog, autoSendTask])

  const voice = useVoiceRecognition({
    onResult: (text) => {
      setTask(text)
      clearLogList()
      autoSendTask(text)
    },
    addLog,
    /** 固定使用 Chrome / Edge Web Speech；讯飞听写易与控制台产品/协议不一致，暂不自动开启 */
    useXfyunAsr: false,
  })

  /** POST /api/generate-chart（multipart），成功后 setChartData + workflow */
  const generateChartFromFile = useCallback(async (file) => {
    if (!file || isGeneratingChart) return
    setIsGeneratingChart(true)
    setContentType('chart')
    setChartData(null)
    setWorkflowSteps([
      { title: '接收文件', detail: file.name || '本地数据文件' },
      { title: '解析数据', detail: '读取前两列作为名称和值' },
    ])
    addLog(`📊 生成图表：${file.name || '数据文件'}`)

    try {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('task', task || '生成柱状图')
      const res = await fetch(apiUrl('/api/generate-chart'), {
        method: 'POST',
        body: formData,
      })
      const data = await res.json()
      if (data.type !== 'chart' || !data.chartData) {
        throw new Error(data.reply || '图表生成失败')
      }
      setChartData(data.chartData)
      setMode(data.mode || 'chart')
      setModeLabel(data.modeLabel || '数据可视化')
      setWorkflowSteps(Array.isArray(data.workflow) ? data.workflow : [])
      addLog(`✅ ${data.reply || '图表生成完成'}`)
    } catch (err) {
      console.error(err)
      setChatReply(err.message || '图表生成失败，请检查文件格式。')
      setContentType('chat')
      setWorkflowSteps([
        { title: '接收文件', detail: file.name || '本地数据文件' },
        { title: '生成失败', detail: '请上传 CSV / TXT / Excel，前两列为名称和值' },
      ])
      addLog('❌ 图表生成失败')
    } finally {
      setIsGeneratingChart(false)
    }
  }, [addLog, isGeneratingChart, task])

  const handleCancelAddApp = useCallback(() => {
    setAddAppDraft(null)
    setAddAppNameInput('')
  }, [])

  const handleBrowsePickExe = useCallback(async () => {
    setPickBrowseBusy(true)
    addLog('📂 请在弹出的系统窗口中选择要加入白名单的 .exe 程序…')
    try {
      const res = await fetch(apiUrl('/api/user-apps/pick'), { method: 'POST' })
      const data = await res.json()
      if (data.code === 501) {
        addLog(`⚠️ ${data.message || '当前环境不支持浏览添加'}`)
        return
      }
      if (data.code !== 200 || !data.path) {
        addLog(data.message ? `ℹ️ ${data.message}` : '已取消选择')
        return
      }
      setAddAppDraft({ path: data.path, suggestedName: data.suggestedName || '我的应用' })
      setAddAppNameInput(data.suggestedName || '我的应用')
    } catch (err) {
      console.error(err)
      addLog('❌ 无法连接后端或弹窗失败，请确认本机已启动 Python 后端')
    } finally {
      setPickBrowseBusy(false)
    }
  }, [addLog])

  const handleConfirmAddApp = useCallback(async () => {
    if (!addAppDraft?.path) return
    const name = addAppNameInput.trim()
    if (!name) {
      addLog('❌ 请填写应用显示名称（例如用游戏名，之后说「打开某某」）')
      return
    }
    try {
      const res = await fetch(apiUrl('/api/user-apps'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, path: addAppDraft.path }),
      })
      const data = await res.json()
      if (data.code === 200) {
        addLog(`✅ ${data.message}`)
        setAddAppDraft(null)
        setAddAppNameInput('')
        refreshUserApps()
      } else {
        addLog(`❌ ${data.message || '添加失败'}`)
      }
    } catch (err) {
      console.error(err)
      addLog('❌ 添加请求失败')
    }
  }, [addAppDraft, addAppNameInput, addLog, refreshUserApps])

  const handleRemoveUserApp = useCallback(async (name) => {
    try {
      const res = await fetch(`${apiUrl('/api/user-apps')}?name=${encodeURIComponent(name)}`, { method: 'DELETE' })
      const data = await res.json()
      if (data.code === 200) {
        addLog(`✅ ${data.message}`)
        refreshUserApps()
      } else {
        addLog(`❌ ${data.message || '移除失败'}`)
      }
    } catch {
      addLog('❌ 移除请求失败')
    }
  }, [addLog, refreshUserApps])

  /** POST /api/analyze-image，百炼 VL；失败时把 workflow 最后一步设为错误说明 */
  const analyzeLocalImage = useCallback(async (file, question = '', options = {}) => {
    if (!file || isAnalyzingImage) return
    const kind = options.kind || ''
    setIsAnalyzingImage(true)
    setContentType('chat')
    setChatReply(kind === 'face_wellness' ? '正在分析人像与护理参考，请稍候…' : '正在分析图片，请稍候...')
    const recvDetail = kind === 'face_wellness' ? '摄像头人像抓拍' : (file.name || '本地图片')
    setWorkflowSteps([
      { title: '接收图片', detail: recvDetail },
      { title: '上传图片', detail: kind === 'face_wellness' ? '发送到肤质与状态洞察接口' : '发送到后端图片理解接口' },
    ])
    addLog(kind === 'face_wellness' ? '📷 肤质与状态分析（摄像头）' : `🖼️ 分析图片：${file.name || '粘贴图片'}`)

    try {
      const formData = new FormData()
      formData.append('image', file)
      formData.append('question', question)
      formData.append('kind', kind)
      const res = await fetch(apiUrl('/api/analyze-image'), {
        method: 'POST',
        body: formData,
      })
      const data = await res.json()
      if (typeof data.code === 'number' && data.code !== 200) {
        const msg = data.reply || '图片分析失败'
        setChatReply(msg)
        setWorkflowSteps([
          { title: '接收图片', detail: file.name || '本地图片' },
          { title: '分析失败', detail: msg },
        ])
        addLog(`❌ ${msg}`)
        return
      }
      setChatReply(data.reply || '图片分析完成，但没有返回内容。')
      setMode(data.mode || 'vision')
      setModeLabel(data.modeLabel || '图片理解')
      setWorkflowSteps(Array.isArray(data.workflow) ? data.workflow : [])
      addLog('✅ 图片分析完成')
    } catch (err) {
      console.error(err)
      setChatReply('图片分析失败，请确认后端服务已启动，并检查图片格式。')
      setWorkflowSteps([
        { title: '接收图片', detail: file.name || '本地图片' },
        { title: '分析失败', detail: '后端服务未连接或图片上传异常' },
      ])
      addLog('❌ 图片分析失败')
    } finally {
      setIsAnalyzingImage(false)
    }
  }, [addLog, isAnalyzingImage])

  return (
    <div className="app">
      <SelectionToolbar />
      <XiaowenBot />
      {/* 顶栏：产品名 */}
      <header className="app-header">
        <div className="app-logo">小文</div>
        <p className="app-subtitle">智能语音助手</p>
      </header>

      <div className="app-body">
        {/* 左栏：模式条 + 输入 + 按 contentType 切换的反馈栈 */}
        <aside className="panel panel--left">
          <ModeBar
            mode={mode}
            modeLabel={modeLabel}
            worldState={worldState}
            quickActions={quickActions}
            onQuickAction={autoSendTask}
          />
          <CommandInput
            task={task}
            setTask={setTask}
            onSend={autoSendTask}
            isCmdActive={voice.isCmdActive}
            isSending={isSending}
            startCmd={voice.startCmdRecognition}
            stopCmd={voice.stopCmdRecognition}
            toggleWake={voice.toggleWakeMode}
            isWakeActive={voice.isWakeActive}
            commandHistory={commandHistory}
            onHistoryClick={autoSendTask}
          />
          <h3 className="panel-title" ref={feedbackRef}>✨ 智慧助手空间</h3>
          <div className={`panel-content panel-content--${contentType}`}>
            <div className="feedback-stack">
              {/* 闲聊、网页链接摘要、应用打开结果等 */}
              {contentType === 'chat' && <ChatPanel reply={chatReply} />}
              {contentType === 'chart' && <ChartPanel data={chartData} onUpload={generateChartFromFile} disabled={isGeneratingChart} />}
              {contentType === 'weather' && <WeatherCard data={weatherData} />}
              {contentType === 'music' && music.previewUrl && <MusicPlayer music={music} />}
              {contentType === 'image' && (imageUrl || imageGenerating) && (
                <ImagePreview imageUrl={imageUrl} prompt={imagePrompt} generating={imageGenerating} elapsed={imageElapsed} />
              )}
              {contentType === 'default' && (
                <>
                  <ImageAnalyzer onAnalyze={analyzeLocalImage} disabled={isAnalyzingImage} />
                  <FaceWellnessCamera onAnalyze={analyzeLocalImage} disabled={isAnalyzingImage} />
                  <ChartPanel onUpload={generateChartFromFile} disabled={isGeneratingChart} />
                  <DefaultPanel
                    isCmdActive={voice.isCmdActive}
                    isWakeActive={voice.isWakeActive}
                    onExampleClick={handleDefaultExample}
                    userExePickSupported={userExePickSupported}
                    pickBrowseBusy={pickBrowseBusy}
                    userAppList={userAppList}
                    addAppDraft={addAppDraft}
                    addAppNameInput={addAppNameInput}
                    onAddAppNameChange={setAddAppNameInput}
                    onBrowsePickExe={handleBrowsePickExe}
                    onCancelAddApp={handleCancelAddApp}
                    onConfirmAddApp={handleConfirmAddApp}
                    onRemoveUserApp={handleRemoveUserApp}
                  />
                </>
              )}
              <WorkflowPanel steps={workflowSteps} />
            </div>
          </div>
        </aside>

        {/* right — 运行日志 */}
        <main className="panel panel--right">
          <LogPanel logs={logList} onClear={clearLogList} />
        </main>
      </div>
    </div>
  )
}

export default App

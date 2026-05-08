/**
 * App.jsx — 根组件 / 应用编排层
 *
 * 职责：
 *   - 持有全局 UI 状态（当前展示类型、天气数据、图片、对话内容、模式栏等）
 *   - 调用 useMusicPlayer / useVoiceRecognition 两个 Hook
 *   - 向后端 /api/send-task 发送指令，根据返回 type / mode / resetUI 切换界面
 *   - 处理“再见小文”：先展示告别回复，再延迟回到初始默认面板
 *
 * 子组件：CommandInput / 左侧反馈区（天气、聊天、图片、图表等）、右侧 LogPanel、吉祥物 XiaowenBot
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
import ChartPanel from './components/ChartPanel'
import XiaowenBot from './components/XiaowenBot'

import useMusicPlayer from './hooks/useMusicPlayer'
import useVoiceRecognition from './hooks/useVoiceRecognition'

// ---------- 与 localStorage 同步的键名、列表长度上限 ----------
const COMMAND_HISTORY_KEY = 'xiaowen_command_history'
const CHAT_HISTORY_KEY = 'xiaowen_chat_history'
const MAX_COMMAND_HISTORY = 8
const MAX_CHAT_HISTORY = 12
/** 与后端 IMAGE_TASK_TIMEOUT（默认 120s）大致对齐，避免前端永久轮询 */
/** 文生图轮询最长等待（毫秒），略大于后端 IMAGE_TASK_TIMEOUT，防止无限轮询 */
const IMAGE_POLL_MAX_MS = 130_000

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

  const music = useMusicPlayer() // 音乐播放状态与 <audio> ref 均在 Hook 内

  /** 追加一条右侧日志 */
  const addLog = useCallback((text) => {
    setLogList((prev) => [...prev, text])
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
        const r = await fetch(`http://127.0.0.1:5001/api/image-status/${taskId}`)
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
      const res = await fetch('http://127.0.0.1:5001/api/send-task', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ task: cmdText, history: chatHistory }),
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
      } else if (data.type === 'web') {
        setChatReply(`${data.reply}\n${data.previewUrl ? `链接：${data.previewUrl}` : ''}`)
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

  const voice = useVoiceRecognition({
    onResult: (text) => {
      setTask(text)
      autoSendTask(text)
    },
    addLog,
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
      const res = await fetch('http://127.0.0.1:5001/api/generate-chart', {
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

  /** POST /api/analyze-image，百炼 VL；失败时把 workflow 最后一步设为错误说明 */
  const analyzeLocalImage = useCallback(async (file, question = '') => {
    if (!file || isAnalyzingImage) return
    setIsAnalyzingImage(true)
    setContentType('chat')
    setChatReply('正在分析图片，请稍候...')
    setWorkflowSteps([
      { title: '接收图片', detail: file.name || '本地图片' },
      { title: '上传图片', detail: '发送到后端图片理解接口' },
    ])
    addLog(`🖼️ 分析图片：${file.name || '粘贴图片'}`)

    try {
      const formData = new FormData()
      formData.append('image', file)
      formData.append('question', question)
      const res = await fetch('http://127.0.0.1:5001/api/analyze-image', {
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
                  <ChartPanel onUpload={generateChartFromFile} disabled={isGeneratingChart} />
                  <DefaultPanel isCmdActive={voice.isCmdActive} isWakeActive={voice.isWakeActive} onExampleClick={autoSendTask} />
                </>
              )}
              <WorkflowPanel steps={workflowSteps} />
            </div>
          </div>
        </aside>

        {/* right — 运行日志 */}
        <main className="panel panel--right">
          <LogPanel logs={logList} />
        </main>
      </div>
    </div>
  )
}

export default App

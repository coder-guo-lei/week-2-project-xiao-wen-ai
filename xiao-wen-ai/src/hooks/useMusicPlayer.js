/**
 * useMusicPlayer.js — 音乐播放器状态 Hook
 *
 * 封装所有与音乐播放相关的状态和操作，供 MusicPlayer 组件使用：
 *   - 播放状态：isPlaying / currentTime / duration / audioError
 *   - 曲库管理：playHistory（最多 50 条，持久化到 localStorage）/ playIndex
 *   - 音量：volume（持久化到 localStorage）
 *   - 操作：enqueueTrack（入队并播放）/ jumpToTrack / togglePlayPause
 *            playPrevious / playNext / handleSeek / setVolume / reset
 *   - audioRef：挂载到 <audio> 元素
 *   - audioHandlers：onTimeUpdate / onEnded / onLoadedMetadata / onError 事件集合
 */
import { useState, useRef, useCallback, useEffect } from 'react'

const MUSIC_HISTORY_KEY = 'xiaowen_music_history'
const MUSIC_VOLUME_KEY = 'xiaowen_music_volume'
const MAX_HISTORY = 50

export default function useMusicPlayer() {
  // ---------- 与 <audio> 同步的播放进度 ----------
  const [isPlaying, setIsPlaying] = useState(false)
  const [currentTime, setCurrentTime] = useState(0)
  const [duration, setDuration] = useState(0)
  // ---------- 播放列表：每项含 url/title/provider 等，初始化时从 localStorage 恢复 ----------
  const [playHistory, setPlayHistory] = useState(() => {
    try {
      const raw = localStorage.getItem(MUSIC_HISTORY_KEY)
      if (!raw) return []
      const parsed = JSON.parse(raw)
      if (!Array.isArray(parsed)) return []
      return parsed
        .filter((x) => x && typeof x.url === 'string' && x.title)
        .map((x, i) => ({
          ...x,
          provider: x.provider || 'audio',
          qishuiUrl: x.qishuiUrl || '',
          qishuiEmbedUrl: x.qishuiEmbedUrl || '',
          id: x.id || `saved-${i}-${String(x.url).slice(-12)}`,
        }))
        .slice(-MAX_HISTORY)
    } catch {
      return []
    }
  })
  const [playIndex, setPlayIndex] = useState(-1) // 当前正在播的历史下标；-1 表示无
  const [audioError, setAudioError] = useState('') // decode / 网络错误时展示给用户
  const [previewUrl, setPreviewUrl] = useState('') // 当前 <audio src>
  const [songName, setSongName] = useState('未知歌曲')
  const [currentProvider, setCurrentProvider] = useState('audio') // 'audio' | 'qishui' 等
  const [qishuiUrl, setQishuiUrl] = useState('') // 汽水外链（新窗口）
  const [qishuiEmbedUrl, setQishuiEmbedUrl] = useState('') // 汽水 embed 地址

  const [volume, setVolumeState] = useState(() => {
    try {
      const v = parseFloat(localStorage.getItem(MUSIC_VOLUME_KEY) || '')
      return Number.isFinite(v) ? v : 0.75
    } catch {
      return 0.75
    }
  })

  const audioRef = useRef(null) // 由 MusicPlayer 里 <audio ref={audioRef}> 赋值
  const playHistoryRef = useRef([]) // 与 playHistory 同步，供回调里读最新列表避免闭包过期

  useEffect(() => {
    playHistoryRef.current = playHistory
  }, [playHistory])

  useEffect(() => {
    if (audioRef.current) audioRef.current.volume = volume
  }, [volume])

  const setVolume = useCallback((vol) => {
    setVolumeState(vol)
    try { localStorage.setItem(MUSIC_VOLUME_KEY, String(vol)) } catch { /* ignore */ }
  }, [])

  /** 写盘并同步 ref，供 remove/clear/enqueue 共用 */
  const persistHistory = useCallback((next) => {
    playHistoryRef.current = next
    try { localStorage.setItem(MUSIC_HISTORY_KEY, JSON.stringify(next)) } catch { /* ignore */ }
  }, [])

  /** 点击列表「播放」：切到指定索引并准备自动播放 */
  const jumpToTrack = useCallback((idx) => {
    const hist = playHistoryRef.current
    if (idx < 0 || idx >= hist.length) return
    const item = hist[idx]
    setPreviewUrl(item.url)
    setSongName(item.title)
    setCurrentProvider(item.provider || 'audio')
    setQishuiUrl(item.qishuiUrl || '')
    setQishuiEmbedUrl(item.qishuiEmbedUrl || '')
    setPlayIndex(idx)
    setAudioError('')
    setIsPlaying(true)
    setCurrentTime(0)
    setDuration(0)
  }, [])

  /** 后端返回新歌：追加历史末尾并立即播放入队项；重复 url 不重复插入 */
  const enqueueTrack = useCallback((url, title, meta = {}) => {
    const entry = {
      id: `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`,
      url,
      title,
      provider: meta.provider || 'audio',
      qishuiUrl: meta.qishuiUrl || '',
      qishuiEmbedUrl: meta.qishuiEmbedUrl || '',
    }
    setPlayHistory((prev) => {
      const next = prev.length && prev[prev.length - 1].url === entry.url
        ? prev
        : [...prev, entry].slice(-MAX_HISTORY)

      if (next !== prev) persistHistory(next)
      playHistoryRef.current = next
      const idx = next.length - 1
      queueMicrotask(() => {
        setPlayIndex(idx)
        setPreviewUrl(url)
        setSongName(title)
        setCurrentProvider(entry.provider)
        setQishuiUrl(entry.qishuiUrl)
        setQishuiEmbedUrl(entry.qishuiEmbedUrl)
        setAudioError('')
        setIsPlaying(true)
      })
      return next
    })
  }, [persistHistory])

  /** 删除一条历史；若删的是当前曲则跳到相邻曲 */
  const removeTrack = useCallback((idx) => {
    const hist = playHistoryRef.current
    if (idx < 0 || idx >= hist.length) return

    const removingCurrent = idx === playIndex
    const next = hist.filter((_, i) => i !== idx)
    persistHistory(next)
    setPlayHistory(next)

    if (!next.length) {
      setPlayIndex(-1)
      setPreviewUrl('')
      setSongName('未知歌曲')
      setCurrentProvider('audio')
      setQishuiUrl('')
      setQishuiEmbedUrl('')
      setAudioError('')
      setIsPlaying(false)
      setCurrentTime(0)
      setDuration(0)
      return
    }

    if (removingCurrent) {
      const nextIdx = Math.min(idx, next.length - 1)
      const item = next[nextIdx]
      setPlayIndex(nextIdx)
      setPreviewUrl(item.url)
      setSongName(item.title)
      setCurrentProvider(item.provider || 'audio')
      setQishuiUrl(item.qishuiUrl || '')
      setQishuiEmbedUrl(item.qishuiEmbedUrl || '')
      setAudioError('')
      setIsPlaying(true)
      setCurrentTime(0)
      setDuration(0)
      return
    }

    if (idx < playIndex) setPlayIndex((prev) => prev - 1)
  }, [persistHistory, playIndex])

  /** 清空列表与当前播放 */
  const clearHistory = useCallback(() => {
    persistHistory([])
    setPlayHistory([])
    setPlayIndex(-1)
    setPreviewUrl('')
    setSongName('未知歌曲')
    setCurrentProvider('audio')
    setQishuiUrl('')
    setQishuiEmbedUrl('')
    setAudioError('')
    setIsPlaying(false)
    setCurrentTime(0)
    setDuration(0)
  }, [persistHistory])

  /** 播放 / 暂停切换；play() 失败写 audioError */
  const togglePlayPause = useCallback(() => {
    if (!audioRef.current) return
    if (isPlaying) {
      audioRef.current.pause()
    } else {
      audioRef.current.play().catch(() => {
        setAudioError('无法开始播放，可能受版权或浏览器策略限制。')
      })
    }
    setIsPlaying(!isPlaying)
  }, [isPlaying])

  /** 上一首：环形索引，依赖 jumpToTrack 统一设置 audio 源 */
  const playPrevious = useCallback(() => {
    const hist = playHistoryRef.current
    if (!hist.length) return false
    let idx = playIndex
    if (idx < 0 || idx >= hist.length) idx = hist.length - 1
    else idx = idx <= 0 ? hist.length - 1 : idx - 1
    jumpToTrack(idx)
    return true
  }, [playIndex, jumpToTrack])

  /** 下一首：环形索引 */
  const playNext = useCallback(() => {
    const hist = playHistoryRef.current
    if (!hist.length) return false
    let idx = playIndex
    if (idx < 0 || idx >= hist.length) idx = 0
    else idx = idx >= hist.length - 1 ? 0 : idx + 1
    jumpToTrack(idx)
    return true
  }, [playIndex, jumpToTrack])

  /** 点击进度条轨道：按点击水平位置比例设置 currentTime */
  const handleSeek = useCallback((e) => {
    const rect = e.currentTarget.getBoundingClientRect()
    const percent = (e.clientX - rect.left) / rect.width
    if (audioRef.current && duration > 0) {
      audioRef.current.currentTime = percent * duration
    }
  }, [duration])

  /** 告别或切模式时：清空当前播放展示（不删历史列表） */
  const reset = useCallback(() => {
    setPreviewUrl('')
    setSongName('未知歌曲')
    setCurrentProvider('audio')
    setQishuiUrl('')
    setQishuiEmbedUrl('')
    setAudioError('')
    setIsPlaying(false)
    setCurrentTime(0)
    setDuration(0)
  }, [])

  /** 展开到 <audio {...audioHandlers}>，保持 MusicPlayer 内联简洁 */
  const audioHandlers = {
    onTimeUpdate: (e) => setCurrentTime(e.target.currentTime),
    onEnded: () => setIsPlaying(false),
    onLoadedMetadata: (e) => setDuration(e.target.duration || 0),
    onError: () => {
      setAudioError('这首歌的音频地址暂时不能播放，可能是版权或外链失效。你可以说“换一首”或搜索其它歌曲。')
      setIsPlaying(false)
    },
  }

  // ---------- 对外 API：状态 + 方法，供 MusicPlayer 解构 ----------
  return {
    audioRef,
    previewUrl,
    songName,
    currentProvider,
    qishuiUrl,
    qishuiEmbedUrl,
    isPlaying,
    currentTime,
    duration,
    playHistory,
    playIndex,
    audioError,
    volume,
    setVolume,
    jumpToTrack,
    enqueueTrack,
    removeTrack,
    clearHistory,
    togglePlayPause,
    playPrevious,
    playNext,
    handleSeek,
    reset,
    audioHandlers,
  }
}

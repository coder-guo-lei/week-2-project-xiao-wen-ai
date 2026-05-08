/**
 * XiaowenBot.jsx — 桌面吉祥物
 *
 * - Pointer Events：按下拖动、松手根据速度启动惯性（requestAnimationFrame + 指数衰减 + 边缘反弹）
 * - prefers-reduced-motion：系统减少动效时不启用「甩出」惯性
 * - localStorage 持久化 left/top；resize 时夹紧在视口内
 * - SVG：西服（驳领+衬衫+领带）；抓取时整体下沉 +「被抓住」嘴眉；惯性旋转时迷糊眼
 * - 惯性结束后先滑落到底边，再在底边晕眩约 3s
 * - 靠在左/右边缘静置约 5s：缩进屏幕只露头探头 + 专用表情
 */
import { useCallback, useEffect, useRef, useState } from 'react'
import './XiaowenBot.css'

/** 随机切换的表情 key，与 CSS 中 .xiaowen-bot__mouth--* 对应 */
const MOODS = ['neutral', 'happy', 'curious', 'sleepy', 'surprised']
const STORAGE_KEY = 'xiaowen_bot_pos'
const DEFAULT_W = 112
const DEFAULT_H = 158
/** 距左右边缘小于此值视为「靠边」 */
const EDGE_NEAR_PX = 46
/** 靠边连续静置多久后触发探头 */
const EDGE_PEEK_AFTER_MS = 5000

/** 把 (x,y) 限制在视口内，留 pad 边距，避免机器人跑出屏幕 */
function clampPos(x, y, vw, vh, w, h) {
  const pad = 8
  return {
    x: Math.min(Math.max(pad, x), Math.max(pad, vw - w - pad)),
    y: Math.min(Math.max(pad, y), Math.max(pad, vh - h - pad)),
  }
}

export default function XiaowenBot() {
  const rootRef = useRef(null)
  const cardRef = useRef(null)
  const moodTimerRef = useRef(null)
  const blinkTimerRef = useRef(null)
  const inertiaRef = useRef(null)
  const dragRef = useRef(null)
  const velRef = useRef({ vx: 0, vy: 0 })
  const posRef = useRef({ x: 24, y: 24 })
  const dizzyTimerRef = useRef(null)
  const fallRafRef = useRef(null)
  const peekIdleTimerRef = useRef(null)

  const [pos, setPos] = useState({ x: 24, y: 24 })
  const [dragging, setDragging] = useState(false)
  /** 拖拽位移（相对起点），驱动衣服被抓摆方向 */
  const [dragPull, setDragPull] = useState({ dx: 0, dy: 0 })
  /** 惯性滑行中：整身快速旋转（丢出去） */
  const [inertiaSpin, setInertiaSpin] = useState(false)
  /** 惯性结束后晕一会 */
  const [dizzy, setDizzy] = useState(false)
  /** 靠边静置后：none | left | right 探头 */
  const [peekSide, setPeekSide] = useState('none')
  /** 滑落到底动画中，不参与靠边计时 */
  const [isFalling, setIsFalling] = useState(false)
  const [pupil, setPupil] = useState({ ox: 0, oy: 0 })
  const [mood, setMood] = useState('neutral')
  const [blink, setBlink] = useState(false)

  const clearDizzyTimer = useCallback(() => {
    if (dizzyTimerRef.current != null) {
      window.clearTimeout(dizzyTimerRef.current)
      dizzyTimerRef.current = null
    }
  }, [])

  const cancelFallAnimation = useCallback(() => {
    if (fallRafRef.current != null) {
      cancelAnimationFrame(fallRafRef.current)
      fallRafRef.current = null
    }
    setIsFalling(false)
  }, [])

  const getBotSize = useCallback(() => {
    const el = rootRef.current
    if (!el) return { w: DEFAULT_W, h: DEFAULT_H }
    const r = el.getBoundingClientRect()
    return { w: r.width || DEFAULT_W, h: r.height || DEFAULT_H }
  }, [])

  const applyClamp = useCallback((x, y) => {
    const { w, h } = getBotSize()
    return clampPos(x, y, window.innerWidth, window.innerHeight, w, h)
  }, [getBotSize])

  useEffect(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY)
      if (raw) {
        const p = JSON.parse(raw)
        if (typeof p.x === 'number' && typeof p.y === 'number') {
          const c = applyClamp(p.x, p.y)
          posRef.current = c
          setPos(c)
          return
        }
      }
    } catch { /* ignore */ }
    const { w, h } = { w: DEFAULT_W, h: DEFAULT_H }
    const initial = {
      x: Math.max(8, window.innerWidth - w - 24),
      y: Math.max(8, window.innerHeight - h - 24),
    }
    posRef.current = initial
    setPos(initial)
  }, [applyClamp])

  useEffect(() => {
    posRef.current = pos
  }, [pos])

  useEffect(() => {
    const onResize = () => setPos((p) => applyClamp(p.x, p.y))
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [applyClamp])

  const persistPos = useCallback((p) => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(p))
    } catch { /* ignore */ }
  }, [])

  const stopInertia = useCallback(() => {
    if (inertiaRef.current != null) {
      cancelAnimationFrame(inertiaRef.current)
      inertiaRef.current = null
    }
    velRef.current = { vx: 0, vy: 0 }
    setInertiaSpin(false)
  }, [])

  /** 惯性停后沿底边「滑落」到屏幕底缘，再执行 onDone（开始晕眩） */
  const animateFallToBottom = useCallback(
    (onDone) => {
      cancelFallAnimation()
      setIsFalling(true)
      const { w, h } = getBotSize()
      const pad = 8
      const maxX = Math.max(pad, window.innerWidth - w - pad)
      const targetY = Math.max(pad, window.innerHeight - h - pad)
      const start = { ...posRef.current }
      const targetX = Math.min(Math.max(pad, start.x), maxX)
      const duration = 480
      const t0 = performance.now()

      const easeOut = (t) => 1 - (1 - t) ** 3

      const tickFall = (now) => {
        const u = Math.min(1, (now - t0) / duration)
        const e = easeOut(u)
        const nx = start.x + (targetX - start.x) * e
        const ny = start.y + (targetY - start.y) * e
        const next = { x: nx, y: ny }
        posRef.current = next
        setPos(next)
        if (u < 1) {
          fallRafRef.current = requestAnimationFrame(tickFall)
        } else {
          fallRafRef.current = null
          persistPos(next)
          setIsFalling(false)
          onDone?.()
        }
      }
      fallRafRef.current = requestAnimationFrame(tickFall)
    },
    [getBotSize, persistPos, cancelFallAnimation],
  )

  /** vx,vy 单位：像素/秒（px/s）；滑行时开启旋转，停后晕眩数秒 */
  const startInertia = useCallback(
    (vx, vy) => {
      stopInertia()
      clearDizzyTimer()
      setDizzy(false)
      setInertiaSpin(true)
      velRef.current = { vx, vy }
      const decay = 10
      const bounce = 0.48
      let lastT = performance.now()

      const tick = (now) => {
        const dt = Math.min((now - lastT) / 1000, 0.06)
        lastT = now

        let { vx: vx0, vy: vy0 } = velRef.current
        const damp = Math.exp(-decay * dt)
        vx0 *= damp
        vy0 *= damp

        const speed = Math.hypot(vx0, vy0)
        if (speed < 28) {
          persistPos(posRef.current)
          stopInertia() // 内含 setInertiaSpin(false)
          const startDizzyAtBottom = () => {
            setDizzy(true)
            clearDizzyTimer()
            dizzyTimerRef.current = window.setTimeout(() => {
              setDizzy(false)
              dizzyTimerRef.current = null
            }, 3000)
          }
          const reduced = typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches
          if (reduced) {
            const { w, h } = getBotSize()
            const pad = 8
            const maxY = Math.max(pad, window.innerHeight - h - pad)
            const snapped = clampPos(posRef.current.x, maxY, window.innerWidth, window.innerHeight, w, h)
            posRef.current = snapped
            setPos(snapped)
            persistPos(snapped)
            startDizzyAtBottom()
          } else {
            animateFallToBottom(startDizzyAtBottom)
          }
          return
        }

        const { w, h } = getBotSize()
        const pad = 8
        const maxX = Math.max(pad, window.innerWidth - w - pad)
        const maxY = Math.max(pad, window.innerHeight - h - pad)

        setPos((p) => {
          let nx = p.x + vx0 * dt
          let ny = p.y + vy0 * dt
          let nvx = vx0
          let nvy = vy0

          if (nx < pad) {
            nx = pad
            nvx = -nvx * bounce
          } else if (nx > maxX) {
            nx = maxX
            nvx = -nvx * bounce
          }
          if (ny < pad) {
            ny = pad
            nvy = -nvy * bounce
          } else if (ny > maxY) {
            ny = maxY
            nvy = -nvy * bounce
          }

          velRef.current = { vx: nvx, vy: nvy }
          const next = { x: nx, y: ny }
          posRef.current = next
          return next
        })

        inertiaRef.current = requestAnimationFrame(tick)
      }

      inertiaRef.current = requestAnimationFrame(tick)
    },
    [getBotSize, stopInertia, persistPos, clearDizzyTimer, animateFallToBottom],
  )

  const updatePupil = useCallback((clientX, clientY) => {
    const el = rootRef.current
    if (!el) return
    const r = el.getBoundingClientRect()
    const faceCx = r.left + r.width / 2
    const faceCy = r.top + r.height * 0.36
    const dx = clientX - faceCx
    const dy = clientY - faceCy
    const len = Math.hypot(dx, dy) || 1
    const damp = Math.min(len / 140, 1)
    const maxX = 5.5
    const maxY = 4.2
    setPupil({
      ox: (dx / len) * maxX * damp,
      oy: (dy / len) * maxY * damp,
    })
  }, [])

  useEffect(() => {
    const onMove = (e) => updatePupil(e.clientX, e.clientY)
    window.addEventListener('mousemove', onMove, { passive: true })
    return () => window.removeEventListener('mousemove', onMove)
  }, [updatePupil])

  useEffect(() => {
    const pick = () => {
      const next = MOODS[Math.floor(Math.random() * MOODS.length)]
      setMood(next)
      moodTimerRef.current = window.setTimeout(pick, 4500 + Math.random() * 7500)
    }
    moodTimerRef.current = window.setTimeout(pick, 3000)
    return () => {
      if (moodTimerRef.current) clearTimeout(moodTimerRef.current)
    }
  }, [])

  useEffect(() => {
    let cancelled = false
    const blinkLoop = () => {
      if (cancelled) return
      setBlink(true)
      window.setTimeout(() => setBlink(false), 110)
      blinkTimerRef.current = window.setTimeout(blinkLoop, 2200 + Math.random() * 5200)
    }
    blinkTimerRef.current = window.setTimeout(blinkLoop, 1800)
    return () => {
      cancelled = true
      if (blinkTimerRef.current) clearTimeout(blinkTimerRef.current)
    }
  }, [])

  useEffect(
    () => () => {
      clearDizzyTimer()
      cancelFallAnimation()
      if (peekIdleTimerRef.current != null) {
        window.clearTimeout(peekIdleTimerRef.current)
        peekIdleTimerRef.current = null
      }
    },
    [clearDizzyTimer, cancelFallAnimation],
  )

  /** 靠左/右边缘不动超过 EDGE_PEEK_AFTER_MS → 探头；拖拽/惯性/晕/滑落时取消 */
  useEffect(() => {
    if (peekIdleTimerRef.current != null) {
      window.clearTimeout(peekIdleTimerRef.current)
      peekIdleTimerRef.current = null
    }

    if (dragging || inertiaSpin || dizzy || isFalling) {
      setPeekSide('none')
      return undefined
    }

    const vw = window.innerWidth
    const w = rootRef.current?.getBoundingClientRect().width || DEFAULT_W
    const pad = 8
    const distLeft = pos.x - pad
    const distRight = vw - w - pad - pos.x

    let edge = null
    if (distLeft <= EDGE_NEAR_PX && distRight <= EDGE_NEAR_PX) {
      edge = distLeft <= distRight ? 'left' : 'right'
    } else if (distLeft <= EDGE_NEAR_PX) {
      edge = 'left'
    } else if (distRight <= EDGE_NEAR_PX) {
      edge = 'right'
    }

    if (!edge) {
      setPeekSide('none')
      return undefined
    }

    /* 仍在靠边但每次位置变化都先缩回去，重新累计 5s「不动」 */
    setPeekSide('none')

    peekIdleTimerRef.current = window.setTimeout(() => {
      setPeekSide(edge)
      peekIdleTimerRef.current = null
    }, EDGE_PEEK_AFTER_MS)

    return () => {
      if (peekIdleTimerRef.current != null) {
        window.clearTimeout(peekIdleTimerRef.current)
        peekIdleTimerRef.current = null
      }
    }
  }, [pos.x, pos.y, dragging, inertiaSpin, dizzy, isFalling])

  const onPointerDown = useCallback(
    (e) => {
      if (e.button !== 0) return
      stopInertia()
      cancelFallAnimation()
      clearDizzyTimer()
      setDizzy(false)
      setPeekSide('none')
      setDragPull({ dx: 0, dy: 0 })
      e.preventDefault()
      cardRef.current?.setPointerCapture(e.pointerId)
      const startX = e.clientX
      const startY = e.clientY
      const { x: ox, y: oy } = posRef.current
      dragRef.current = {
        pointerId: e.pointerId,
        startX,
        startY,
        origX: ox,
        origY: oy,
        samples: [{ t: performance.now(), x: startX, y: startY }],
      }
      setDragging(true)
    },
    [stopInertia, clearDizzyTimer, cancelFallAnimation],
  )

  const onPointerMove = useCallback(
    (e) => {
      const d = dragRef.current
      if (!d || e.pointerId !== d.pointerId) return
      const nx = d.origX + (e.clientX - d.startX)
      const ny = d.origY + (e.clientY - d.startY)
      const now = performance.now()
      d.samples.push({ t: now, x: e.clientX, y: e.clientY })
      if (d.samples.length > 8) d.samples.shift()
      const next = applyClamp(nx, ny)
      posRef.current = next
      setPos(next)
      setDragPull({
        dx: Math.max(-42, Math.min(42, e.clientX - d.startX)),
        dy: Math.max(-42, Math.min(42, e.clientY - d.startY)),
      })
    },
    [applyClamp],
  )

  const endDrag = useCallback(
    (e) => {
      const d = dragRef.current
      if (!d || e.pointerId !== d.pointerId) return
      try {
        cardRef.current?.releasePointerCapture(e.pointerId)
      } catch { /* ignore */ }
      dragRef.current = null
      setDragging(false)
      setDragPull({ dx: 0, dy: 0 })

      const samples = d.samples
      let vx = 0
      let vy = 0
      if (samples.length >= 2) {
        const a = samples[samples.length - 1]
        const b = samples[Math.max(0, samples.length - 4)]
        const dtSec = (a.t - b.t) / 1000
        if (dtSec > 0.012) {
          vx = (a.x - b.x) / dtSec
          vy = (a.y - b.y) / dtSec
        }
      }

      persistPos(posRef.current)

      const speed = Math.hypot(vx, vy)
      const allowThrow =
        typeof window !== 'undefined' && !window.matchMedia('(prefers-reduced-motion: reduce)').matches
      if (allowThrow && speed > 380) {
        startInertia(vx, vy)
      }
    },
    [persistPos, startInertia],
  )

  return (
    // fixed 定位由 CSS 控制；left/top 为像素坐标；衣服摆角用 CSS 变量
    <div
      className={`xiaowen-bot ${dragging ? 'xiaowen-bot--dragging' : ''} ${inertiaSpin ? 'xiaowen-bot--inertia' : ''} ${dizzy ? 'xiaowen-bot--dizzy' : ''} ${peekSide === 'left' ? 'xiaowen-bot--peek-left' : ''} ${peekSide === 'right' ? 'xiaowen-bot--peek-right' : ''}`}
      ref={rootRef}
      style={{
        left: pos.x,
        top: pos.y,
        right: 'auto',
        bottom: 'auto',
        '--cloth-pull-x': String(dragPull.dx),
        '--cloth-pull-y': String(dragPull.dy),
      }}
      aria-hidden="true"
    >
      <div
        ref={cardRef}
        className={`xiaowen-bot__card xiaowen-bot__card--${mood}${dragging ? ' xiaowen-bot__card--grabbed' : ''}${peekSide !== 'none' ? ' xiaowen-bot__card--peek' : ''}`}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={endDrag}
        onPointerCancel={endDrag}
        onLostPointerCapture={endDrag}
        title="拖拽移动；靠边静置约 5 秒会探头；甩出去会转晕落底边再缓过来"
      >
        <div className="xiaowen-bot__figure">
        <svg className="xiaowen-bot__svg" viewBox="0 0 120 140" preserveAspectRatio="xMidYMid meet">
          {/* 渐变与轻微模糊滤镜 */}
          <defs>
            <linearGradient id="xiaowen-bot-body" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#818cf8" />
              <stop offset="55%" stopColor="#6366f1" />
              <stop offset="100%" stopColor="#4f46e5" />
            </linearGradient>
            <linearGradient id="xiaowen-bot-face" x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stopColor="#f8fafc" />
              <stop offset="100%" stopColor="#e0e7ff" />
            </linearGradient>
            <filter id="xiaowen-bot-soft" x="-20%" y="-20%" width="140%" height="140%">
              <feGaussianBlur in="SourceGraphic" stdDeviation="0.8" result="b" />
              <feMerge>
                <feMergeNode in="b" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>

          {/* 身体、脸部、耳朵 */}
          <ellipse cx="60" cy="118" rx="44" ry="18" fill="rgba(99,102,241,0.14)" />
          <ellipse cx="60" cy="92" rx="46" ry="42" fill="url(#xiaowen-bot-body)" stroke="#4338ca" strokeWidth="1.2" />

          <ellipse cx="60" cy="58" rx="40" ry="36" fill="url(#xiaowen-bot-face)" stroke="#a5b4fc" strokeWidth="1.4" />

          <circle cx="22" cy="54" r="9" fill="#818cf8" stroke="#6366f1" strokeWidth="1" />
          <circle cx="98" cy="54" r="9" fill="#818cf8" stroke="#6366f1" strokeWidth="1" />

          <ellipse
            cx="43"
            cy="54"
            rx="11"
            ry={blink ? 1.4 : 13}
            fill="#fff"
            stroke="#c7d2fe"
            strokeWidth="1"
            className="xiaowen-bot__eyelid"
          />
          {!blink && (
            <g transform={`translate(${43 + pupil.ox}, ${54 + pupil.oy})`} className="xiaowen-bot__pupil-mount">
              {inertiaSpin || dizzy ? (
                <g className="xiaowen-bot__pupil-orbit">
                  <circle r="6.8" cx="0" cy="0" fill="#e8eef7" stroke="#94a3b8" strokeWidth="0.65" className="xiaowen-bot__pupil-sclera" />
                  {/* 略偏心，绕中心转时像眼珠在眼窝里打滚 */}
                  <circle className="xiaowen-bot__pupil-dazed" r="3.1" cx="1.6" cy="-0.4" fill="#475569" />
                </g>
              ) : (
                <circle r="5.2" cx="0" cy="0" fill="#312e81" className="xiaowen-bot__pupil" />
              )}
            </g>
          )}
          <ellipse
            cx="77"
            cy="54"
            rx="11"
            ry={blink ? 1.4 : 13}
            fill="#fff"
            stroke="#c7d2fe"
            strokeWidth="1"
            className="xiaowen-bot__eyelid"
          />
          {!blink && (
            <g transform={`translate(${77 + pupil.ox}, ${54 + pupil.oy})`} className="xiaowen-bot__pupil-mount">
              {inertiaSpin || dizzy ? (
                <g className="xiaowen-bot__pupil-orbit">
                  <circle r="6.8" cx="0" cy="0" fill="#e8eef7" stroke="#94a3b8" strokeWidth="0.65" className="xiaowen-bot__pupil-sclera" />
                  <circle className="xiaowen-bot__pupil-dazed" r="3.1" cx="1.6" cy="-0.4" fill="#475569" />
                </g>
              ) : (
                <circle r="5.2" cx="0" cy="0" fill="#312e81" className="xiaowen-bot__pupil" />
              )}
            </g>
          )}

          {/* 眉毛、嘴（仅当前 mood 对应 path 在 CSS 中 display:block） */}
          <path
            className="xiaowen-bot__brow xiaowen-bot__brow--l"
            d="M32 38 Q43 34 54 38"
            fill="none"
            stroke="#6366f1"
            strokeWidth="2.2"
            strokeLinecap="round"
          />
          <path
            className="xiaowen-bot__brow xiaowen-bot__brow--r"
            d="M66 38 Q77 34 88 38"
            fill="none"
            stroke="#6366f1"
            strokeWidth="2.2"
            strokeLinecap="round"
          />

          <path className="xiaowen-bot__mouth xiaowen-bot__mouth--neutral" d="M44 74 Q60 82 76 74" fill="none" stroke="#4338ca" strokeWidth="2.4" strokeLinecap="round" />
          <path className="xiaowen-bot__mouth xiaowen-bot__mouth--happy" d="M42 76 Q60 92 78 76" fill="none" stroke="#4338ca" strokeWidth="2.6" strokeLinecap="round" />
          <path className="xiaowen-bot__mouth xiaowen-bot__mouth--curious" d="M52 78 Q60 84 68 76" fill="none" stroke="#4338ca" strokeWidth="2.4" strokeLinecap="round" />
          <line className="xiaowen-bot__mouth xiaowen-bot__mouth--sleepy" x1="46" y1="80" x2="74" y2="80" stroke="#4338ca" strokeWidth="2.2" strokeLinecap="round" />
          <ellipse className="xiaowen-bot__mouth xiaowen-bot__mouth--surprised" cx="60" cy="78" rx="6" ry="8" fill="none" stroke="#4338ca" strokeWidth="2.2" />
          <path
            className="xiaowen-bot__mouth xiaowen-bot__mouth--grabbed"
            d="M 46 80 Q 60 70 74 80"
            fill="none"
            stroke="#4338ca"
            strokeWidth="2.4"
            strokeLinecap="round"
          />
          {/* 靠边探头：抿嘴好奇 */}
          <ellipse
            className="xiaowen-bot__mouth xiaowen-bot__mouth--peek"
            cx="60"
            cy="79"
            rx="5"
            ry="3.5"
            fill="none"
            stroke="#4338ca"
            strokeWidth="2"
          />

          {/* 西服：衬衫 V 字、领带、深色驳领外套；抓取时整组 CSS 摆动 */}
          <g className="xiaowen-bot__clothes">
            <path
              d="M 52 78 L 60 96 L 68 78 L 64 82 L 60 92 L 56 82 Z"
              fill="#f1f5f9"
              stroke="#94a3b8"
              strokeWidth="0.75"
              strokeLinejoin="round"
            />
            <path d="M 58 82 L 62 82 L 60 102 Z" fill="#b91c1c" />
            <rect x="57.5" y="80" width="5" height="7" rx="0.8" fill="#991b1b" />
            <path
              className="xiaowen-bot__suit-lapel"
              d="M 38 84 L 33 116 Q 56 128 59 108 L 56 84 Q 48 80 38 84 Z"
              fill="#1e293b"
              stroke="#0f172a"
              strokeWidth="1"
              strokeLinejoin="round"
            />
            <path
              className="xiaowen-bot__suit-lapel"
              d="M 82 84 L 87 116 Q 64 128 61 108 L 64 84 Q 72 80 82 84 Z"
              fill="#1e293b"
              stroke="#0f172a"
              strokeWidth="1"
              strokeLinejoin="round"
            />
            <path
              d="M 48 76 L 54 72 L 60 76 L 66 72 L 72 76"
              fill="none"
              stroke="#334155"
              strokeWidth="1.8"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </g>

          <ellipse cx="28" cy="64" rx="7" ry="4" fill="rgba(236,72,153,0.18)" />
          <ellipse cx="92" cy="64" rx="7" ry="4" fill="rgba(236,72,153,0.18)" />

          <line x1="60" y1="22" x2="60" y2="8" stroke="#6366f1" strokeWidth="2.5" strokeLinecap="round" />
          <circle cx="60" cy="6" r="5" fill="#fbbf24" stroke="#f59e0b" strokeWidth="1" filter="url(#xiaowen-bot-soft)" />
        </svg>
        <span className="xiaowen-bot__label">小文</span>
        </div>
      </div>
    </div>
  )
}

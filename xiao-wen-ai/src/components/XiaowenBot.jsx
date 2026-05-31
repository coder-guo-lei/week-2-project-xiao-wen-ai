/**
 * XiaowenBot.jsx — 小文AI智能语音助手 · 桌面吉祥物
 * 造型：圆滚滚蛋形 — 哑光白主体 + 淡紫面罩 + 渐变蓝超大眼 + 能量核心 + 星环轨道 + 耳罩天线 + 短粗四肢
 * 交互：拖拽/惯性/晕眩/探头/表情/眼球跟随 | 点击：语音波形 + 消息气泡
 */
import { useCallback, useEffect, useId, useRef, useState } from 'react'
import './XiaowenBot.css'

const MOODS = ['neutral', 'happy', 'curious', 'sleepy', 'surprised']
const STORAGE_KEY = 'xiaowen_bot_pos'
const BUBBLE_TEXTS = [
  '你好呀~',
  '我是小文AI',
  '有什么可以帮你？',
  '聆听你的指令',
  '随时待命哦',
]
const DEFAULT_W = 140
const DEFAULT_H = 180
const EDGE_NEAR_PX = 46
const EDGE_PEEK_AFTER_MS = 5000
const SPEAK_MS = 3000
const CLICK_DRAG_THRESHOLD = 8

function clampPos(x, y, vw, vh, w, h) {
  const pad = 8
  return {
    x: Math.min(Math.max(pad, x), Math.max(pad, vw - w - pad)),
    y: Math.min(Math.max(pad, y), Math.max(pad, vh - h - pad)),
  }
}

function SpaceRobotSvg({ uid, blink, pupil, inertiaSpin, dizzy, dragging, peekSide }) {
  const id = (name) => `xw-bot-${name}-${uid}`

  const renderEye = (cx, cy) => (
    <g key={cx} transform={`translate(${cx + pupil.ox}, ${cy + pupil.oy})`} className="xiaowen-bot__eye-mount">
      {inertiaSpin || dizzy ? (
        <g className="xiaowen-bot__pupil-orbit">
          <circle r="14" fill="#bfdbfe" stroke="#7dd3fc" strokeWidth="0.8" />
          <circle r="5" cx="3" cy="-1" fill="#1e3a5f" className="xiaowen-bot__pupil-dazed" />
        </g>
      ) : (
        <g className="xiaowen-bot__eye-inner">
          <circle r="14" fill={`url(#${id('eye')})`} />
          <ellipse cx="0" cy="3" rx="6.5" ry="7.5" fill="#1d4ed8" opacity="0.3" />
          <circle r="9.5" fill="none" stroke="rgba(96,165,250,0.25)" strokeWidth="1" />
          <ellipse cx="-6" cy="-5.5" rx="5" ry="4.2" fill="#ffffff" opacity="0.98" />
          <circle r="2.4" cx="5.5" cy="-2.2" fill="#ffffff" opacity="0.85" />
          <circle r="1.6" cx="-2.2" cy="6" fill="#ffffff" opacity="0.6" />
          <circle r="1" cx="7.5" cy="4.2" fill="#ffffff" opacity="0.45" />
        </g>
      )}
    </g>
  )

  return (
    <svg className="xiaowen-bot__svg" viewBox="0 0 140 180" fill="none" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <radialGradient id={id('body')} cx="46%" cy="32%" r="70%">
          <stop offset="0%" stopColor="#ffffff" />
          <stop offset="40%" stopColor="#f8fafc" />
          <stop offset="75%" stopColor="#e2e8f0" />
          <stop offset="95%" stopColor="#c8d2e0" />
        </radialGradient>
        <radialGradient id={id('face')} cx="50%" cy="38%" r="60%">
          <stop offset="0%" stopColor="#ffffff" />
          <stop offset="55%" stopColor="#fdfdfd" />
          <stop offset="100%" stopColor="#f4f6fa" />
        </radialGradient>
        <linearGradient id={id('limb')} x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" stopColor="#bae6fd" />
          <stop offset="35%" stopColor="#7dd3fc" />
          <stop offset="70%" stopColor="#38bdf8" />
          <stop offset="100%" stopColor="#0ea5e9" />
        </linearGradient>
        <linearGradient id={id('panel')} x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" stopColor="#ede9fe" />
          <stop offset="30%" stopColor="#c4b5fd" />
          <stop offset="65%" stopColor="#a78bfa" />
          <stop offset="100%" stopColor="#8b5cf6" />
        </linearGradient>
        <linearGradient id={id('eye')} x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" stopColor="#1e40af" />
          <stop offset="30%" stopColor="#2563eb" />
          <stop offset="62%" stopColor="#3b82f6" />
          <stop offset="100%" stopColor="#60a5fa" />
        </linearGradient>
        <radialGradient id={id('core')} cx="50%" cy="50%" r="50%">
          <stop offset="0%" stopColor="#ffffff" />
          <stop offset="25%" stopColor="#cffafe" />
          <stop offset="55%" stopColor="#22d3ee" />
          <stop offset="100%" stopColor="#0891b2" />
        </radialGradient>
        <filter id={id('glow')} x="-100%" y="-100%" width="300%" height="300%">
          <feGaussianBlur stdDeviation="3.5" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
        <filter id={id('bloom')} x="-120%" y="-120%" width="340%" height="340%">
          <feGaussianBlur stdDeviation="6" result="b" />
          <feMerge>
            <feMergeNode in="b" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
        <filter id={id('soft')} x="-60%" y="-60%" width="220%" height="220%">
          <feGaussianBlur stdDeviation="2.2" result="b" />
          <feMerge>
            <feMergeNode in="b" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>

      {/* 地面柔影 */}
      <ellipse cx="70" cy="172" rx="46" ry="9" fill="rgba(139,92,246,0.08)" />

      {/* 星环 · 后层 */}
      <g className="xiaowen-bot__rings xiaowen-bot__rings--back" transform="translate(70 108)">
        <ellipse rx="70" ry="20" fill="none" stroke="rgba(34,211,238,0.1)" strokeWidth="2.4" transform="rotate(-26)" />
        <ellipse rx="58" ry="14" fill="none" stroke="rgba(167,139,250,0.15)" strokeWidth="1.8" transform="rotate(-14)" />
      </g>

      {/* 主体 · 圆滚滚蛋形 */}
      <g className="xiaowen-bot__body">
        <path
          d="M22 50 C22 8 40 4 70 4 C100 4 118 8 118 50 C118 102 110 138 70 138 C30 138 22 102 22 50 Z"
          fill={`url(#${id('body')})`}
          stroke="rgba(148,163,184,0.28)"
          strokeWidth="0.9"
        />
        <ellipse cx="42" cy="34" rx="16" ry="21" fill="rgba(255,255,255,0.5)" opacity="0.6" />
        <path d="M26 106 C26 134 50 138 70 138 C90 138 114 134 114 106 C114 118 102 128 70 128 C38 128 26 118 26 106 Z" fill="rgba(99,102,241,0.07)" />
      </g>

      {/* 四肢 · 更短更粗（放在主体前面、星环前层前面） */}
      <g className="xiaowen-bot__circuit">
        <g className="xiaowen-bot__limb--arm-l">
          <ellipse cx="20" cy="101" rx="10" ry="13" fill={`url(#${id('limb')})`} stroke="#0ea5e9" strokeWidth="0.7" opacity="0.95" />
          <ellipse cx="19" cy="107" rx="8.5" ry="4.5" fill="none" stroke="#67e8f9" strokeWidth="1.8" filter={`url(#${id('glow')})`} />
        </g>
        <g className="xiaowen-bot__limb--arm-r">
          <ellipse cx="120" cy="101" rx="10" ry="13" fill={`url(#${id('limb')})`} stroke="#0ea5e9" strokeWidth="0.7" opacity="0.95" />
          <ellipse cx="121" cy="107" rx="8.5" ry="4.5" fill="none" stroke="#67e8f9" strokeWidth="1.8" filter={`url(#${id('glow')})`} />
        </g>
        <g className="xiaowen-bot__limb--leg-l">
          <ellipse cx="50" cy="136" rx="13.5" ry="12" fill={`url(#${id('limb')})`} stroke="#0ea5e9" strokeWidth="0.8" />
          <ellipse cx="50" cy="142" rx="11.5" ry="5" fill="#bae6fd" opacity="0.5" />
        </g>
        <g className="xiaowen-bot__limb--leg-r">
          <ellipse cx="90" cy="136" rx="13.5" ry="12" fill={`url(#${id('limb')})`} stroke="#0ea5e9" strokeWidth="0.8" />
          <ellipse cx="90" cy="142" rx="11.5" ry="5" fill="#bae6fd" opacity="0.5" />
        </g>
      </g>

      {/* 两侧科技面板 */}
      <g className="xiaowen-bot__panel">
        <rect x="24" y="80" width="11" height="34" rx="5.5" fill={`url(#${id('panel')})`} stroke="rgba(139,92,246,0.4)" strokeWidth="0.8" opacity="0.8" />
        <line x1="27" y1="88" x2="32" y2="88" stroke="#67e8f9" strokeWidth="1.3" strokeLinecap="round" opacity="0.6" filter={`url(#${id('glow')})`} />
        <line x1="27" y1="106" x2="32" y2="106" stroke="#67e8f9" strokeWidth="1.3" strokeLinecap="round" opacity="0.6" filter={`url(#${id('glow')})`} />

        <rect x="105" y="80" width="11" height="34" rx="5.5" fill={`url(#${id('panel')})`} stroke="rgba(139,92,246,0.4)" strokeWidth="0.8" opacity="0.8" />
        <line x1="108" y1="88" x2="113" y2="88" stroke="#67e8f9" strokeWidth="1.3" strokeLinecap="round" opacity="0.6" filter={`url(#${id('glow')})`} />
        <line x1="108" y1="106" x2="113" y2="106" stroke="#67e8f9" strokeWidth="1.3" strokeLinecap="round" opacity="0.6" filter={`url(#${id('glow')})`} />
      </g>

      {/* 能量核心 */}
      <g className="xiaowen-bot__core">
        <circle cx="70" cy="116" r="24" fill="rgba(34,211,238,0.07)" filter={`url(#${id('bloom')})`} className="xiaowen-bot__pulse" />
        <circle cx="70" cy="116" r="19" fill="rgba(221,214,254,0.35)" stroke="rgba(167,139,250,0.5)" strokeWidth="2.2" />
        <circle cx="70" cy="116" r="13.5" fill="none" stroke="#22d3ee" strokeWidth="2.8" filter={`url(#${id('glow')})`} />
        <circle cx="70" cy="116" r="9.5" fill={`url(#${id('core')})`} />
        <circle cx="70" cy="116" r="4" fill="#ffffff" opacity="0.95" filter={`url(#${id('soft')})`} />
      </g>

      {/* 星环 · 前层 */}
      <g className="xiaowen-bot__rings xiaowen-bot__rings--front" transform="translate(70 108)">
        <ellipse
          rx="71" ry="21" fill="none"
          stroke="#22d3ee" strokeWidth="2.8"
          strokeDasharray="11 10"
          transform="rotate(-30)"
          className="xiaowen-bot__ring-dash"
          filter={`url(#${id('glow')})`}
          opacity="0.82"
        />
        <ellipse rx="57" ry="15" fill="none" stroke="rgba(167,139,250,0.6)" strokeWidth="1.6" transform="rotate(-10)" />
        <ellipse rx="48" ry="11" fill="none" stroke="rgba(103,232,249,0.45)" strokeWidth="1.1" transform="rotate(-4)" />
      </g>

      {/* 耳罩 · 更立体 */}
      <g className="xiaowen-bot__ear">
        <ellipse cx="13" cy="54" rx="13" ry="15" fill={`url(#${id('panel')})`} stroke="rgba(139,92,246,0.55)" strokeWidth="1.3" opacity="0.97" />
        <ellipse cx="14" cy="56" rx="10.5" ry="12.5" fill="rgba(88,50,200,0.14)" />
        <ellipse cx="13" cy="54" rx="7.5" ry="8.5" fill="none" stroke="#22d3ee" strokeWidth="2.4" filter={`url(#${id('glow')})`} />
        <ellipse cx="10" cy="48" rx="4" ry="2.2" fill="rgba(255,255,255,0.35)" />
        <circle cx="13" cy="54" r="2.2" fill="#67e8f9" opacity="0.9" />

        <ellipse cx="127" cy="54" rx="13" ry="15" fill={`url(#${id('panel')})`} stroke="rgba(139,92,246,0.55)" strokeWidth="1.3" opacity="0.97" />
        <ellipse cx="126" cy="56" rx="10.5" ry="12.5" fill="rgba(88,50,200,0.14)" />
        <ellipse cx="127" cy="54" rx="7.5" ry="8.5" fill="none" stroke="#22d3ee" strokeWidth="2.4" filter={`url(#${id('glow')})`} />
        <ellipse cx="130" cy="48" rx="4" ry="2.2" fill="rgba(255,255,255,0.35)" />
        <circle cx="127" cy="54" r="2.2" fill="#67e8f9" opacity="0.9" />
      </g>

      {/* 面罩 · 更厚更亮 */}
      <g className="xiaowen-bot__helmet">
        <ellipse cx="70" cy="56" rx="48" ry="46" fill="none" stroke="rgba(34,211,238,0.2)" strokeWidth="7" filter={`url(#${id('bloom')})`} />
        <ellipse cx="70" cy="56" rx="47" ry="45" fill={`url(#${id('face')})`} stroke={`url(#${id('panel')})`} strokeWidth="3.2" />
        <ellipse cx="70" cy="56" rx="44.5" ry="42.5" fill="none" stroke="rgba(103,232,249,0.4)" strokeWidth="1.6" filter={`url(#${id('glow')})`} />
        <ellipse cx="70" cy="48" rx="40" ry="29" fill="rgba(224,231,255,0.28)" />
      </g>

      {/* 眼睛 */}
      <ellipse cx="42" cy="56" rx="15" ry={blink ? 1.4 : 15} fill="#e0f2fe" className="xiaowen-bot__eyelid" />
      {!blink && renderEye(42, 56)}
      <ellipse cx="98" cy="56" rx="15" ry={blink ? 1.4 : 15} fill="#e0f2fe" className="xiaowen-bot__eyelid" />
      {!blink && renderEye(98, 56)}

      {/* 腮红 */}
      <ellipse cx="26" cy="64" rx="7.5" ry="4.5" fill="#FB9288" opacity="0.25" />
      <ellipse cx="114" cy="64" rx="7.5" ry="4.5" fill="#FB9288" opacity="0.25" />

      {/* 嘴巴（已修复为微笑线） */}
      <path className="xiaowen-bot__mouth xiaowen-bot__mouth--neutral" d="M52 74 Q70 82 88 74" stroke="#92400E" strokeWidth="1.9" strokeLinecap="round" fill="none" />
      <path className="xiaowen-bot__mouth xiaowen-bot__mouth--happy" d="M50 72 Q70 90 90 72" stroke="#92400E" strokeWidth="2.1" strokeLinecap="round" fill="none" />
      <path className="xiaowen-bot__mouth xiaowen-bot__mouth--curious" d="M60 76 Q70 80 80 76" stroke="#92400E" strokeWidth="1.7" strokeLinecap="round" fill="none" />
      <line className="xiaowen-bot__mouth xiaowen-bot__mouth--sleepy" x1="56" y1="78" x2="84" y2="78" stroke="#92400E" strokeWidth="1.7" strokeLinecap="round" />
      <ellipse className="xiaowen-bot__mouth xiaowen-bot__mouth--surprised" cx="70" cy="76" rx="5" ry="6.5" stroke="#92400E" strokeWidth="1.7" fill="none" />
      <path className="xiaowen-bot__mouth xiaowen-bot__mouth--grabbed" d="M56 78 Q70 70 84 78" stroke="#92400E" strokeWidth="1.7" strokeLinecap="round" fill="none" />
      <ellipse className="xiaowen-bot__mouth xiaowen-bot__mouth--peek" cx="70" cy="77" rx="4" ry="3" stroke="#92400E" strokeWidth="1.6" fill="none" />

      {/* 天线（已修复位置） */}
      <g className="xiaowen-bot__antenna-group">
        <path d="M56 30 Q50 12 60 2 Q64 -2 72 0" stroke={`url(#${id('limb')})`} strokeWidth="3" strokeLinecap="round" fill="none" />
        <circle cx="72" cy="0" r="6.5" fill="#7dd3fc" stroke="#38bdf8" strokeWidth="1.4" className="xiaowen-bot__antenna-tip" />
        <circle cx="70" cy="-2" r="3.2" fill="rgba(255,255,255,0.7)" />
      </g>

      {/* 眉毛 */}
      {(dragging || peekSide !== 'none') && (
        <>
          <path className="xiaowen-bot__brow xiaowen-bot__brow--l" d="M28 38 Q42 32 52 38" stroke="#64748b" strokeWidth="2.1" strokeLinecap="round" fill="none" />
          <path className="xiaowen-bot__brow xiaowen-bot__brow--r" d="M88 38 Q100 32 112 38" stroke="#64748b" strokeWidth="2.1" strokeLinecap="round" fill="none" />
        </>
      )}
    </svg>
  )
}

export default function XiaowenBot() {
  const uid = useId().replace(/:/g, '')

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
  const speakTimerRef = useRef(null)
  const didDragMoveRef = useRef(false)

  const [pos, setPos] = useState({ x: 24, y: 24 })
  const [dragging, setDragging] = useState(false)
  const [dragPull, setDragPull] = useState({ dx: 0, dy: 0 })
  const [inertiaSpin, setInertiaSpin] = useState(false)
  const [dizzy, setDizzy] = useState(false)
  const [peekSide, setPeekSide] = useState('none')
  const [isFalling, setIsFalling] = useState(false)
  const [pupil, setPupil] = useState({ ox: 0, oy: 0 })
  const [mood, setMood] = useState('neutral')
  const [blink, setBlink] = useState(false)
  const [isSpeaking, setIsSpeaking] = useState(false)
  const [bubbleText, setBubbleText] = useState(BUBBLE_TEXTS[0])
  const [showBubble, setShowBubble] = useState(false)

  const clearSpeakTimer = useCallback(() => {
    if (speakTimerRef.current != null) {
      window.clearTimeout(speakTimerRef.current)
      speakTimerRef.current = null
    }
  }, [])

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
          queueMicrotask(() => setPos(c))
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
    queueMicrotask(() => setPos(initial))
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
          stopInertia()
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
    const faceCy = r.top + r.height * 0.32
    const dx = clientX - faceCx
    const dy = clientY - faceCy
    const len = Math.hypot(dx, dy) || 1
    const damp = Math.min(len / 120, 1)
    setPupil({
      ox: (dx / len) * 4 * damp,
      oy: (dy / len) * 3.2 * damp,
    })
  }, [])

  useEffect(() => {
    const onMove = (e) => updatePupil(e.clientX, e.clientY)
    window.addEventListener('mousemove', onMove, { passive: true })
    return () => window.removeEventListener('mousemove', onMove)
  }, [updatePupil])

  useEffect(() => {
    const pick = () => {
      setMood(MOODS[Math.floor(Math.random() * MOODS.length)])
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
      clearSpeakTimer()
      cancelFallAnimation()
      if (peekIdleTimerRef.current != null) {
        window.clearTimeout(peekIdleTimerRef.current)
        peekIdleTimerRef.current = null
      }
    },
    [clearDizzyTimer, clearSpeakTimer, cancelFallAnimation],
  )

  useEffect(() => {
    if (peekIdleTimerRef.current != null) {
      window.clearTimeout(peekIdleTimerRef.current)
      peekIdleTimerRef.current = null
    }

    if (dragging || inertiaSpin || dizzy || isFalling) {
      queueMicrotask(() => setPeekSide('none'))
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
      queueMicrotask(() => setPeekSide('none'))
      return undefined
    }

    queueMicrotask(() => setPeekSide('none'))

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

  const handleClick = useCallback(() => {
    if (didDragMoveRef.current) return
    clearSpeakTimer()
    setBubbleText(BUBBLE_TEXTS[Math.floor(Math.random() * BUBBLE_TEXTS.length)])
    setShowBubble(true)
    setIsSpeaking(true)
    speakTimerRef.current = window.setTimeout(() => {
      setIsSpeaking(false)
      setShowBubble(false)
      speakTimerRef.current = null
    }, SPEAK_MS)
  }, [clearSpeakTimer])

  const onPointerDown = useCallback(
    (e) => {
      if (e.button !== 0) return
      stopInertia()
      cancelFallAnimation()
      clearDizzyTimer()
      setDizzy(false)
      setPeekSide('none')
      setDragPull({ dx: 0, dy: 0 })
      didDragMoveRef.current = false
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
      const dx = e.clientX - d.startX
      const dy = e.clientY - d.startY
      if (Math.hypot(dx, dy) > CLICK_DRAG_THRESHOLD) {
        didDragMoveRef.current = true
      }
      const nx = d.origX + dx
      const ny = d.origY + dy
      const now = performance.now()
      d.samples.push({ t: now, x: e.clientX, y: e.clientY })
      if (d.samples.length > 8) d.samples.shift()
      const next = applyClamp(nx, ny)
      posRef.current = next
      setPos(next)
      setDragPull({
        dx: Math.max(-42, Math.min(42, dx)),
        dy: Math.max(-42, Math.min(42, dy)),
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

  const stateClass = [
    'xiaowen-bot',
    dragging && 'xiaowen-bot--dragging',
    inertiaSpin && 'xiaowen-bot--inertia',
    dizzy && 'xiaowen-bot--dizzy',
    peekSide === 'left' && 'xiaowen-bot--peek-left',
    peekSide === 'right' && 'xiaowen-bot--peek-right',
    isSpeaking && 'xiaowen-bot--speaking',
  ].filter(Boolean).join(' ')

  const cardClass = [
    'xiaowen-bot__card',
    `xiaowen-bot__card--${mood}`,
    dragging && 'xiaowen-bot__card--grabbed',
    peekSide !== 'none' && 'xiaowen-bot__card--peek',
    isSpeaking && 'xiaowen-bot__card--speaking',
  ].filter(Boolean).join(' ')

  return (
    <div
      className={stateClass}
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
      {showBubble && (
        <div className="xiaowen-bot__bubble" role="status">
          {bubbleText}
          <span className="xiaowen-bot__bubble-tip" />
        </div>
      )}

      {isSpeaking && (
        <div className="xiaowen-bot__voice-wave" aria-hidden="true">
          {[0, 1, 2, 3, 4, 5, 6].map((i) => (
            <span key={i} />
          ))}
        </div>
      )}

      <div
        ref={cardRef}
        className={cardClass}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={endDrag}
        onPointerCancel={endDrag}
        onLostPointerCapture={endDrag}
        onClick={handleClick}
        title="拖拽移动 | 点击唤醒语音 | 靠边会探头"
      >
        <span className="xiaowen-bot__badge">AI</span>
        <div className="xiaowen-bot__figure">
          <SpaceRobotSvg
            uid={uid}
            blink={blink}
            pupil={pupil}
            inertiaSpin={inertiaSpin}
            dizzy={dizzy}
            dragging={dragging}
            peekSide={peekSide}
          />
        </div>
      </div>
    </div>
  )
}

import { useEffect, useRef } from 'react'
import * as THREE from 'three'
import './LoginParticleBg.css'

// ── 配色方案 ─────────────────────────────────────────────
const COLOR_PALETTE = [
  { color: '#4A90D9', weight: 0.35 }, // 蓝色 35%
  { color: '#7C5CFC', weight: 0.25 }, // 紫色 25%
  { color: '#00D4AA', weight: 0.2 }, // 青绿 20%
  { color: '#FFFFFF', weight: 0.2 }, // 白色星光 20%
]

// ── 按权重随机选色 ──────────────────────────────────────
function pickColor() {
  const rand = Math.random()
  let cumulative = 0
  for (const entry of COLOR_PALETTE) {
    cumulative += entry.weight
    if (rand <= cumulative) return entry.color
  }
  return COLOR_PALETTE[0].color
}

// ── 生成球形渐变纹理 ─────────────────────────────────────
function createGlowTexture() {
  const size = 64
  const canvas = document.createElement('canvas')
  canvas.width = size
  canvas.height = size
  const ctx = canvas.getContext('2d')

  const gradient = ctx.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size / 2)
  gradient.addColorStop(0, 'rgba(255, 255, 255, 1)')
  gradient.addColorStop(0.1, 'rgba(255, 255, 255, 0.9)')
  gradient.addColorStop(0.4, 'rgba(255, 255, 255, 0.4)')
  gradient.addColorStop(0.7, 'rgba(255, 255, 255, 0.05)')
  gradient.addColorStop(1, 'rgba(255, 255, 255, 0)')

  ctx.fillStyle = gradient
  ctx.fillRect(0, 0, size, size)

  return new THREE.CanvasTexture(canvas)
}

// ── 是否为移动端 ──────────────────────────────────────────
function isMobile() {
  return /Mobi|Android/i.test(navigator.userAgent)
}

export default function LoginParticleBg({ className = '', ambient = false }) {
  const containerRef = useRef(null)
  const animFrameRef = useRef(null)
  const mouseRef = useRef({ x: 0, y: 0 })
  const targetRef = useRef({ x: 0, y: 0 })
  const currentRef = useRef({ x: 0, y: 0 })
  const ambientRef = useRef(ambient)
  ambientRef.current = ambient

  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    // ── 粒子数量 ────────────────────────────────
    const particleCount = isMobile() ? 200 : ambientRef.current ? 350 : 800

    // ── 场景 / 相机 / 渲染器 ───────────────────
    const scene = new THREE.Scene()

    const camera = new THREE.PerspectiveCamera(
      75,
      window.innerWidth / window.innerHeight,
      0.1,
      1000,
    )
    camera.position.z = 3

    const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true })
    renderer.setSize(window.innerWidth, window.innerHeight)
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    renderer.setClearColor(0x000000, 0)

    const canvas = renderer.domElement
    canvas.style.position = 'absolute'
    canvas.style.inset = '0'
    canvas.style.zIndex = '0'
    canvas.style.pointerEvents = 'none'
    container.appendChild(canvas)

    // ── 粒子几何体 ──────────────────────────────
    const geometry = new THREE.BufferGeometry()
    const positions = new Float32Array(particleCount * 3)
    const colors = new Float32Array(particleCount * 3)
    const sizes = new Float32Array(particleCount)

    for (let i = 0; i < particleCount; i++) {
      const theta = Math.random() * Math.PI * 2
      const phi = Math.acos(2 * Math.random() - 1)
      const radius = 2.5 + Math.random() * 1.0

      positions[i * 3] = radius * Math.sin(phi) * Math.cos(theta)
      positions[i * 3 + 1] = radius * Math.sin(phi) * Math.sin(theta)
      positions[i * 3 + 2] = radius * Math.cos(phi)

      const hexColor = pickColor()
      const color = new THREE.Color(hexColor)
      colors[i * 3] = color.r
      colors[i * 3 + 1] = color.g
      colors[i * 3 + 2] = color.b

      const isWhite = hexColor === '#FFFFFF'
      sizes[i] = isWhite
        ? 0.02 + Math.random() * 0.01
        : 0.008 + Math.random() * 0.007
    }

    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3))
    geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3))
    geometry.setAttribute('size', new THREE.BufferAttribute(sizes, 1))

    // ── 材质 ───────────────────────────────────
    const glowTexture = createGlowTexture()
    const material = new THREE.PointsMaterial({
      size: 0.015,
      map: glowTexture,
      blending: THREE.AdditiveBlending,
      vertexColors: true,
      depthWrite: false,
      transparent: true,
    })

    const particleSystem = new THREE.Points(geometry, material)
    scene.add(particleSystem)

    // ── 鼠标事件 ────────────────────────────────
    const handleMouseMove = (e) => {
      mouseRef.current.x = (e.clientX / window.innerWidth) * 2 - 1
      mouseRef.current.y = -(e.clientY / window.innerHeight) * 2 + 1
    }

    const handleTouchMove = (e) => {
      if (e.touches.length > 0) {
        mouseRef.current.x = (e.touches[0].clientX / window.innerWidth) * 2 - 1
        mouseRef.current.y = -(e.touches[0].clientY / window.innerHeight) * 2 + 1
      }
    }

    window.addEventListener('mousemove', handleMouseMove)
    window.addEventListener('touchmove', handleTouchMove, { passive: true })

    // ── resize ──────────────────────────────────
    const handleResize = () => {
      camera.aspect = window.innerWidth / window.innerHeight
      camera.updateProjectionMatrix()
      renderer.setSize(window.innerWidth, window.innerHeight)
      renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    }
    window.addEventListener('resize', handleResize)

    // ── 动画循环 ────────────────────────────────
    const animate = () => {
      animFrameRef.current = requestAnimationFrame(animate)

      // 粒子自转
      particleSystem.rotation.x += ambientRef.current ? 0.00015 : 0.0003
      particleSystem.rotation.y += ambientRef.current ? 0.00025 : 0.0005

      // 鼠标视差：lerp 平滑插值
      targetRef.current.x = mouseRef.current.x * 0.3
      targetRef.current.y = mouseRef.current.y * 0.3

      currentRef.current.x += (targetRef.current.x - currentRef.current.x) * 0.05
      currentRef.current.y += (targetRef.current.y - currentRef.current.y) * 0.05

      particleSystem.position.x = currentRef.current.x
      particleSystem.position.y = currentRef.current.y

      renderer.render(scene, camera)
    }
    animate()

    // ── 清理 ────────────────────────────────────
    return () => {
      if (animFrameRef.current) {
        cancelAnimationFrame(animFrameRef.current)
      }
      window.removeEventListener('mousemove', handleMouseMove)
      window.removeEventListener('touchmove', handleTouchMove)
      window.removeEventListener('resize', handleResize)
      geometry.dispose()
      material.dispose()
      glowTexture.dispose()
      renderer.dispose()
      if (container.contains(canvas)) {
        container.removeChild(canvas)
      }
    }
  }, [])

  return <div ref={containerRef} className={`login-particle-bg ${className}`.trim()} />
}

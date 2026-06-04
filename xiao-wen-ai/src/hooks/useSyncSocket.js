/**
 * 多端日志同步 WebSocket：连接 /ws/sync，断线自动重连。
 */
import { useCallback, useEffect, useRef, useState } from 'react'
import { wsUrl } from '../wsBase'

const CLIENT_ID =
  typeof crypto !== 'undefined' && crypto.randomUUID ? crypto.randomUUID() : `client-${Date.now()}`

export default function useSyncSocket({ onMessage, enabled = true }) {
  const wsRef = useRef(null)
  const reconnectTimerRef = useRef(null)
  const onMessageRef = useRef(onMessage)
  const [connected, setConnected] = useState(false)

  onMessageRef.current = onMessage

  const send = useCallback((type, payload) => {
    const ws = wsRef.current
    if (ws?.readyState !== WebSocket.OPEN) return
    ws.send(JSON.stringify({ type, payload, from: CLIENT_ID }))
  }, [])

  useEffect(() => {
    if (!enabled) return undefined

    let cancelled = false

    function connect() {
      if (cancelled) return
      const ws = new WebSocket(wsUrl())
      wsRef.current = ws

      ws.onopen = () => {
        if (!cancelled) setConnected(true)
      }

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data)
          if (msg.from === CLIENT_ID) return
          onMessageRef.current?.(msg)
        } catch {
          /* ignore malformed frame */
        }
      }

      ws.onclose = () => {
        setConnected(false)
        if (!cancelled) {
          reconnectTimerRef.current = window.setTimeout(connect, 2000)
        }
      }

      ws.onerror = () => {
        ws.close()
      }
    }

    connect()

    return () => {
      cancelled = true
      clearTimeout(reconnectTimerRef.current)
      const ws = wsRef.current
      if (ws) {
        ws.onclose = null
        ws.onerror = null
        ws.close()
      }
      wsRef.current = null
      setConnected(false)
    }
  }, [enabled])

  return { send, connected, clientId: CLIENT_ID }
}

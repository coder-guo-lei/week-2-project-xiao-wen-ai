/**
 * 麦克风 → 16kHz WAV → POST 后端 /api/speech-to-text（讯飞听写）
 * 优先使用 AudioWorklet（无 ScriptProcessor 弃用警告）；不支持时再回退 ScriptProcessor。
 */

import captureWorkletUrl from './xfyunCapture.worklet.js?url'
import { API_BASE } from '../apiBase.js'

const API_PREFIX = String(API_BASE || '').replace(/\/$/, '')

export function downsampleBuffer(buffer, inputRate, outputRate = 16000) {
  if (inputRate === outputRate) return buffer
  const ratio = inputRate / outputRate
  const newLength = Math.round(buffer.length / ratio)
  const result = new Float32Array(newLength)
  let offsetBuffer = 0
  for (let i = 0; i < newLength; i++) {
    const nextOffsetBuffer = Math.round((i + 1) * ratio)
    let accum = 0
    let count = 0
    for (let j = offsetBuffer; j < nextOffsetBuffer && j < buffer.length; j++) {
      accum += buffer[j]
      count++
    }
    result[i] = count ? accum / count : 0
    offsetBuffer = nextOffsetBuffer
  }
  return result
}

function floatToWavBlob(float32, sampleRate) {
  const buffer = new ArrayBuffer(44 + float32.length * 2)
  const view = new DataView(buffer)
  const writeStr = (off, str) => {
    for (let i = 0; i < str.length; i++) view.setUint8(off + i, str.charCodeAt(i))
  }
  writeStr(0, 'RIFF')
  view.setUint32(4, 36 + float32.length * 2, true)
  writeStr(8, 'WAVE')
  writeStr(12, 'fmt ')
  view.setUint32(16, 16, true)
  view.setUint16(20, 1, true)
  view.setUint16(22, 1, true)
  view.setUint32(24, sampleRate, true)
  view.setUint32(28, sampleRate * 2, true)
  view.setUint16(32, 2, true)
  view.setUint16(34, 16, true)
  writeStr(36, 'data')
  view.setUint32(40, float32.length * 2, true)
  let offset = 44
  for (let i = 0; i < float32.length; i++) {
    const s = Math.max(-1, Math.min(1, float32[i]))
    view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7fff, true)
    offset += 2
  }
  return new Blob([buffer], { type: 'audio/wav' })
}

/**
 * @param {{ signal?: AbortSignal; silenceMs?: number; maxMs?: number; noVoiceCutMs?: number }} opts — noVoiceCutMs 默认 15s 无有效人声则结束
 * @returns {Promise<string>} 识别文本，失败或取消为空字符串
 */
export async function recordAndTranscribeXfyun(opts = {}) {
  const {
    signal,
    silenceMs = 2800,
    maxMs = 55000,
    /** 从未检测到说话（一直近似静音）超过此时长则结束录音 */
    noVoiceCutMs = 15000,
  } = opts

  const stream = await navigator.mediaDevices.getUserMedia({
    audio: {
      echoCancellation: true,
      noiseSuppression: true,
      autoGainControl: true,
    },
  })

  const ctx = new AudioContext()
  const inputRate = ctx.sampleRate
  const source = ctx.createMediaStreamSource(stream)
  const mute = ctx.createGain()
  mute.gain.value = 0

  const chunks = []
  let hadVoice = false
  let silentAccumMs = 0
  let noVoiceAccumMs = 0
  /** 每块时长随缓冲长度变化（Worklet 多为 128 样点/块） */
  let chunkMs = (128 / inputRate) * 1000
  const t0 = typeof performance !== 'undefined' ? performance.now() : Date.now()

  let proc = null
  let workletNode = null
  let useWorklet = false

  try {
    await ctx.audioWorklet.addModule(captureWorkletUrl)
    workletNode = new AudioWorkletNode(ctx, 'xfyun-capture', {
      numberOfInputs: 1,
      numberOfOutputs: 1,
      channelCount: 1,
      channelCountMode: 'explicit',
    })
    useWorklet = true
  } catch {
    const LegacyScript = ctx.createScriptProcessor(4096, 1, 1)
    proc = LegacyScript
    chunkMs = (4096 / inputRate) * 1000
  }

  const stopHardware = async () => {
    try {
      workletNode?.disconnect()
    } catch { /* ignore */ }
    try {
      proc?.disconnect()
    } catch { /* ignore */ }
    try {
      source.disconnect()
    } catch { /* ignore */ }
    try {
      mute.disconnect()
    } catch { /* ignore */ }
    stream.getTracks().forEach((t) => t.stop())
    try {
      await ctx.close()
    } catch { /* ignore */ }
  }

  const FETCH_TIMEOUT_MS = 45000

  return new Promise((resolve, reject) => {
    let finishing = false
    let settled = false
    const resolveOnce = (v) => {
      if (settled) return
      settled = true
      resolve(v)
    }
    const rejectOnce = (e) => {
      if (settled) return
      settled = true
      reject(e)
    }

    const onAudioBuffer = (input) => {
      if (finishing) return
      if (!input || !input.length) return
      chunkMs = (input.length / inputRate) * 1000

      if (signal?.aborted) {
        void finish('abort')
        return
      }

      chunks.push(new Float32Array(input))
      let sum = 0
      for (let i = 0; i < input.length; i++) sum += input[i] * input[i]
      const rms = Math.sqrt(sum / input.length)
      if (rms > 0.02) hadVoice = true
      if (!hadVoice) {
        noVoiceAccumMs += chunkMs
        if (noVoiceAccumMs >= noVoiceCutMs) {
          void finish('novoice')
          return
        }
      }
      if (hadVoice) {
        silentAccumMs = rms < 0.008 ? silentAccumMs + chunkMs : 0
        if (silentAccumMs >= silenceMs) {
          void finish('silence')
        }
      }
      const elapsed =
        (typeof performance !== 'undefined' ? performance.now() : Date.now()) - t0
      if (elapsed >= maxMs) void finish('max')
    }

    const finish = async (reason) => {
      if (finishing) return
      finishing = true

      if (useWorklet && workletNode) {
        workletNode.port.onmessage = null
      }
      if (proc) {
        proc.onaudioprocess = null
      }

      try {
        if (reason === 'abort' || signal?.aborted) {
          await stopHardware()
          resolveOnce('')
          return
        }

        let total = 0
        for (const c of chunks) total += c.length
        const merged = new Float32Array(total)
        let off = 0
        for (const c of chunks) {
          merged.set(c, off)
          off += c.length
        }

        await stopHardware()

        if (total === 0) {
          resolveOnce('')
          return
        }

        const pcm16k = downsampleBuffer(merged, inputRate, 16000)
        const wav = floatToWavBlob(pcm16k, 16000)
        const fd = new FormData()
        fd.append('audio', wav, 'speech.wav')

        const combined = new AbortController()
        const tid = setTimeout(() => combined.abort(), FETCH_TIMEOUT_MS)
        const onUserAbort = () => combined.abort()
        if (signal) {
          signal.addEventListener('abort', onUserAbort, { once: true })
        }

        try {
          const res = await fetch(`${API_PREFIX}/api/speech-to-text`, {
            method: 'POST',
            body: fd,
            signal: combined.signal,
          })
          const data = await res.json().catch(() => ({}))
          if (!res.ok) {
            const msg = (data && data.error) || `服务返回 ${res.status}`
            rejectOnce(new Error(msg))
            return
          }
          resolveOnce(String(data.text || '').trim())
        } catch (e) {
          const name = e && e.name
          if (name === 'AbortError') {
            resolveOnce('')
          } else {
            rejectOnce(e instanceof Error ? e : new Error(String(e)))
          }
        } finally {
          clearTimeout(tid)
          if (signal) signal.removeEventListener('abort', onUserAbort)
        }
      } catch (e) {
        rejectOnce(e instanceof Error ? e : new Error(String(e)))
      }
    }

    if (useWorklet && workletNode) {
      workletNode.port.onmessage = (e) => {
        const buf = e.data
        if (buf instanceof Float32Array) onAudioBuffer(buf)
      }
      source.connect(workletNode)
      workletNode.connect(mute)
      mute.connect(ctx.destination)
    } else if (proc) {
      proc.onaudioprocess = (e) => {
        onAudioBuffer(e.inputBuffer.getChannelData(0))
      }
      source.connect(proc)
      proc.connect(mute)
      mute.connect(ctx.destination)
    } else {
      void stopHardware()
      resolveOnce('')
      return
    }

    if (signal) {
      signal.addEventListener('abort', () => void finish('abort'), { once: true })
    }
  })
}

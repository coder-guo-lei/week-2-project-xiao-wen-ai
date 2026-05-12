/**
 * AudioWorklet：采集麦克风 Float32 单声道块（替代已弃用的 ScriptProcessor）
 */
class XfyunCaptureProcessor extends AudioWorkletProcessor {
  process(inputs) {
    const input = inputs[0]
    if (!input || !input[0]) return true
    const ch = input[0]
    const copy = new Float32Array(ch.length)
    copy.set(ch)
    this.port.postMessage(copy, [copy.buffer])
    return true
  }
}

registerProcessor('xfyun-capture', XfyunCaptureProcessor)

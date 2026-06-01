/**
 * 根据指令历史与对话记录，规则推断偏好推荐（轻量「行为画像」，非云端大数据）。
 */
import { normalizePreferences } from '../preferences'

const MIN_SAMPLES = 3

const DETAILED_CMD = /详细|展开|深入|介绍一下|讲讲|为什么|原理|全面|具体/
const PROFESSIONAL_CMD = /报告|分析|数据|图表|统计|专业|工作|项目|方案/
const FRIENDLY_CMD = /笑话|故事|聊天|随便|辛苦|谢谢|哈哈|有趣/
const MUSIC_CMD = /音乐|播放|放首|唱歌|歌曲/
const NICKNAME_PATTERNS = [
  /叫我([^\s，。！？,.]{1,8})/,
  /称呼我[为是]?([^\s，。！？,.]{1,8})/,
  /你可以叫我([^\s，。！？,.]{1,8})/,
]

const FIELD_LABELS = {
  replyStyle: '回复风格',
  assistantTone: '助手语气',
  userNickname: '称呼',
  ttsVoice: '朗读音色',
}

function textOf(item) {
  if (typeof item === 'string') return item
  if (item && typeof item.content === 'string') return item.content
  return ''
}

function scorePattern(text, regex) {
  return regex.test(text) ? 1 : 0
}

function inferNickname(userTexts) {
  const counts = new Map()
  for (const t of userTexts) {
    for (const re of NICKNAME_PATTERNS) {
      const m = t.match(re)
      if (m?.[1]) {
        const name = m[1].trim()
        if (name && name !== '小文' && name.length <= 8) {
          counts.set(name, (counts.get(name) || 0) + 1)
        }
      }
    }
  }
  let best = ''
  let max = 0
  for (const [name, c] of counts) {
    if (c > max) {
      max = c
      best = name
    }
  }
  return best
}

/**
 * @param {{ commandHistory?: string[], chatHistory?: {role:string,content:string}[] }} input
 * @returns {{ suggestions: object, reasons: {field:string,value:string,text:string}[], sampleSize: number, hasEnoughData: boolean }}
 */
export function recommendPreferences(input = {}) {
  const commands = (input.commandHistory || []).map((s) => String(s).trim()).filter(Boolean)
  const chats = Array.isArray(input.chatHistory) ? input.chatHistory : []
  const userTexts = chats.filter((m) => m.role === 'user').map(textOf)
  const assistantTexts = chats.filter((m) => m.role === 'assistant').map(textOf)
  const allUserText = [...commands, ...userTexts].join('\n')

  const sampleSize = commands.length + chats.length
  const hasEnoughData = sampleSize >= MIN_SAMPLES

  const suggestions = {}
  const reasons = []

  if (!hasEnoughData) {
    return { suggestions, reasons, sampleSize, hasEnoughData }
  }

  let detailedScore = 0
  let conciseScore = 0
  commands.forEach((c) => {
    detailedScore += scorePattern(c, DETAILED_CMD)
    if (c.length <= 12 && !DETAILED_CMD.test(c)) conciseScore += 1
  })
  userTexts.forEach((t) => { detailedScore += scorePattern(t, DETAILED_CMD) })

  const assistantLengths = assistantTexts.map((t) => t.length).filter((n) => n > 0)
  const avgAssistantLen = assistantLengths.length
    ? assistantLengths.reduce((a, b) => a + b, 0) / assistantLengths.length
    : 0

  if (detailedScore >= 2 || avgAssistantLen > 140) {
    suggestions.replyStyle = 'detailed'
    reasons.push({
      field: 'replyStyle',
      value: 'detailed',
      text: detailedScore >= 2
        ? `最近 ${detailedScore} 次输入包含「详细/展开/介绍」等表述`
        : `近期助手回复平均较长（约 ${Math.round(avgAssistantLen)} 字），更适合详细风格`,
    })
  } else if (commands.length >= 4 && detailedScore === 0 && avgAssistantLen < 90) {
    suggestions.replyStyle = 'concise'
    reasons.push({
      field: 'replyStyle',
      value: 'concise',
      text: '你常用短指令且很少要求长文，推荐保持简洁回复',
    })
  }

  let proScore = 0
  let friendlyScore = 0
  const scanTone = (t) => {
    proScore += scorePattern(t, PROFESSIONAL_CMD)
    friendlyScore += scorePattern(t, FRIENDLY_CMD)
  }
  commands.forEach(scanTone)
  userTexts.forEach(scanTone)

  if (proScore > friendlyScore && proScore >= 2) {
    suggestions.assistantTone = 'professional'
    reasons.push({
      field: 'assistantTone',
      value: 'professional',
      text: `历史指令中「分析/报告/数据」类表述较多（${proScore} 次）`,
    })
  } else if (friendlyScore >= 2) {
    suggestions.assistantTone = 'friendly'
    reasons.push({
      field: 'assistantTone',
      value: 'friendly',
      text: `你常进行闲聊、笑话、故事类互动（${friendlyScore} 次）`,
    })
  }

  const nick = inferNickname([...userTexts, ...commands])
  if (nick) {
    suggestions.userNickname = nick
    reasons.push({
      field: 'userNickname',
      value: nick,
      text: `从对话中识别到你希望被称为「${nick}」`,
    })
  }

  const musicHits = commands.filter((c) => MUSIC_CMD.test(c)).length
  if (musicHits >= 2) {
    suggestions.ttsVoice = 'female_jiuxu'
    reasons.push({
      field: 'ttsVoice',
      value: 'female_jiuxu',
      text: `你多次使用音乐相关指令（${musicHits} 次），可选另一女声朗读`,
    })
  }

  return { suggestions, reasons, sampleSize, hasEnoughData }
}

/** 与当前偏好对比，返回有差异且带说明的推荐项 */
export function getActionableRecommendations(currentPrefs, recoResult) {
  const current = normalizePreferences(currentPrefs)
  const { suggestions, reasons, hasEnoughData } = recoResult
  if (!hasEnoughData) return []

  const reasonMap = Object.fromEntries(reasons.map((r) => [r.field, r.text]))

  return Object.entries(suggestions)
    .filter(([field, value]) => current[field] !== value)
    .map(([field, value]) => ({
      field,
      value,
      label: FIELD_LABELS[field] || field,
      reason: reasonMap[field] || '根据历史行为推断',
    }))
}

export function recommendationFingerprint(items) {
  return JSON.stringify(items.map((i) => [i.field, i.value]).sort())
}

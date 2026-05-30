import { groupTurns, formatExportTimestamp, buildExportFilename } from './format.js'
import { downloadText } from './download.js'

export function buildMarkdown(history, { exportedAt = new Date() } = {}) {
  const turns = groupTurns(history)
  const lines = [
    '# 小文 AI 对话记录',
    '',
    `> 导出时间：${formatExportTimestamp(exportedAt)}  `,
    `> 对话轮次：${turns.length}  `,
    `> 消息条数：${normalizeCount(history)}`,
    '',
    '---',
    '',
  ]

  turns.forEach((turn, idx) => {
    lines.push(`## 第 ${idx + 1} 轮`, '')
    lines.push('### 用户', '', turn.user, '')
    lines.push('### 小文', '', turn.assistant || '（无回复）', '')
    lines.push('---', '')
  })

  return lines.join('\n').trimEnd() + '\n'
}

function normalizeCount(history) {
  if (!Array.isArray(history)) return 0
  return history.filter((m) => m?.content?.trim()).length
}

export async function exportChatMarkdown(history, options = {}) {
  const md = buildMarkdown(history, options)
  const filename = buildExportFilename('md', options.exportedAt)
  downloadText(md, filename, 'text/markdown;charset=utf-8')
}

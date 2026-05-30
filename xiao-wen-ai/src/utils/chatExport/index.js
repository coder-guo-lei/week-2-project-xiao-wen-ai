import { normalizeHistory, groupTurns } from './format.js'
import { exportChatMarkdown, buildMarkdown } from './exportMarkdown.js'
import { exportChatDocx } from './exportDocx.js'
import { exportChatPdf } from './exportPdf.js'

export { normalizeHistory, groupTurns, buildMarkdown }

export const EXPORT_FORMATS = {
  markdown: { label: 'Markdown', ext: 'md', export: exportChatMarkdown },
  docx: { label: 'Word', ext: 'docx', export: exportChatDocx },
  pdf: { label: 'PDF', ext: 'pdf', export: exportChatPdf },
}

export async function exportChatHistory(format, history, options = {}) {
  const normalized = normalizeHistory(history)
  if (normalized.length === 0) {
    throw new Error('暂无对话记录可导出')
  }
  const handler = EXPORT_FORMATS[format]
  if (!handler) throw new Error(`不支持的导出格式：${format}`)
  await handler.export(normalized, options)
}

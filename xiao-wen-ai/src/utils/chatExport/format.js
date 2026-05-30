/** 对话记录导出：归一化、分组、文件名与时间戳 */

export function normalizeHistory(history) {
  if (!Array.isArray(history)) return []
  return history.filter(
    (m) => m && (m.role === 'user' || m.role === 'assistant') && String(m.content ?? '').trim(),
  )
}

/** 将扁平 history 按 user + assistant 配对为轮次 */
export function groupTurns(history) {
  const list = normalizeHistory(history)
  const turns = []
  for (let i = 0; i < list.length; i++) {
    if (list[i].role !== 'user') continue
    const userContent = String(list[i].content).trim()
    let assistantContent = ''
    if (list[i + 1]?.role === 'assistant') {
      assistantContent = String(list[i + 1].content).trim()
      i += 1
    }
    turns.push({ user: userContent, assistant: assistantContent })
  }
  return turns
}

export function formatExportTimestamp(date = new Date()) {
  const p = (n) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${p(date.getMonth() + 1)}-${p(date.getDate())} ${p(date.getHours())}:${p(date.getMinutes())}:${p(date.getSeconds())}`
}

export function buildExportFilename(ext, date = new Date()) {
  const p = (n) => String(n).padStart(2, '0')
  const stamp = `${date.getFullYear()}${p(date.getMonth() + 1)}${p(date.getDate())}_${p(date.getHours())}${p(date.getMinutes())}`
  return `小文对话记录_${stamp}.${ext}`
}

export function escapeHtml(text) {
  return String(text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

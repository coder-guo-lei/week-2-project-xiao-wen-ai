import { groupTurns, formatExportTimestamp, buildExportFilename, escapeHtml } from './format.js'

const PDF_ROOT_ID = 'xiaowen-chat-export-root'

function buildExportHtml(history, exportedAt) {
  const turns = groupTurns(history)
  const turnBlocks = turns
    .map(
      (turn, idx) => `
    <section class="turn">
      <h2>第 ${idx + 1} 轮</h2>
      <h3 class="role-user">用户</h3>
      <div class="content">${escapeHtml(turn.user).replace(/\n/g, '<br/>')}</div>
      <h3 class="role-assistant">小文</h3>
      <div class="content">${escapeHtml(turn.assistant || '（无回复）').replace(/\n/g, '<br/>')}</div>
    </section>`,
    )
    .join('')

  return `
<div class="export-doc">
  <h1>小文 AI 对话记录</h1>
  <p class="meta">导出时间：${escapeHtml(formatExportTimestamp(exportedAt))} · 对话轮次：${turns.length}</p>
  ${turnBlocks || '<p class="empty">暂无对话内容</p>'}
</div>`
}

function injectStyles(root) {
  const style = document.createElement('style')
  style.textContent = `
    #${PDF_ROOT_ID} {
      position: fixed; left: -9999px; top: 0;
      width: 794px; padding: 40px 48px;
      background: #fff; color: #1c1917;
      font-family: "Noto Sans SC", "PingFang SC", "Microsoft YaHei", sans-serif;
      font-size: 14px; line-height: 1.75;
      box-sizing: border-box;
    }
    #${PDF_ROOT_ID} .export-doc h1 {
      font-size: 22px; font-weight: 700; text-align: center;
      margin: 0 0 8px; color: #2a6e64;
    }
    #${PDF_ROOT_ID} .meta {
      text-align: center; font-size: 12px; color: #8c857c;
      margin: 0 0 24px; padding-bottom: 16px;
      border-bottom: 1px solid #ddd6c8;
    }
    #${PDF_ROOT_ID} .turn { margin-bottom: 20px; page-break-inside: avoid; }
    #${PDF_ROOT_ID} .turn h2 {
      font-size: 16px; font-weight: 700; margin: 16px 0 10px;
      color: #1c1917; border-left: 4px solid #3d8a80; padding-left: 10px;
    }
    #${PDF_ROOT_ID} .turn h3 {
      font-size: 13px; font-weight: 600; margin: 12px 0 6px;
    }
    #${PDF_ROOT_ID} .role-user { color: #2a6e64; }
    #${PDF_ROOT_ID} .role-assistant { color: #57534e; }
    #${PDF_ROOT_ID} .content {
      background: #f7f2ea; border: 1px solid #ddd6c8;
      border-radius: 8px; padding: 10px 14px; margin-bottom: 8px;
      word-break: break-word;
    }
    #${PDF_ROOT_ID} .empty { color: #8c857c; text-align: center; }
  `
  root.appendChild(style)
}

async function waitForFonts() {
  if (document.fonts?.ready) {
    await document.fonts.ready
  }
}

export async function exportChatPdf(history, options = {}) {
  const exportedAt = options.exportedAt ?? new Date()
  const turns = groupTurns(history)
  if (turns.length === 0) {
    throw new Error('暂无对话记录可导出')
  }

  let root = document.getElementById(PDF_ROOT_ID)
  if (!root) {
    root = document.createElement('div')
    root.id = PDF_ROOT_ID
    document.body.appendChild(root)
  }
  root.innerHTML = ''
  injectStyles(root)
  root.insertAdjacentHTML('beforeend', buildExportHtml(history, exportedAt))

  await waitForFonts()
  await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)))

  const html2pdf = (await import('html2pdf.js')).default
  const target = root.querySelector('.export-doc')
  const filename = buildExportFilename('pdf', exportedAt)

  await html2pdf()
    .set({
      margin: [12, 14, 12, 14],
      filename,
      image: { type: 'jpeg', quality: 0.95 },
      html2canvas: { scale: 2, useCORS: true, letterRendering: true },
      jsPDF: { unit: 'mm', format: 'a4', orientation: 'portrait' },
      pagebreak: { mode: ['avoid-all', 'css', 'legacy'] },
    })
    .from(target)
    .save()

  root.remove()
}

import { Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType } from 'docx'
import { groupTurns, formatExportTimestamp, buildExportFilename } from './format.js'
import { downloadBlob } from './download.js'

const USER_COLOR = '2A6E64'
const ASSISTANT_COLOR = '57534E'
const META_COLOR = '8C857C'

export async function exportChatDocx(history, options = {}) {
  const exportedAt = options.exportedAt ?? new Date()
  const turns = groupTurns(history)
  const children = [
    new Paragraph({
      heading: HeadingLevel.TITLE,
      alignment: AlignmentType.CENTER,
      children: [
        new TextRun({ text: '小文 AI 对话记录', bold: true, size: 44, font: 'Microsoft YaHei' }),
      ],
    }),
    new Paragraph({
      spacing: { after: 120 },
      children: [
        new TextRun({
          text: `导出时间：${formatExportTimestamp(exportedAt)}    对话轮次：${turns.length}`,
          size: 20,
          color: META_COLOR,
          font: 'Microsoft YaHei',
        }),
      ],
    }),
  ]

  turns.forEach((turn, idx) => {
    children.push(
      new Paragraph({
        heading: HeadingLevel.HEADING_1,
        spacing: { before: 280, after: 120 },
        children: [
          new TextRun({ text: `第 ${idx + 1} 轮`, bold: true, size: 28, font: 'Microsoft YaHei' }),
        ],
      }),
      new Paragraph({
        heading: HeadingLevel.HEADING_2,
        spacing: { after: 80 },
        children: [
          new TextRun({
            text: '用户',
            bold: true,
            size: 24,
            color: USER_COLOR,
            font: 'Microsoft YaHei',
          }),
        ],
      }),
      ...paragraphsFromText(turn.user, { spacingAfter: 160 }),
      new Paragraph({
        heading: HeadingLevel.HEADING_2,
        spacing: { before: 80, after: 80 },
        children: [
          new TextRun({
            text: '小文',
            bold: true,
            size: 24,
            color: ASSISTANT_COLOR,
            font: 'Microsoft YaHei',
          }),
        ],
      }),
      ...paragraphsFromText(turn.assistant || '（无回复）', { spacingAfter: 200 }),
    )
  })

  const doc = new Document({
    styles: {
      default: {
        document: {
          run: { font: 'Microsoft YaHei', size: 22 },
        },
      },
    },
    sections: [{ children }],
  })

  const blob = await Packer.toBlob(doc)
  downloadBlob(blob, buildExportFilename('docx', exportedAt))
}

function paragraphsFromText(text, { spacingAfter = 120 } = {}) {
  const chunks = String(text).split(/\n/)
  return chunks.map(
    (line, i) =>
      new Paragraph({
        spacing: { after: i === chunks.length - 1 ? spacingAfter : 60, line: 360 },
        children: [new TextRun({ text: line || ' ', size: 22, font: 'Microsoft YaHei' })],
      }),
  )
}

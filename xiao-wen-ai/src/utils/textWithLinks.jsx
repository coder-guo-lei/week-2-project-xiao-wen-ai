/** 将文本中的 http(s) 链接渲染为可点击 <a> */
export function renderTextWithLinks(text) {
  const urlRegex = /(https?:\/\/[^\s，。！？；、]+)/g
  const parts = String(text ?? '').split(urlRegex)
  return parts.map((part, index) => {
    if (/^https?:\/\//.test(part)) {
      return (
        <a key={`${part}-${index}`} href={part} target="_blank" rel="noreferrer">
          {part}
        </a>
      )
    }
    return part
  })
}

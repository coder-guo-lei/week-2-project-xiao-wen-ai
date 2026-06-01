/**
 * 讯飞 TTS 发音人：在线合成 v2 + 超拟人（与 backend/config 映射一致）
 */

export const TTS_CLASSIC_VOICES = [
  { value: 'x4_xiaoyan', label: '讯飞小燕', tag: '女声' },
  { value: 'x4_yezi', label: '讯飞小露', tag: '女声' },
  { value: 'aisjiuxu', label: '讯飞许久', tag: '男声' },
  { value: 'aisjinger', label: '讯飞小婧', tag: '女声' },
  { value: 'aisbabyxu', label: '讯飞许小宝', tag: '童声' },
]

/** 控制台「超拟人语音合成」已领取发音人 */
export const TTS_SUPER_VOICES = [
  { value: 'x6_lingxiaoxuan_pro', label: '聆小璇', tag: '女声' },
  { value: 'x5_lingyuzhao_flow', label: '聆玉昭', tag: '女声' },
  { value: 'x6_lingxiaoyue_pro', label: '聆小玥', tag: '女声' },
  { value: 'x6_lingyuyan_pro', label: '聆玉言', tag: '女声' },
  { value: 'x6_lingfeiyi_pro', label: '聆飞逸', tag: '男声' },
  { value: 'x6_wumeinv_pro', label: '妩媚姐姐', tag: '女声' },
  { value: 'x6_ruyadashu_pro', label: '儒雅大叔', tag: '男声' },
]

/** @deprecated 合并列表，兼容旧引用 */
export const TTS_VOICE_OPTIONS = [...TTS_CLASSIC_VOICES, ...TTS_SUPER_VOICES]

const VCN_PATTERN = /^[a-zA-Z0-9_]{2,128}$/

const LEGACY_MAP = {
  default: 'x4_xiaoyan',
  female: 'x4_xiaoyan',
  gentle_female: 'aisjiuxu',
  steady_male: 'x6_lingfeiyi_pro',
  female_jiuxu: 'aisjiuxu',
  super_default: 'x6_lingxiaoxuan_pro',
}

const ALL_VOICES = [...TTS_CLASSIC_VOICES, ...TTS_SUPER_VOICES]

export function normalizeTtsVoice(voice) {
  const v = String(voice || '').trim()
  if (!v) return 'x4_xiaoyan'
  if (LEGACY_MAP[v]) return LEGACY_MAP[v]
  if (VCN_PATTERN.test(v)) return v
  return 'x4_xiaoyan'
}

export function isSuperTtsVoice(voice) {
  const v = normalizeTtsVoice(voice)
  if (TTS_SUPER_VOICES.some((o) => o.value === v)) return true
  if (TTS_CLASSIC_VOICES.some((o) => o.value === v)) return false
  return /^x[567]_/.test(v)
}

export function ttsVoiceLabel(voice) {
  const v = normalizeTtsVoice(voice)
  const hit = ALL_VOICES.find((o) => o.value === v)
  if (hit) return `${hit.label}（${isSuperTtsVoice(v) ? '超拟人' : '在线'}）`
  return v
}

export function ttsEngineLabel(voice) {
  return isSuperTtsVoice(voice) ? '超拟人' : '在线合成'
}

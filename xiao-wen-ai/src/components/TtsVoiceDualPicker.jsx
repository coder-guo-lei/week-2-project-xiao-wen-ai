/**
 * TtsVoiceDualPicker — 双栏音色：左「在线合成」右「超拟人」，点选即切换
 */
import {
  TTS_CLASSIC_VOICES,
  TTS_SUPER_VOICES,
  isSuperTtsVoice,
  normalizeTtsVoice,
  ttsEngineLabel,
  ttsVoiceLabel,
} from '../utils/ttsVoices'
import './TtsVoiceDualPicker.css'

function VoiceColumn({ title, subtitle, voices, value, disabled, onSelect }) {
  return (
    <div className="tts-dual-col">
      <div className="tts-dual-col-head">
        <span className="tts-dual-col-title">{title}</span>
        <span className="tts-dual-col-sub">{subtitle}</span>
      </div>
      <div className="tts-dual-list" role="listbox" aria-label={title}>
        {voices.map((v) => {
          const active = value === v.value
          return (
            <button
              key={v.value}
              type="button"
              role="option"
              aria-selected={active}
              className={`tts-dual-item${active ? ' tts-dual-item--active' : ''}`}
              disabled={disabled}
              onClick={() => onSelect(v.value)}
            >
              <span className="tts-dual-item-name">{v.label}</span>
              <span className="tts-dual-item-tag">{v.tag}</span>
            </button>
          )
        })}
      </div>
    </div>
  )
}

export default function TtsVoiceDualPicker({ value, onChange, disabled = false, compact = false }) {
  const vcn = normalizeTtsVoice(value)

  return (
    <div className={`tts-dual${compact ? ' tts-dual--compact' : ''}`}>
      <div className="tts-dual-summary">
        当前：<strong>{ttsVoiceLabel(vcn)}</strong>
        <span className="tts-dual-engine-badge">{ttsEngineLabel(vcn)}</span>
      </div>
      <div className="tts-dual-grid">
        <VoiceColumn
          title="在线合成"
          subtitle="基础发音人 · tts-api"
          voices={TTS_CLASSIC_VOICES}
          value={isSuperTtsVoice(vcn) ? '' : vcn}
          disabled={disabled}
          onSelect={onChange}
        />
        <VoiceColumn
          title="超拟人"
          subtitle="高自然度 · WebSocket"
          voices={TTS_SUPER_VOICES}
          value={isSuperTtsVoice(vcn) ? vcn : ''}
          disabled={disabled}
          onSelect={onChange}
        />
      </div>
    </div>
  )
}

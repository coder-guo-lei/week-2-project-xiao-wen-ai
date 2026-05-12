/**
 * WeatherCard.jsx — 天气信息卡片
 *
 * Props.data：
 *   city / weather / temperature / wind / humidity — 实况
 *   displayCity — 卡片主标题（如「保定市竞秀区」）
 *   regionLabel — 播报用完整行政区（可选）
 *   formattedAddress — 逆地理结构化地址，副标题展示（可选）
 *   outdoorTips — string[] 出行提示条目
 *   travelPlanText — 可选，行程 / 建议正文
 */
import './WeatherCard.css'

/** 关键词到 CSS linear-gradient 的映射，用于卡片背景 */
const WEATHER_GRADIENTS = {
  rain: 'linear-gradient(145deg, #334155 0%, #0f766e 55%, #134e4a 100%)',
  sunny: 'linear-gradient(135deg, #fde68a 0%, #f59e0b 45%, #ea580c 100%)',
  cloudy: 'linear-gradient(145deg, #94a3b8 0%, #64748b 40%, #3f4f5f 100%)',
  default: 'linear-gradient(145deg, #2dd4bf 0%, #147a6e 50%, #0f5f56 100%)',
}

/** 根据中文天气描述字符串选背景；无数据时用 default */
function getWeatherBg(weather) {
  if (!weather) return WEATHER_GRADIENTS.default
  if (weather.includes('雨')) return WEATHER_GRADIENTS.rain
  if (weather.includes('晴')) return WEATHER_GRADIENTS.sunny
  if (weather.includes('云') || weather.includes('阴')) return WEATHER_GRADIENTS.cloudy
  return WEATHER_GRADIENTS.default
}

/** 根据关键词返回 emoji 图标，增强可读性 */
function weatherIcon(weather) {
  if (!weather) return '🌈'
  if (weather.includes('雨')) return '🌧️'
  if (weather.includes('晴')) return '☀️'
  if (weather.includes('云')) return '⛅'
  if (weather.includes('阴')) return '☁️'
  if (weather.includes('雪')) return '❄️'
  return '🌈'
}

export default function WeatherCard({ data }) {
  // 父组件应保证有 data 才切到 weather 视图；此处再防一手
  if (!data) return null
  const title = (data.displayCity || data.city || '').trim() || '天气'
  const subAddr = (data.formattedAddress || '').trim()
  const tips = Array.isArray(data.outdoorTips) ? data.outdoorTips.filter(Boolean) : []
  const travel = typeof data.travelPlanText === 'string' ? data.travelPlanText.trim() : ''

  return (
    <div className="wc" style={{ background: getWeatherBg(data.weather) }}>
      <div className="wc-main">
        <span className="wc-icon">{weatherIcon(data.weather)}</span>
        <h2 className="wc-city">{title}</h2>
        {subAddr ? (
          <div className="wc-address" title={subAddr}>
            {data.locationSource === 'browser_gps' ? '📍 ' : ''}
            {subAddr.length > 48 ? `${subAddr.slice(0, 48)}…` : subAddr}
          </div>
        ) : null}
        <div className="wc-weather">{data.weather}</div>
        <div className="wc-temp">{data.temperature}</div>
        <div className="wc-detail">
          <span>{data.wind}</span>
          <span className="wc-dot">·</span>
          <span>湿度 {data.humidity}</span>
        </div>
      </div>

      {tips.length > 0 && (
        <div className="wc-panel wc-tips">
          <div className="wc-panel-title">出行提示</div>
          <ul className="wc-tip-list">
            {tips.map((t, i) => (
              <li key={i}>{t}</li>
            ))}
          </ul>
        </div>
      )}

      {travel ? (
        <div className="wc-panel wc-travel">
          <div className="wc-panel-title">行程与建议</div>
          <div className="wc-travel-body">{travel}</div>
        </div>
      ) : null}
    </div>
  )
}

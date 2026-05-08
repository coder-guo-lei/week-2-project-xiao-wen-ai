/**
 * WeatherCard.jsx — 天气信息卡片
 *
 * 功能：
 *   - 根据天气状况（晴 / 雨 / 云阴）切换背景渐变色和天气图标
 *   - 展示城市、天气描述、气温、风力、湿度
 * Props：
 *   data {object} 天气数据，字段：city / weather / temperature / wind / humidity
 */
import './WeatherCard.css'

/** 关键词到 CSS linear-gradient 的映射，用于卡片背景 */
const WEATHER_GRADIENTS = {
  rain: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
  sunny: 'linear-gradient(135deg, #f6d365 0%, #fda085 100%)',
  cloudy: 'linear-gradient(135deg, #a8c0ff 0%, #3f2b96 40%)',
  default: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
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
  return (
    <div className="wc" style={{ background: getWeatherBg(data.weather) }}>
      <span className="wc-icon">{weatherIcon(data.weather)}</span>
      <h2 className="wc-city">{data.city}</h2>
      <div className="wc-weather">{data.weather}</div>
      <div className="wc-temp">{data.temperature}</div>
      <div className="wc-detail">
        <span>{data.wind}</span>
        <span className="wc-dot">·</span>
        <span>湿度 {data.humidity}</span>
      </div>
    </div>
  )
}

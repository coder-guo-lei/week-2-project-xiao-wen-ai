/**
 * 前端入口：把 React 根组件挂到 index.html 里的 <div id="root">。
 * 整站只 mount 一次 App；全局样式在 index.css。
 */
import { StrictMode } from 'react' // 开发模式下故意双重渲染子树，便于发现不纯副作用
import { createRoot } from 'react-dom/client' // React 18+ 客户端 API（取代 ReactDOM.render）
import './index.css' // 全局 CSS 变量、reset、字体
import App from './App.jsx' // 应用根：状态、请求、左右栏布局

// 在 #root 上创建 React 根并渲染整棵组件树
createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
)

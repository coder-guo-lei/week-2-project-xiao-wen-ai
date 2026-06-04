/**
 * MusicPlayer.jsx — 音乐播放器
 *
 * 功能：
 *   - 旋转唱片动画（播放时自动旋转）
 *   - 播放 / 暂停、上一首 / 下一首控制
 *   - 进度条（可点击跳转）+ 时间显示
 *   - 音量滑条（持久化到 localStorage）
 *   - 版权/链接错误时显示黄色提示条
 *   - 最近播放历史列表（最多 50 条，点击可切歌）
 * Props：
 *   music {object} useMusicPlayer() Hook 返回的全部状态与操作
 */
import { useState } from 'react'
import './MusicPlayer.css'

/** 秒 → m:ss，用于进度条两侧时间文案 */
function formatTime(seconds) {
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${mins}:${secs < 10 ? '0' : ''}${secs}`
}

export default function MusicPlayer({ music }) {
  const [showPlaylist, setShowPlaylist] = useState(false) // 是否展开底部播放列表
  const [showQishuiLogin, setShowQishuiLogin] = useState(true) // 汽水模式：是否展开内嵌登录 iframe
  const [qishuiFrameKey, setQishuiFrameKey] = useState(0) // 改 key 强制重载汽水播放 iframe
  const {
    audioRef,
    previewUrl,
    songName,
    currentProvider,
    qishuiUrl,
    qishuiEmbedUrl,
    isPlaying,
    currentTime,
    duration,
    playHistory,
    playIndex,
    audioError,
    volume,
    setVolume,
    jumpToTrack,
    removeTrack,
    clearHistory,
    togglePlayPause,
    playPrevious,
    playNext,
    handleSeek,
    audioHandlers,
  } = music
  // 汽水音乐：不走 <audio>，用官方 embed 页面播（依赖用户浏览器已登录）
  const isQishuiMode = currentProvider === 'qishui' && qishuiEmbedUrl
  const qishuiLoginUrl = 'https://music.douyin.com/qishui/'
  const refreshQishuiFrame = () => setQishuiFrameKey((prev) => prev + 1)

  /** 删除列表项时阻止事件冒泡到「播放」按钮 */
  const handleDeleteTrack = (e, idx) => {
    e.stopPropagation()
    removeTrack(idx)
  }

  return (
    <div className="mp">
      <div className="mp-main">
        {/* disc */}
        <div className="mp-disc-wrap">
          <div className={`mp-disc ${isPlaying ? 'mp-disc--spin' : ''}`}>
            <span className="mp-disc-note">♪</span>
          </div>
        </div>

        {/* meta */}
        <div className="mp-meta">
          <span className="mp-badge">{isQishuiMode ? '汽水音乐 · 会员播放' : '正在播放'}</span>
          <h4 className="mp-title">{songName}</h4>
          <p className="mp-sub">
            {isQishuiMode
              ? '可在项目内登录汽水音乐；若浏览器限制登录窗口，请用新窗口登录后刷新播放面板'
              : playIndex >= 0 && playHistory.length > 0
                ? `${playIndex + 1} / ${playHistory.length}`
                : '—'}
          </p>
        </div>

        {isQishuiMode && (
          <div className="mp-qishui-card">
            <div className="mp-qishui-head">
              <div>
                <strong>汽水音乐官方播放</strong>
                <span>会员歌曲由你的汽水账号授权播放，项目只负责嵌入官方页面</span>
              </div>
              <div className="mp-qishui-actions">
                <button
                  type="button"
                  className="mp-qishui-ghost"
                  onClick={() => setShowQishuiLogin((prev) => !prev)}
                >
                  {showQishuiLogin ? '收起登录' : '项目内登录'}
                </button>
                <button type="button" className="mp-qishui-ghost" onClick={refreshQishuiFrame}>
                  已登录，刷新
                </button>
                <a
                  href={qishuiUrl || qishuiEmbedUrl}
                  target="_blank"
                  rel="noreferrer"
                  className="mp-qishui-open"
                >
                  新窗口播放
                </a>
              </div>
            </div>

            {showQishuiLogin && (
              <div className="mp-qishui-login">
                <div className="mp-qishui-login-title">
                  <strong>项目内登录汽水音乐</strong>
                  <span>登录成功后点击“已登录，刷新”，播放页会读取浏览器登录状态</span>
                </div>
                <iframe
                  title="汽水音乐登录"
                  src={qishuiLoginUrl}
                  className="mp-qishui-login-frame"
                  loading="lazy"
                  allow="autoplay; clipboard-write; encrypted-media; fullscreen; picture-in-picture"
                  referrerPolicy="no-referrer-when-downgrade"
                />
              </div>
            )}

            <div className="mp-qishui-player-head">
              <span>当前播放页</span>
              <small>{songName}</small>
            </div>
            <iframe
              key={`${qishuiEmbedUrl}-${qishuiFrameKey}`}
              title={`汽水音乐 - ${songName}`}
              src={qishuiEmbedUrl}
              className="mp-qishui-frame"
              loading="lazy"
              allow="autoplay; clipboard-write; encrypted-media; fullscreen; picture-in-picture"
              referrerPolicy="no-referrer-when-downgrade"
            />
            <p className="mp-qishui-tip">
              如果登录或播放区域提示无法显示，说明汽水音乐官方限制第三方嵌入。此时点击“新窗口播放”完成登录/播放，项目会继续保留播放列表和入口。
            </p>
          </div>
        )}

        {/* error */}
        {audioError && (
          <div className="mp-error" role="alert">
            <span>⚠️</span>
            <span>{audioError}</span>
          </div>
        )}

        {/* controls */}
        {/* 普通音频：原生 audio + 进度条 + 音量 */}
        {!isQishuiMode && (
          <>
            <div className="mp-controls">
              <button
                className="mp-skip"
                onClick={playPrevious}
                disabled={!playHistory.length}
                title="上一首"
              >
                ⏮
              </button>
              <button
                className={`mp-play ${isPlaying ? 'is-paused' : ''}`}
                onClick={togglePlayPause}
              >
                {isPlaying ? '⏸' : '▶'}
              </button>
              <button
                className="mp-skip"
                onClick={playNext}
                disabled={!playHistory.length}
                title="下一首"
              >
                ⏭
              </button>
            </div>

            {/* progress */}
            <div className="mp-progress">
              <div className="mp-progress-track" onMouseDown={handleSeek}>
                <div
                  className="mp-progress-fill"
                  style={{ width: `${duration > 0 ? (currentTime / duration) * 100 : 0}%` }}
                />
              </div>
              <div className="mp-time">
                <span>{formatTime(currentTime)}</span>
                <span>{formatTime(duration)}</span>
              </div>
            </div>

            {/* volume */}
            <div className="mp-vol">
              <span className="mp-vol-icon">🔊</span>
              <input
                type="range"
                min="0"
                max="1"
                step="0.05"
                value={volume}
                onChange={(e) => setVolume(parseFloat(e.target.value))}
                className="mp-vol-slider"
              />
            </div>

            {/* key=previewUrl：换歌时强制重挂载 audio 元素，触发重新加载 */}
            <audio
              ref={audioRef}
              key={previewUrl}
              src={previewUrl}
              autoPlay
              preload="auto"
              style={{ display: 'none' }}
              {...audioHandlers}
            />
          </>
        )}

        <button
          type="button"
          className={`mp-list-toggle ${showPlaylist ? 'is-open' : ''}`}
          onClick={() => setShowPlaylist((prev) => !prev)}
        >
          <span>📃 音乐列表</span>
          <span>{playHistory.length} 首</span>
        </button>
      </div>

      {/* playlist */}
      {showPlaylist && (
        <div className="mp-history mp-playlist-panel">
          <div className="mp-history-head">
            <span>音乐列表</span>
            <div className="mp-history-actions">
              <span className="mp-history-count">{playHistory.length} 首</span>
              <button
                type="button"
                className="mp-clear-btn"
                onClick={clearHistory}
                disabled={!playHistory.length}
              >
                清空
              </button>
            </div>
          </div>

          {playHistory.length > 0 ? (
            <ul className="mp-history-list mp-playlist-list">
              {[...playHistory].reverse().map((item, revIdx) => {
                const i = playHistory.length - 1 - revIdx
                return (
                  <li key={item.id}>
                    <div
                      className={`mp-history-item mp-playlist-item ${i === playIndex ? 'is-active' : ''}`}
                    >
                      <button
                        type="button"
                        className="mp-playlist-play"
                        onClick={() => jumpToTrack(i)}
                        title="播放这首"
                      >
                        <span className="mp-history-idx">{i + 1}</span>
                        <span className="mp-history-name">
                          {item.title}
                          {item.provider === 'qishui' && <em>汽水</em>}
                        </span>
                      </button>
                      <button
                        type="button"
                        className="mp-delete-btn"
                        onClick={(e) => handleDeleteTrack(e, i)}
                        title="删除这首"
                      >
                        删除
                      </button>
                    </div>
                  </li>
                )
              })}
            </ul>
          ) : (
            <div className="mp-empty-list">暂无音乐，先点播一首吧。</div>
          )}
        </div>
      )}
    </div>
  )
}

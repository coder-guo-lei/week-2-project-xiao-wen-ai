# `src/hooks/useMusicPlayer.js` — 模块说明

## 职责

封装 `<audio>` 驱动所需的**播放状态**、**播放列表（含汽水音乐元数据）**、**音量持久化**、**上一首/下一首**与 **reset**，供 `App.jsx` 与 `MusicPlayer.jsx` 使用。

## 常量

| 符号 | 含义 |
|------|------|
| `MUSIC_HISTORY_KEY` | `localStorage` 中播放历史 JSON。 |
| `MUSIC_VOLUME_KEY` | 音量 0–1 浮点字符串。 |
| `MAX_HISTORY` | 最多保留 50 条。 |

## 状态与 Ref（节选）

- `isPlaying`、`currentTime`、`duration`、`audioError`：与 DOM 音频事件同步。
- `playHistory`：每项含 `url`、`title`、`provider`、`qishuiUrl`、`qishuiEmbedUrl`、`id`；初始化时从 `localStorage` 过滤非法项。
- `playIndex`：当前曲目下标，`-1` 表示无。
- `previewUrl`、`songName`、`currentProvider`、`qishuiUrl`、`qishuiEmbedUrl`：当前曲展示与外链。
- `volume` + `setVolume`：写 `localStorage` 并设置 `audioRef.current.volume`。
- `audioRef`：由 `MusicPlayer` 绑定到 `<audio>`。
- `playHistoryRef`：`useEffect` 与 `playHistory` 同步，避免 `useCallback` 闭包读到旧列表。

## 主要方法（见源码 JSDoc）

| 方法 | 作用 |
|------|------|
| `persistHistory` | 更新 ref + `localStorage`。 |
| `jumpToTrack(idx)` | 播放历史中指定项并置 `isPlaying`。 |
| `enqueueTrack(url, title, meta)` | 新曲入队（同 URL 不重复追加），`queueMicrotask` 切到新索引并播放。 |
| `playPrevious` / `playNext` | 环形切换，返回是否成功（列表空则 false）。 |
| `togglePlayPause` / `handleSeek` | 播放控制与进度拖动。 |
| `reset` | 停止音频、清空预览与错误（`App` 在 `resetAllContent` 中调用）。 |

## 事件对象 `audioHandlers`

供 `MusicPlayer` 展开到 `<audio onTimeUpdate={...} />`：`onTimeUpdate`、`onEnded`（自动下一首）、`onLoadedMetadata`、`onError`。

## 与后端

- 后端 `type: music` 返回 `previewUrl`、`songName`、`musicProvider`、汽水 URL 等；`App.autoSendTask` 调用 `music.enqueueTrack(...)`。

# `backend/services/xfyun_iat.py` — 模块说明

## 职责概述

讯飞 **语音听写（流式版）**：`wss://iat-api.xfyun.cn/v2/iat`，输入为 **16kHz 16bit 单声道 PCM**；对外入口接受 **WAV 字节**，内部解码重采样后发送。

## 常量

| 符号 | 含义 |
|------|------|
| `IAT_HOST` / `IAT_PATH` | 听写服务域名与路径。 |
| `CHUNK_BYTES` | 1280 字节/帧（约 40ms@16k 16bit mono）。 |
| `CHUNK_INTERVAL_SEC` | 帧间隔 0.04s，模拟实时流。 |
| `MAX_PCM_BYTES` | 最多约 60s 16k 立体声转单声道后的字节上限截断。 |

## 函数说明

| 函数 | 作用 |
|------|------|
| `_xfyun_http_date_gmt` | 与 TTS 相同 GMT 日期串。 |
| `_xfyun_iat_ws_url` | 生成带鉴权 query 的 WSS URL。 |
| `_stereo_to_mono_i16` | 16bit 立体声交错 → 单声道平均。 |
| `_resample_mono_i16` | 无 `audioop` 时的线性插值重采样。 |
| `wav_to_pcm16k_mono` | `wave` 模块读 WAV，转 16k mono PCM。 |
| `_extract_line_text` | 从 `data.result.ws[].cw[].w` 拼出当前识别行。 |
| `transcribe_pcm16k_mono`（async） | 建立 WebSocket；**并行** `send_audio_frames` 与 `recv_results`（避免只发不收导致超时）；首帧带 `common`/`business`；末帧 `status=2`；超时 35s。 |
| `transcribe_pcm16k_mono_sync` | `asyncio.run` 包装。 |
| `transcribe_wav_bytes` | WAV → PCM → sync 听写；解码失败返回错误字符串。 |

## `audioop` 兼容

- Python 3.13+ 可能移除 `audioop`：先 `try import audioop`，失败则用纯 Python `_resample_mono_i16`。

## 与路由层

- `routes/api.py` 的 `speech_to_text` 校验 WAV 头后调用 `transcribe_wav_bytes`。

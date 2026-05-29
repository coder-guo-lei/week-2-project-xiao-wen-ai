# `backend/services/xfyun_tts.py` — 模块说明

## 职责概述

讯飞 **在线语音合成**：支持经典 **v2 WebSocket**（`tts-api.xfyun.cn`）与可选 **超拟人** WebSocket（`XFYUN_SUPER_TTS_WS_URL`）。处理文本长度限制（UTF-8 字节预算）、多段 PCM 拼接、MP3 与 WAV MIME、超拟人失败 **11200** 降级到经典发音人。

## 公开符号（文件末尾与中间导出）

| 符号 | 作用 |
|------|------|
| `plain_text_for_tts(raw)` | 去 Markdown/链接/Emoji 等，得到适合朗读的纯文本。 |
| `split_text_for_xfyun_chunks` | 按标点切段（旧/辅助逻辑）。 |
| `split_text_by_utf8_budget` | 按 UTF-8 字节上限切段，满足讯飞单次会话限制。 |
| `_xfyun_response_is_mp3` / `xfyun_response_is_mp3` | 超长多连接时强制 WAV（MP3 不可拼接）。 |
| `tts_cache_file` | 磁盘缓存文件路径（SHA256 命名）。 |
| `async_xfyun_tts_audio` | 异步入口：选 super/classic，返回 `(bytes, mime, engine_tag)`。 |

## 主要内部函数

- **`_xfyun_http_date_gmt`**：英文 RFC 2822 日期，鉴权必需（避免中文 locale）。
- **`_xfyun_auth_url`** / **`_xfyun_super_ws_auth_url`**：HMAC-SHA256 签名拼进 WSS URL。
- **`_pcm_to_wav`**：原始 PCM → 标准 WAV 容器。
- **`_xfyun_audio_business`**：经典 TTS 的 `business` 字段（`aue` raw/lame、`vcn`、`speed`、`volume`）。
- **`_xfyun_ws_one_shot`**：经典版一次 `data.status=2` 会话收发循环。
- **`_async_xfyun_super_tts_one_segment`**：超拟人单段合成，解析 `payload.audio` 流。
- **`super_vcn_to_classic_fallback`**：超拟人 vcn → 经典 vcn 映射表。
- **`_async_xfyun_classic_tts_audio` / `_async_xfyun_super_tts_audio`**：多段文本循环合成并拼接 PCM。
- **`_async_xfyun_tts_audio`**：总入口；超拟人捕获 11200 后降级 classic。

## 配置依赖（`config`）

`USE_XFYUN_SUPER_TTS`、`XFYUN_APP_ID`、`XFYUN_API_KEY`、`XFYUN_API_SECRET`、`XFYUN_TTS_*`、`TTS_CACHE_DIR`、`XFYUN_SUPER_*` 等。

## 与 `routes/api.py` 的衔接

- 路由层负责：`asyncio.run`、HTTP `Response` 头 `X-TTS-*`、错误 JSON。
- 本文件不负责 HTTP，只负责音频字节与 MIME。

"""讯飞语音听写（流式版）WebAPI — WebSocket iat-api.xfyun.cn/v2/iat，PCM 16k 单声道见文档。"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import io
import json
import logging
import urllib.parse
import wave
from datetime import datetime, timezone
from email.utils import format_datetime

import websockets

from config import XFYUN_API_KEY, XFYUN_API_SECRET, XFYUN_APP_ID

logger = logging.getLogger(__name__)

IAT_HOST = "iat-api.xfyun.cn"
IAT_PATH = "/v2/iat"
CHUNK_BYTES = 1280  # 文档建议 16k PCM 每帧约 40ms
CHUNK_INTERVAL_SEC = 0.04
MAX_PCM_BYTES = 16000 * 2 * 60  # 60s 上限


def _xfyun_http_date_gmt():
    return format_datetime(datetime.now(timezone.utc), usegmt=True)


def _xfyun_iat_ws_url(app_id: str, api_key: str, api_secret: str) -> str:
    """与 TTS 相同：host + date + GET path 做 HMAC-SHA256，query 带 authorization / date / host。"""
    date = _xfyun_http_date_gmt()
    signature_origin = f"host: {IAT_HOST}\ndate: {date}\nGET {IAT_PATH} HTTP/1.1"
    signature_sha = hmac.new(
        api_secret.encode("utf-8"),
        signature_origin.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()
    signature = base64.b64encode(signature_sha).decode()
    authorization_origin = (
        f'api_key="{api_key}", algorithm="hmac-sha256", '
        f'headers="host date request-line", signature="{signature}"'
    )
    authorization = base64.b64encode(authorization_origin.encode("utf-8")).decode()
    q = urllib.parse.urlencode(
        {
            "authorization": authorization,
            "date": date,
            "host": IAT_HOST,
        }
    )
    return f"wss://{IAT_HOST}{IAT_PATH}?{q}"


try:
    import audioop  # Python 3.13 起标准库可能移除，故保留纯 Python 回退
except ImportError:
    audioop = None


def _stereo_to_mono_i16(frames: bytes, width: int) -> bytes:
    import struct

    if width != 2:
        raise ValueError("仅支持 16bit WAV")
    n = len(frames) // 4
    mids = []
    for i in range(n):
        left, right = struct.unpack_from("<hh", frames, i * 4)
        mids.append((left + right) // 2)
    return struct.pack(f"<{len(mids)}h", *mids)


def _resample_mono_i16(frames: bytes, old_rate: int, new_rate: int) -> bytes:
    """线性插值重采样（无 audioop 时使用）。"""
    import struct

    n = len(frames) // 2
    samples = struct.unpack(f"<{n}h", frames)
    new_n = max(1, int(n * new_rate / old_rate))
    out: list[int] = []
    for j in range(new_n):
        src_pos = j * old_rate / new_rate
        i = int(src_pos)
        frac = src_pos - i
        if i + 1 < n:
            v = samples[i] * (1 - frac) + samples[i + 1] * frac
        else:
            v = float(samples[min(i, n - 1)])
        out.append(int(max(-32768, min(32767, round(v)))))
    return struct.pack(f"<{len(out)}h", *out)


def wav_to_pcm16k_mono(wav_bytes: bytes) -> bytes:
    """WAV → 16kHz 16bit 单声道 PCM（raw）。"""
    buf = io.BytesIO(wav_bytes)
    with wave.open(buf, "rb") as wf:
        channels = wf.getnchannels()
        width = wf.getsampwidth()
        rate = wf.getframerate()
        frames = wf.readframes(wf.getnframes())
    if width != 2:
        raise ValueError("仅支持 16bit PCM WAV（sampwidth=2）")
    if channels == 2:
        frames = _stereo_to_mono_i16(frames, width)
    elif channels != 1:
        raise ValueError("仅支持单声道或立体声")
    if rate == 16000:
        return frames
    if audioop is not None:
        frames, _ = audioop.ratecv(frames, width, 1, rate, 16000, None)
        return frames
    return _resample_mono_i16(frames, rate, 16000)


def _extract_line_text(result_block: dict) -> str:
    """从 data.result 抽取一行文本。"""
    parts: list[str] = []
    for ws in result_block.get("ws") or []:
        for cw in ws.get("cw") or []:
            w = cw.get("w")
            if w:
                parts.append(w)
    return "".join(parts)


async def transcribe_pcm16k_mono(pcm: bytes) -> tuple[str, str | None]:
    """
    发送 PCM 至讯飞听写，返回 (文本, 错误说明)。
    需在控制台开通「语音听写（流式版）」并使用同一套 AppID/APIKey/APISecret。
    """
    if not (XFYUN_APP_ID and XFYUN_API_KEY and XFYUN_API_SECRET):
        return "", "未配置讯飞密钥"
    pcm = pcm[:MAX_PCM_BYTES]
    if not pcm:
        return "", "音频为空"

    url = _xfyun_iat_ws_url(XFYUN_APP_ID, XFYUN_API_KEY, XFYUN_API_SECRET)
    last_text = ""
    recv_err: list[str | None] = [None]

    try:
        async with websockets.connect(
            url,
            max_size=None,
            ping_interval=20,
            ping_timeout=20,
        ) as ws:
            padding = (-len(pcm)) % CHUNK_BYTES
            padded = pcm + (b"\x00" * padding) if padding else pcm
            chunks = [padded[i : i + CHUNK_BYTES] for i in range(0, len(padded), CHUNK_BYTES)]
            if not chunks:
                chunks = [b""]

            async def send_audio_frames():
                """按帧发送；必须与 recv 并行，否则服务端下行堆积易导致「server read msg timeout」。"""
                for idx, chunk in enumerate(chunks):
                    is_first = idx == 0
                    status = 0 if is_first else 1
                    payload: dict = {
                        "data": {
                            "status": status,
                            "format": "audio/L16;rate=16000",
                            "encoding": "raw",
                            "audio": base64.b64encode(chunk).decode("ascii"),
                        }
                    }
                    if is_first:
                        payload["common"] = {"app_id": XFYUN_APP_ID}
                        payload["business"] = {
                            "language": "zh_cn",
                            "domain": "iat",
                            "accent": "mandarin",
                            "ptt": 1,
                        }
                    await ws.send(json.dumps(payload, ensure_ascii=False))
                    if idx < len(chunks) - 1:
                        await asyncio.sleep(CHUNK_INTERVAL_SEC)
                await ws.send(json.dumps({"data": {"status": 2}}, ensure_ascii=False))

            async def recv_results():
                nonlocal last_text
                while True:
                    try:
                        raw = await ws.recv()
                    except websockets.exceptions.ConnectionClosed:
                        break
                    try:
                        msg = json.loads(raw)
                    except json.JSONDecodeError:
                        continue

                    code = msg.get("code")
                    if code != 0:
                        err = msg.get("message") or str(code)
                        logger.warning("xfyun iat error frame: %s", msg)
                        recv_err[0] = err
                        break

                    data = msg.get("data") or {}
                    if data.get("result"):
                        line = _extract_line_text(data["result"])
                        if line:
                            last_text = line

            try:
                await asyncio.wait_for(
                    asyncio.gather(
                        send_audio_frames(),
                        recv_results(),
                        return_exceptions=True,
                    ),
                    timeout=35.0,
                )
            except asyncio.TimeoutError:
                return (last_text.strip() or ""), "听写连接超时（请缩短录音或检查网络）"

    except websockets.exceptions.ConnectionClosedOK:
        pass
    except websockets.exceptions.ConnectionClosedError as e:
        logger.warning("xfyun iat connection closed: %s", e)
    except Exception as e:
        logger.exception("xfyun iat failed")
        return "", str(e)

    if recv_err[0]:
        return "", recv_err[0]

    return last_text.strip(), None


def transcribe_pcm16k_mono_sync(pcm: bytes) -> tuple[str, str | None]:
    return asyncio.run(transcribe_pcm16k_mono(pcm))


def transcribe_wav_bytes(wav_bytes: bytes) -> tuple[str, str | None]:
    try:
        pcm = wav_to_pcm16k_mono(wav_bytes)
    except Exception as e:
        logger.warning("wav decode: %s", e)
        return "", f"无法解析 WAV：{e}"
    return transcribe_pcm16k_mono_sync(pcm)

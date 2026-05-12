"""讯飞在线 TTS + 超拟人 WebSocket 合成逻辑。"""
import base64
import hashlib
import hmac
import io
import json
import logging
import os
import unicodedata
import urllib.parse
import wave
from datetime import datetime, timezone
from email.utils import format_datetime
from pathlib import Path

import re

try:
    import websockets
except ImportError:
    websockets = None

logger = logging.getLogger(__name__)

from config import (
    TTS_CACHE_DIR,
    USE_XFYUN_SUPER_TTS,
    XFYUN_API_KEY,
    XFYUN_API_SECRET,
    XFYUN_APP_ID,
    XFYUN_SUPER_TEXT_UTF8_MAX,
    XFYUN_SUPER_TTS_SAMPLE_RATE,
    XFYUN_SUPER_TTS_WS_URL,
    XFYUN_TEXT_UTF8_MAX,
    XFYUN_TTS_AUDIO_FORMAT,
    XFYUN_TTS_SAMPLE_RATE,
)

def plain_text_for_tts(raw: str) -> str:
    """将小文回复转为适合语音合成的纯文本：去掉 Markdown、链接、文档锚点，避免读出星号或无关符号。"""
    if not raw:
        return ""
    s = unicodedata.normalize("NFKC", raw)
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    # Emoji / 彩色符号（如 😊）易被读成杂音或乱码，朗读前去掉
    s = re.sub(
        r"[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF"
        r"\U0001F1E0-\U0001F1FF\U00002700-\U000027BF\U0001F900-\U0001F9FF"
        r"\U00002600-\U000026FF\U0001FA70-\U0001FAFF]+",
        "",
        s,
    )
    s = s.replace("\ufe0f", "")
    s = re.sub(r"[\u200b-\u200d\ufeff]", "", s)
    s = re.sub(r"<br\s*/?>", "，", s, flags=re.I)
    s = re.sub(r"<[^>]+>", "", s)
    s = re.sub(r"```[\s\S]*?```", "。", s)
    s = re.sub(r"`([^`]+)`", r"\1", s)
    s = re.sub(r"!\[([^\]]*)\]\([^)]*\)", r"\1", s)
    s = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", s)
    for _ in range(8):
        prev = s
        s = re.sub(r"\*\*([^*]+)\*\*", r"\1", s)
        s = re.sub(r"__([^_]+)__", r"\1", s)
        if s == prev:
            break
    s = re.sub(r"(?<!\*)\*(?!\*)([^*]{1,800}?)(?<!\*)\*(?!\*)", r"\1", s)
    s = re.sub(r"(?m)^#+\s*", "", s)
    s = re.sub(r"(?m)^>\s*", "", s)
    s = re.sub(r"(?m)^[\s]*[-*+]\s+", "", s)
    s = re.sub(r"(?m)^\s*\d+\.\s+", "", s)
    s = re.sub(r"【[^】]*\.md(?:#[^】]*)?】", "。", s)
    s = re.sub(r"【([^】]{0,200})】", r"\1", s)
    s = re.sub(r"https?://[^\s\u3000，。！？；）』」\]】]+", "", s)
    s = re.sub(r"\*{1,2}", "", s)
    s = re.sub(r"#{1,6}\s*", "", s)
    s = re.sub(r"[ \t\f\v]+", " ", s)
    s = re.sub(r"\n+", "。", s)
    s = re.sub(r"。+", "。", s)
    return s.strip()


def split_text_for_xfyun_chunks(text: str, max_chars: int) -> list[str]:
    """按标点优先切段（用于旧逻辑）；讯飞单次会话见 split_text_by_utf8_budget。"""
    text = (text or "").strip()
    if not text:
        return []
    max_chars = max(120, min(int(max_chars), 600))
    if len(text) <= max_chars:
        return [text]

    pieces: list[str] = []
    start = 0
    n = len(text)
    while start < n:
        end = min(start + max_chars, n)
        if end < n:
            window = text[start:end]
            best = -1
            for sep in ("。", "！", "？", "\n", "；", "，", "、"):
                p = window.rfind(sep)
                if p > best:
                    best = p
            if best >= max(24, len(window) // 5):
                end = start + best + 1
        chunk = text[start:end].strip()
        if chunk:
            pieces.append(chunk)
        start = end if end > start else start + 1
    return [p for p in pieces if p]


# 讯飞文档：base64 前文本须 < 8000 字节；且「不支持多次分段传输」— 每连接只发 status=2 一次
XFYUN_TEXT_UTF8_MAX = 7800


def split_text_by_utf8_budget(text: str, max_bytes: int = XFYUN_TEXT_UTF8_MAX) -> list[str]:
    """按 UTF-8 字节预算切段。讯飞流式版每次会话只支持一段文本（status 必须为 2），超长则多连拼接 PCM。"""
    text = (text or "").strip()
    if not text:
        return []
    if len(text.encode("utf-8")) <= max_bytes:
        return [text]

    parts: list[str] = []
    buf = ""
    size = 0
    for ch in text:
        b = ch.encode("utf-8")
        if size + len(b) > max_bytes and buf:
            parts.append(buf)
            buf = ch
            size = len(b)
        else:
            buf += ch
            size += len(b)
    if buf:
        parts.append(buf)
    return parts


def _xfyun_response_is_mp3(spoken: str) -> bool:
    """MP3 不可跨会话拼接；超长文本拆多连接时只能输出 WAV。"""
    if XFYUN_TTS_AUDIO_FORMAT != "mp3":
        return False
    budget = XFYUN_SUPER_TEXT_UTF8_MAX if USE_XFYUN_SUPER_TTS else XFYUN_TEXT_UTF8_MAX
    return len(split_text_by_utf8_budget(spoken, budget)) <= 1


def _xfyun_http_date_gmt():
    """与讯飞鉴权一致：英文星期/月份（RFC 2822）。勿用 locale 的 strftime，否则中文系统会得到「周四/五月」导致 401。"""
    return format_datetime(datetime.now(timezone.utc), usegmt=True)


def _xfyun_auth_url(app_id: str, api_key: str, api_secret: str) -> str:
    date = _xfyun_http_date_gmt()
    signature_origin = f"host: tts-api.xfyun.cn\ndate: {date}\nGET /v2/tts HTTP/1.1"
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
    return (
        "wss://tts-api.xfyun.cn/v2/tts?"
        f"authorization={urllib.parse.quote(authorization, safe='')}"
        f"&date={urllib.parse.quote(date, safe='')}"
        f"&host=tts-api.xfyun.cn&appid={urllib.parse.quote(app_id, safe='')}"
    )


def _xfyun_super_ws_auth_url(base_wss: str, api_key: str, api_secret: str) -> str:
    """超拟人 WebSocket 鉴权（host/date/authorization 查询参数，见官方 demo）。"""
    u = urllib.parse.urlparse(base_wss)
    host = u.hostname or ""
    path = u.path or "/"
    date = _xfyun_http_date_gmt()
    signature_origin = f"host: {host}\ndate: {date}\nGET {path} HTTP/1.1"
    sig = hmac.new(
        api_secret.encode("utf-8"),
        signature_origin.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()
    signature = base64.b64encode(sig).decode()
    authorization_origin = (
        f'api_key="{api_key}", algorithm="hmac-sha256", '
        f'headers="host date request-line", signature="{signature}"'
    )
    authorization = base64.b64encode(authorization_origin.encode("utf-8")).decode()
    q = urllib.parse.urlencode(
        {
            "authorization": authorization,
            "date": date,
            "host": host,
        }
    )
    return f"{base_wss}?{q}"


def _tts_cache_file(vcn: str, speed: int, volume: int, text: str, audio_fmt: str) -> Path:
    """audio_fmt: wav | mp3（与合成格式一致，避免扩展名与内容不符）"""
    engine = "super" if USE_XFYUN_SUPER_TTS else "classic"
    sr_tag = str(XFYUN_SUPER_TTS_SAMPLE_RATE if USE_XFYUN_SUPER_TTS else XFYUN_TTS_SAMPLE_RATE)
    payload = f"v7_{engine}\n{sr_tag}\n{audio_fmt}\n{vcn}\n{speed}\n{volume}\n{text}".encode("utf-8")
    ext = ".wav" if audio_fmt == "wav" else ".mp3"
    name = hashlib.sha256(payload).hexdigest() + ext
    return TTS_CACHE_DIR / name


def _pcm_to_wav(pcm: bytes, sample_rate: int) -> bytes:
    """讯飞 raw/L16 单声道 16bit 小端 PCM → 标准 WAV。"""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm)
    return buf.getvalue()


def _xfyun_audio_business(vcn: str, speed: int, volume: int, want_mp3: bool) -> dict:
    """want_mp3：文档规定 lame 需 sfl=1；采样率仅支持 8k/16k。"""
    sp = max(0, min(100, speed))
    vol = max(0, min(100, volume))
    base = {"vcn": vcn, "speed": sp, "volume": vol, "tte": "UTF8"}
    if want_mp3:
        return {**base, "aue": "lame", "sfl": 1}
    sr = 8000 if XFYUN_TTS_SAMPLE_RATE <= 12000 else 16000
    return {**base, "aue": "raw", "auf": f"audio/L16;rate={sr}"}


async def _xfyun_ws_one_shot(text_segment: str, business: dict) -> bytes:
    """一次会话只发一条 JSON：data.status 固定为 2（见讯飞在线语音合成流式版文档）。"""
    url = _xfyun_auth_url(XFYUN_APP_ID, XFYUN_API_KEY, XFYUN_API_SECRET)
    out = bytearray()
    async with websockets.connect(
        url,
        ping_interval=20,
        ping_timeout=120,
        close_timeout=30,
        max_size=16 * 1024 * 1024,
    ) as ws:
        frame = {
            "common": {"app_id": XFYUN_APP_ID},
            "business": business,
            "data": {
                "status": 2,
                "text": base64.b64encode(text_segment.encode("utf-8")).decode("ascii"),
            },
        }
        await ws.send(json.dumps(frame))
        while True:
            raw = await ws.recv()
            msg = json.loads(raw)
            code = msg.get("code")
            if code != 0:
                err = msg.get("message", str(msg))
                raise RuntimeError(f"讯飞TTS错误({code}): {err}")
            d = msg.get("data") or {}
            aud = d.get("audio")
            if aud:
                out.extend(base64.b64decode(aud))
            if d.get("status") == 2:
                break
    return bytes(out)


async def _async_xfyun_super_tts_one_segment(
    text_segment: str,
    vcn: str,
    speed: int,
    volume: int,
    want_mp3: bool,
) -> bytes:
    """超拟人合成：一次性文本 header.status=2、payload.text.status=2；收齐 payload.audio 流。"""
    url = _xfyun_super_ws_auth_url(XFYUN_SUPER_TTS_WS_URL, XFYUN_API_KEY, XFYUN_API_SECRET)
    enc = "lame" if want_mp3 else "raw"
    oral_level = os.environ.get("XFYUN_SUPER_ORAL_LEVEL", "mid").strip().lower()
    if oral_level not in ("high", "mid", "low"):
        oral_level = "mid"
    try:
        spark_assist = int(os.environ.get("XFYUN_SUPER_SPARK_ASSIST", "1"))
    except (TypeError, ValueError):
        spark_assist = 1
    spark_assist = 1 if spark_assist else 0
    try:
        pitch = int(os.environ.get("XFYUN_SUPER_TTS_PITCH", "50"))
    except (TypeError, ValueError):
        pitch = 50
    pitch = max(0, min(100, pitch))

    parameter: dict = {}
    if os.environ.get("XFYUN_SUPER_ORAL_DISABLE", "").strip().lower() not in ("1", "true", "yes"):
        parameter["oral"] = {
            "oral_level": oral_level,
            "spark_assist": spark_assist,
            "stop_split": 0,
            "remain": 0,
        }
    parameter["tts"] = {
        "vcn": vcn,
        "speed": max(0, min(100, speed)),
        "volume": max(0, min(100, volume)),
        "pitch": pitch,
        "bgs": 0,
        "reg": 0,
        "rdn": 0,
        "rhy": 0,
        "audio": {
            "encoding": enc,
            "sample_rate": XFYUN_SUPER_TTS_SAMPLE_RATE,
            "channels": 1,
            "bit_depth": 16,
            "frame_size": 0,
        },
    }

    req = {
        "header": {"app_id": XFYUN_APP_ID, "status": 2},
        "parameter": parameter,
        "payload": {
            "text": {
                "encoding": "utf8",
                "compress": "raw",
                "format": "plain",
                "status": 2,
                "seq": 0,
                "text": base64.b64encode(text_segment.encode("utf-8")).decode("ascii"),
            }
        },
    }
    out = bytearray()
    audio_done = False
    async with websockets.connect(
        url,
        ping_interval=20,
        ping_timeout=120,
        close_timeout=30,
        max_size=16 * 1024 * 1024,
    ) as ws:
        await ws.send(json.dumps(req))
        for _ in range(4096):
            raw = await ws.recv()
            msg = json.loads(raw)
            hdr = msg.get("header") or {}
            code = hdr.get("code")
            if code is None:
                code = msg.get("code")
            if code is not None and int(code) != 0:
                err = hdr.get("message") or msg.get("message") or str(msg)
                raise RuntimeError(f"讯飞超拟人TTS错误({code}): {err}")
            pl = msg.get("payload") or {}
            aud = pl.get("audio")
            if isinstance(aud, dict):
                b64 = aud.get("audio")
                if b64:
                    out.extend(base64.b64decode(b64))
                if aud.get("status") == 2:
                    audio_done = True
                    break
        if not audio_done:
            raise RuntimeError("讯飞超拟人TTS错误：未收到结束帧（payload.audio.status=2）")
    return bytes(out)


def super_vcn_to_classic_fallback(super_vcn: str) -> str:
    """超拟人发音人 11200 未授权时，降级「在线语音合成」v2 的兼容 vcn（两套列表不通用）。"""
    v = (super_vcn or "").strip().lower()
    exact = {
        "x5_lingfeiyi_flow": "xiaofeng",
        "x5_lingxiaoxuan_flow": "xiaoyan",
        "x5_lingyuzhao_flow": "aisjiuxu",
        "x5_lingxiaoqi_flow": "xiaoyan",
    }
    if v in exact:
        return exact[v]
    if not v.startswith("x5_"):
        return "xiaoyan"
    if any(k in v for k in ("lingfei", "feiyi", "yufeng", "feichen", "yunjian", "xiyue")):
        return "xiaofeng"
    return "xiaoyan"


async def _async_xfyun_classic_tts_audio(
    text: str,
    vcn: str,
    speed: int,
    volume: int,
) -> tuple[bytes, str]:
    """在线语音合成 v2（tts-api.xfyun.cn），与超拟人发音人列表独立。"""
    segments = split_text_by_utf8_budget(text, XFYUN_TEXT_UTF8_MAX)
    if not segments:
        return b"", "audio/wav"

    want_mp3 = XFYUN_TTS_AUDIO_FORMAT == "mp3"
    if len(segments) > 1:
        want_mp3 = False

    sr = 8000 if XFYUN_TTS_SAMPLE_RATE <= 12000 else 16000
    pcm_parts: list[bytes] = []
    mp3_blob: bytes | None = None

    for seg in segments:
        biz = _xfyun_audio_business(vcn, speed, volume, want_mp3)
        chunk = await _xfyun_ws_one_shot(seg, biz)
        if want_mp3:
            mp3_blob = chunk
        else:
            pcm_parts.append(chunk)

    if want_mp3 and mp3_blob is not None:
        return mp3_blob, "audio/mpeg"

    pcm = b"".join(pcm_parts)
    if len(pcm) % 2:
        pcm = pcm[:-1]
    return _pcm_to_wav(pcm, sr), "audio/wav"


async def _async_xfyun_super_tts_audio(
    text: str,
    vcn: str,
    speed: int,
    volume: int,
) -> tuple[bytes, str]:
    """超拟人：raw PCM（推荐）或 lame MP3；超长按字节切段多连，仅拼 PCM 后封 WAV。"""
    segments = split_text_by_utf8_budget(text, XFYUN_SUPER_TEXT_UTF8_MAX)
    if not segments:
        return b"", "audio/wav"

    want_mp3 = XFYUN_TTS_AUDIO_FORMAT == "mp3"
    if len(segments) > 1:
        want_mp3 = False

    pcm_parts: list[bytes] = []
    mp3_blob: bytes | None = None
    sr = XFYUN_SUPER_TTS_SAMPLE_RATE

    for seg in segments:
        chunk = await _async_xfyun_super_tts_one_segment(seg, vcn, speed, volume, want_mp3)
        if want_mp3:
            mp3_blob = chunk
        else:
            pcm_parts.append(chunk)

    if want_mp3 and mp3_blob is not None:
        return mp3_blob, "audio/mpeg"

    pcm = b"".join(pcm_parts)
    if len(pcm) % 2:
        pcm = pcm[:-1]
    return _pcm_to_wav(pcm, sr), "audio/wav"


async def _async_xfyun_tts_audio(
    text: str,
    vcn: str,
    speed: int,
    volume: int,
) -> tuple[bytes, str, str]:
    """返回 (音频字节, MIME, 引擎标签)：super | classic | classic-fallback。
    超拟人 11200（发音人未授权）时自动走在线 v2 兼容发音人。"""
    if USE_XFYUN_SUPER_TTS:
        try:
            b, m = await _async_xfyun_super_tts_audio(text, vcn, speed, volume)
            return b, m, "super"
        except RuntimeError as e:
            err = str(e)
            if "11200" not in err and "未授权" not in err:
                raise
            classic_vcn = super_vcn_to_classic_fallback(vcn)
            logger.warning(
                "xfyun super TTS failed (%s), fallback to classic vcn=%s (was %s)",
                err[:120],
                classic_vcn,
                vcn,
            )
            b, m = await _async_xfyun_classic_tts_audio(text, classic_vcn, speed, volume)
            return b, m, "classic-fallback"

    b, m = await _async_xfyun_classic_tts_audio(text, vcn, speed, volume)
    return b, m, "classic"


xfyun_response_is_mp3 = _xfyun_response_is_mp3
tts_cache_file = _tts_cache_file
async_xfyun_tts_audio = _async_xfyun_tts_audio

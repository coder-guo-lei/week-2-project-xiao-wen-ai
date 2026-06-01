"""指令解析、天气、音乐、对话、图表、模拟世界等核心业务逻辑。"""
import base64
import csv
import io
import json
import logging
import os
import random
import re
import subprocess
import time
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

import requests

try:
    from zoneinfo import ZoneInfo
except ImportError:
    ZoneInfo = None

try:
    from zhdate import ZhDate
except ImportError:
    ZhDate = None

from config import (
    AMAP_KEY,
    CHAT_TIMEOUT,
    DASHSCOPE_API_KEY,
    DASHSCOPE_CHAT_MODEL,
    DASHSCOPE_CHAT_URL,
    DASHSCOPE_IMAGE_MODEL,
    DASHSCOPE_TASK_POLL_INTERVAL,
    DASHSCOPE_VL_MODEL,
    DEEPSEEK_API_KEY,
    DEEPSEEK_CHAT_MODEL,
    DEEPSEEK_CHAT_URL,
    IMAGE_SIZE,
    IMAGE_TASK_TIMEOUT,
    LOCAL_TIMEZONE,
    MAX_CHAT_HISTORY_MESSAGES,
    MAX_CHAT_MESSAGE_CHARS,
    MAX_KNOWLEDGE_SNIPPETS,
    MAX_UPLOAD_IMAGE_BYTES,
    MSG_LLM_NOT_CONFIGURED,
    PRIMARY_LLM_DEEPSEEK_FIRST,
    WORLD_SIM_LLM,
    WORLD_SIM_LLM_MIN_LEN,
    MSG_TRANSLATE_NOT_CONFIGURED,
    MSG_VISION_NEED_DASHSCOPE,
    NETEASE_HEADERS,
    REPO_ROOT,
    REQUEST_TIMEOUT,
    WORLD_ACTIONS,
    WORLD_THEMES,
    resolve_tencent_qq_exe,
    resolve_tencent_wechat_exe,
    resolve_douyin_exe,
    resolve_netease_cloud_exe,
)
import session
from logic.dialogue_manager import get_dialogue_manager, normalize_messages
from logic.intent_classifier import (
    INTENT_APP_LAUNCH,
    INTENT_APP_LIST,
    INTENT_CHART,
    INTENT_IMAGE_GENERATE,
    INTENT_IMAGE_LOOKUP,
    INTENT_IMAGE_UNDERSTANDING,
    INTENT_KNOWLEDGE,
    INTENT_LOCAL_FOOD,
    INTENT_MUSIC,
    INTENT_MUSIC_NAV,
    INTENT_WEATHER,
    INTENT_WEB_OPEN,
    INTENT_WORLD_CREATE,
    classify_intent,
    intent_workflow_label,
)
from logic.user_apps import load_user_apps, merge_launchers
from routes.preferences import build_personalized_system_prompt, load_user_preferences

logger = logging.getLogger(__name__)

# =============================================================================
# 【本文件导读】task_parser.py 体量很大，维护时优先用编辑器搜索「# ----------」章节标题。
#
# 大致结构（行号随版本变化，以文件中分隔线为准）：
#   · 文件开头 ~ 「1. 天气」前：通用 HTTP（OpenAI 兼容）、LLM 兜底、工具函数
#   · 「1. 天气查询模块」：高德天气、出行提示等
#   · 「2. 音乐搜索模块」：网易云等解析与外链
#   · 「3. AI 绘画模块」：文生图提交、轮询说明配合 routes/api.py
#   · 「4. 通用对话模块」：闲聊、知识库、翻译意图等
#   · 「5. 本地应用启动模块」：白名单、微信/QQ 路径解析、快捷方式
#   · 「6. 模拟世界对话模块」：文字 RPG 状态在 session
#   · 「6.5 数据图表生成模块」：CSV/从指令抽数
#   · 「7. 指令解析核心」：parse_command() — LLM 意图分类 + 规则兜底 + 缓存，再分发到各业务分支
#
# HTTP 与前端字段拼装见 routes/api.py；环境变量见 config.py。
# =============================================================================


def primary_chat_model_label():
    if PRIMARY_LLM_DEEPSEEK_FIRST:
        if DEEPSEEK_API_KEY:
            return DEEPSEEK_CHAT_MODEL
        if DASHSCOPE_API_KEY:
            return DASHSCOPE_CHAT_MODEL
    else:
        if DASHSCOPE_API_KEY:
            return DASHSCOPE_CHAT_MODEL
        if DEEPSEEK_API_KEY:
            return DEEPSEEK_CHAT_MODEL
    return "未配置"


def openai_compat_chat(api_url, api_key, model, messages, temperature=None):
    """调用 OpenAI 兼容的 chat/completions，成功返回文本，失败返回 None。"""
    if not api_key:
        return None
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    body = {"model": model, "messages": messages}
    if temperature is not None:
        body["temperature"] = temperature
    try:
        resp = requests.post(api_url, json=body, headers=headers, timeout=CHAT_TIMEOUT)
        data = resp.json()
        if resp.status_code != 200:
            err = data.get("error") or data.get("message") or data
            logger.error("LLM HTTP %s: %s", resp.status_code, err)
            return None
        if data.get("error"):
            logger.error("LLM error field: %s", data.get("error"))
            return None
        choices = data.get("choices") or []
        if choices:
            content = (choices[0].get("message") or {}).get("content")
            if content:
                return content.strip()
    except requests.RequestException as e:
        logger.error("LLM request: %s", e)
    except Exception as e:
        logger.error("LLM error: %s", e)
    return None


def openai_compat_chat_fallback(messages, temperature=None):
    """按 PRIMARY_LLM 顺序调用 DashScope 与 DeepSeek，成功返回文本。"""
    order = [
        (DASHSCOPE_CHAT_URL, DASHSCOPE_API_KEY, DASHSCOPE_CHAT_MODEL),
        (DEEPSEEK_CHAT_URL, DEEPSEEK_API_KEY, DEEPSEEK_CHAT_MODEL),
    ]
    if PRIMARY_LLM_DEEPSEEK_FIRST:
        order.reverse()
    for url, key, model in order:
        text = openai_compat_chat(url, key, model, messages, temperature)
        if text:
            return text
    return None


logger.info(
    "LLM：DashScope=%s | DeepSeek=%s | 对话模型展示=%s | 高德=%s",
    "已配置" if DASHSCOPE_API_KEY else "未配置",
    "已配置(%s)" % DEEPSEEK_CHAT_MODEL if DEEPSEEK_API_KEY else "未配置",
    primary_chat_model_label(),
    "已配置 AMAP_KEY" if AMAP_KEY else "未配置（天气为占位数据）",
)


def workflow_steps(*items):
    """返回前端可视化的任务执行链路。"""
    return [{"title": title, "detail": detail} for title, detail in items]


def with_workflow(result, *items):
    result["workflow"] = workflow_steps(*items)
    return result


def is_music_intent(task):
    """避免「听个笑话 / 讲个故事」等被误判为音乐。"""
    if ("笑话" in task or "故事" in task or "相声" in task) and not any(
        x in task for x in ("音乐", "歌", "曲", "播放", "唱")
    ):
        return False
    nav_kw = (
        "换一首", "换首歌", "下一首", "上一首", "前一首", "切歌", "下首歌", "上首歌",
        "再换一首", "再来一首", "随机一首", "随便换", "再换",
    )
    if any(k in task for k in nav_kw):
        return True
    if any(k in task for k in ("来一首", "来首歌", "来个歌", "放首歌", "播首歌")):
        return True
    return any(kw in task for kw in ["播放", "听", "音乐", "歌", "唱"])


# -------------------------- 1. 天气查询模块 --------------------------
_WEATHER_DEICTIC_FRAGMENT = re.compile(
    r'那边|这里|当地|本地|那里|这边|附近|周围|哪儿|哪里|啥地方|什么地方|'
    r'咋样|啥样|如何|怎样|怎么样|好不|冷不冷|热不热|下不下雨|'
    r'这两天|那几天|这些天|近来|最近|今儿|那天'
)

_COMMON_WEATHER_CITIES = tuple(
    sorted(
        {
            "乌鲁木齐",
            "呼和浩特",
            "齐齐哈尔",
            "石家庄",
            "哈尔滨",
            "秦皇岛",
            "香格里拉",
            "西双版纳",
            "连云港",
            "张家界",
            "喀什",
            "呼伦贝尔",
            "满洲里",
            "齐齐哈尔",
            "北京",
            "上海",
            "天津",
            "重庆",
            "广州",
            "深圳",
            "杭州",
            "南京",
            "成都",
            "武汉",
            "西安",
            "苏州",
            "长沙",
            "郑州",
            "青岛",
            "厦门",
            "昆明",
            "大连",
            "沈阳",
            "济南",
            "合肥",
            "福州",
            "长春",
            "太原",
            "南昌",
            "贵阳",
            "南宁",
            "海口",
            "兰州",
            "银川",
            "西宁",
            "拉萨",
            "宁波",
            "无锡",
            "佛山",
            "东莞",
            "珠海",
            "桂林",
            "三亚",
            "温州",
            "烟台",
            "威海",
            "洛阳",
            "开封",
            "丽江",
            "大理",
            "敦煌",
            "绵阳",
            "保定",
            "唐山",
            "廊坊",
            "潍坊",
            "徐州",
            "常州",
            "扬州",
            "盐城",
            "绍兴",
            "台州",
            "嘉兴",
            "金华",
            "义乌",
            "赣州",
            "九江",
            "宜昌",
            "襄阳",
            "岳阳",
            "株洲",
            "湛江",
            "惠州",
            "中山",
            "江门",
            "汕头",
            "乐山",
            "宜宾",
            "遵义",
            "曲靖",
            "延吉",
            "丹东",
            "营口",
            "吉林",
            "大庆",
            "包头",
            "赤峰",
            "通辽",
            "聊城",
            "菏泽",
            "邯郸",
            "柳州",
            "北海",
            "漳州",
            "莆田",
            "宁德",
            "三明",
            "龙岩",
            "常德",
            "湘潭",
            "上饶",
            "鞍山",
            "大庆",
        },
        key=len,
        reverse=True,
    )
)

_WEATHER_STRIP_PREFIX = (
    "这两天",
    "那几天",
    "这些天",
    "最近",
    "请问",
    "我想知道",
    "想知道",
    "查一下",
    "帮忙看看",
    "帮忙",
    "那边",
    "这里",
    "那里",
    "这边",
    "当地",
    "本地",
    "那儿",
)
_WEATHER_STRIP_SUFFIX = ("怎么样", "如何", "咋样", "啥样", "好不", "怎样", "行吗")
_WEATHER_STRIP_INLINE = ("这两天", "那几天", "这些天", "最近", "那天")


def sanitize_weather_city_fragment(raw: str) -> str:
    """去掉天气问句里的时间指代、指示语等噪音，保留真实地名片段。"""
    s = raw.strip()
    for _ in range(5):
        prev = s
        for p in _WEATHER_STRIP_PREFIX:
            if s.startswith(p):
                s = s[len(p) :].strip()
        for p in _WEATHER_STRIP_SUFFIX:
            if s.endswith(p):
                s = s[: -len(p)].strip()
        for noise in _WEATHER_STRIP_INLINE:
            s = s.replace(noise, "").strip()
        for p in ("那边", "这里", "那儿", "这边"):
            if s.endswith(p):
                s = s[: -len(p)].strip()
        if s == prev:
            break
    return s


def extract_city_candidate(task: str) -> str | None:
    """从问句中提取地名候选；无法得到可靠地名时返回 None。"""
    patterns = [
        r"(.*?)天气",
        r"(.*?)的天气",
        r"我要(.*?)天气",
    ]
    for pattern in patterns:
        match = re.search(pattern, task)
        if not match:
            continue
        frag = sanitize_weather_city_fragment(match.group(1).strip())
        if len(frag) < 2 or frag in ("今天", "明天", "后天", "昨天"):
            continue
        # 「今天的天气」会把「今天的」误当地名；纯时间指代不参与城市解析
        if re.match(r"^(今|明|后)天(的)?$", frag) or re.match(r"^(今|明|后)天的", frag):
            continue
        if len(frag) > 12:
            continue
        if _WEATHER_DEICTIC_FRAGMENT.fullmatch(frag) or (
            len(frag) <= 8 and _WEATHER_DEICTIC_FRAGMENT.search(frag) and not re.search(r"[市县区州盟旗]|(?:北京|上海|天津|重庆)$", frag)
        ):
            continue
        return frag[:24]
    return None


_RE_USER_DEST = re.compile(
    r"(?:想)?(?:去|到|往|飞(?:到|往)?)([\u4e00-\u9fa5]{2,8}?)(?=玩|旅游|逛|出差|度假|两日|两天|三日|三天|几日|几天)"
)


def infer_city_from_single_task(text: str) -> str | None:
    """从当前这一句里抽目的地（如「想去北京玩两天…天气」→ 北京）。"""
    mo = _RE_USER_DEST.search(text)
    if mo:
        c = mo.group(1).strip()[:12]
        if len(c) >= 2:
            return c
    for name in _COMMON_WEATHER_CITIES:
        if name in text:
            return name
    return None


def infer_city_from_chat_history(history: list[dict], *, include_assistant: bool = True) -> str | None:
    """从近期对话里推断目的地（如「去北京玩两天」→ 北京）。
    查天气时建议 include_assistant=False：避免小文闲聊里提到「北京炸酱面」等被误当地点。"""
    if not history:
        return None

    def keyword_city(text: str) -> str | None:
        for name in _COMMON_WEATHER_CITIES:
            if name in text:
                return name
        return None

    for m in reversed(history):
        if m.get("role") != "user":
            continue
        content = (m.get("content") or "").strip()
        mo = _RE_USER_DEST.search(content)
        if mo:
            return mo.group(1).strip()[:12]

    for m in reversed(history):
        if m.get("role") != "user":
            continue
        hit = keyword_city((m.get("content") or "").strip())
        if hit:
            return hit

    if include_assistant:
        for m in reversed(history):
            if m.get("role") != "assistant":
                continue
            hit = keyword_city((m.get("content") or "").strip())
            if hit:
                return hit

    return None


def short_city_label(name: str) -> str:
    """卡片标题用的短地名（如「北京市」→「北京」）。"""
    n = (name or "").strip()
    if not n:
        return ""
    if len(n) > 2 and n.endswith(("市", "县", "区", "盟", "州")):
        n = n[:-1]
    return n[:12]


# 获取天气信息
# 先获取城市编码，再获取天气信息,在返回前端需要的格式天气信息
def get_weather_info(city="北京", adcode: str | None = None, location_detail: dict | None = None):
    """查天气：默认按城市名做地理编码；若传入 6 位 adcode（如来自 GPS 逆地理）则跳过地理编码。
    location_detail：逆地理结果，用于卡片与文案展示「省市区/街道」等明确地区。"""
    disp = short_city_label(city)
    placeholder = {
        "city": disp,
        "displayCity": disp,
        "weather": "晴",
        "temperature": "25°C",
        "wind": "微风",
        "humidity": "40%",
    }
    if not AMAP_KEY:
        logger.warning("未配置 AMAP_KEY，天气接口不可用，返回占位数据。请在 backend/.env 设置高德 Web 服务 Key。")
        return placeholder
    try:
        if adcode and re.fullmatch(r"\d{6}", str(adcode).strip()):
            ad = str(adcode).strip()
            weather_url = f"https://restapi.amap.com/v3/weather/weatherInfo?key={AMAP_KEY}&city={ad}"
            weather_resp = requests.get(weather_url, timeout=REQUEST_TIMEOUT)
            weather_data = weather_resp.json()
            if weather_data.get("status") == "1" and weather_data.get("lives"):
                live = weather_data["lives"][0]
                api_full = live["province"] + live["city"]
                out = {
                    "city": api_full,
                    "displayCity": disp or short_city_label(api_full),
                    "weather": live["weather"],
                    "temperature": live["temperature"] + "°C",
                    "wind": f"{live['winddirection']}风 {live['windpower']}级",
                    "humidity": live["humidity"] + "%",
                }
                if isinstance(location_detail, dict) and location_detail:
                    rl = (
                        location_detail.get("region_label_full")
                        or location_detail.get("region_label")
                        or ""
                    ).strip()
                    ct = (location_detail.get("card_title") or "").strip()
                    fmt = (location_detail.get("formatted_address") or "").strip()
                    if rl:
                        out["regionLabel"] = rl[:120]
                    if ct:
                        out["displayCity"] = ct[:48]
                    elif rl:
                        out["displayCity"] = rl[:48]
                    if fmt:
                        out["formattedAddress"] = fmt[:160]
                return out
            raise RuntimeError("weather by adcode empty")

        geo_url = f"https://restapi.amap.com/v3/geocode/geo?key={AMAP_KEY}&address={city}"
        geo_resp = requests.get(geo_url, timeout=REQUEST_TIMEOUT)
        geo_data = geo_resp.json()

        if geo_data["status"] != "1" or not geo_data.get("geocodes"):
            raise Exception(f"City '{city}' not found")

        ad = geo_data["geocodes"][0]["adcode"]

        weather_url = f"https://restapi.amap.com/v3/weather/weatherInfo?key={AMAP_KEY}&city={ad}"
        weather_resp = requests.get(weather_url, timeout=REQUEST_TIMEOUT)
        weather_data = weather_resp.json()

        if weather_data["status"] == "1" and weather_data.get("lives"):
            live = weather_data["lives"][0]
            api_full = live["province"] + live["city"]
            out = {
                "city": api_full,
                "displayCity": short_city_label(city),
                "weather": live["weather"],
                "temperature": live["temperature"] + "°C",
                "wind": f"{live['winddirection']}风 {live['windpower']}级",
                "humidity": live["humidity"] + "%",
            }
            if isinstance(location_detail, dict) and location_detail:
                rl = (
                    location_detail.get("region_label_full")
                    or location_detail.get("region_label")
                    or ""
                ).strip()
                if rl:
                    out["regionLabel"] = rl[:120]
                    out["displayCity"] = (location_detail.get("card_title") or rl)[:48]
                fmt = (location_detail.get("formatted_address") or "").strip()
                if fmt:
                    out["formattedAddress"] = fmt[:160]
            return out
    except Exception as e:
        logger.error(f"Weather API Error: {e}")

    return placeholder


def _amap_wgs84_to_gcj02(lng: float, lat: float) -> tuple[float, float]:
    """浏览器 GPS 多为 WGS84，高德国内接口需 GCJ02。"""
    if not AMAP_KEY:
        return lng, lat
    try:
        u = (
            "https://restapi.amap.com/v3/assistant/coordinate/convert"
            f"?key={AMAP_KEY}&locations={lng},{lat}&coordsys=gps&output=json"
        )
        r = requests.get(u, timeout=REQUEST_TIMEOUT)
        j = r.json()
        if j.get("status") == "1" and j.get("locations"):
            a, b = j["locations"].split(",")
            return float(a), float(b)
    except Exception as e:
        logger.warning("amap coordinate convert failed: %s", e)
    return lng, lat


def amap_regeocode_lng_lat(lng: float, lat: float) -> dict | None:
    """逆地理：返回 adcode、展示地名、完整地址等。"""
    if not AMAP_KEY:
        return None
    try:
        glng, glat = _amap_wgs84_to_gcj02(lng, lat)
        u = (
            "https://restapi.amap.com/v3/geocode/regeo"
            f"?key={AMAP_KEY}&location={glng},{glat}&radius=500&extensions=base"
        )
        r = requests.get(u, timeout=REQUEST_TIMEOUT)
        j = r.json()
        if j.get("status") != "1" or not j.get("regeocode"):
            return None
        comp = j["regeocode"].get("addressComponent") or {}

        def _ac_str(v):
            if v is None:
                return ""
            if isinstance(v, list):
                return str(v[0] or "").strip() if v else ""
            return str(v).strip()

        prov = _ac_str(comp.get("province"))
        city = _ac_str(comp.get("city"))
        dist = _ac_str(comp.get("district"))
        adcode = str(comp.get("adcode") or "").strip()
        if not re.fullmatch(r"\d{6}", adcode):
            return None
        fmt = (j["regeocode"].get("formatted_address") or "").strip()
        tw = _ac_str(comp.get("township"))
        st = _ac_str(comp.get("street"))
        sn = _ac_str(comp.get("streetNumber"))
        nb = _ac_str(comp.get("neighborhood"))
        if city:
            display = f"{prov}{city}".replace("市市", "市")
        elif dist:
            display = f"{prov}{dist}"
        else:
            display = prov or "当地"
        # 卡片/播报用：市+区 优先，便于「保定市竞秀区」这种明确地区
        card_title = ""
        if city and dist:
            card_title = f"{city}{dist}".replace("市市", "市")
        elif dist:
            card_title = f"{prov}{dist}" if prov else dist
        elif city:
            card_title = city
        else:
            card_title = display[:40]
        street_line = "".join(x for x in (st, sn) if x).strip()
        if tw and street_line:
            finer = f"{tw}{street_line}"
        elif tw:
            finer = tw
        elif nb:
            finer = nb
        elif street_line:
            finer = street_line
        else:
            finer = ""
        region_label = "".join(p for p in (prov, city, dist) if p).replace("市市", "市")
        if finer and finer not in region_label:
            region_label_full = f"{region_label}{finer}" if region_label else finer
        else:
            region_label_full = region_label or fmt or display
        return {
            "lng": glng,
            "lat": glat,
            "adcode": adcode,
            "formatted_address": fmt,
            "display_city": display[:48],
            "card_title": (card_title or display)[:40],
            "region_label": (region_label or display)[:80],
            "region_label_full": region_label_full[:120],
            "finer_location": finer[:80],
            "province": prov,
            "district": dist,
            "city": city,
            "township": tw,
            "street": st,
        }
    except Exception as e:
        logger.warning("amap regeo failed: %s", e)
    return None


def amap_nearby_dining(lng: float, lat: float, radius: int = 2500, limit: int = 8) -> list[dict]:
    """周边餐饮服务 POI（types=050000）。"""
    if not AMAP_KEY:
        return []
    try:
        glng, glat = _amap_wgs84_to_gcj02(lng, lat)
        u = (
            "https://restapi.amap.com/v3/place/around"
            f"?key={AMAP_KEY}&location={glng},{glat}&types=050000&radius={radius}&offset={limit}&extensions=all"
        )
        r = requests.get(u, timeout=REQUEST_TIMEOUT)
        j = r.json()
        if j.get("status") != "1":
            return []
        out = []
        for p in (j.get("pois") or [])[:limit]:
            name = (p.get("name") or "").strip()
            if not name:
                continue
            addr = (p.get("address") or "").strip()
            dist = (p.get("distance") or "").strip()
            out.append({"name": name, "address": addr, "distance_m": dist})
        return out
    except Exception as e:
        logger.warning("amap place around failed: %s", e)
    return []


def format_location_hint_for_llm(client_location: dict | None) -> str | None:
    """供闲聊模型参考的一句话位置描述（不含精确经纬度）。"""
    if not client_location:
        return None
    lng = client_location.get("lng") or client_location.get("longitude")
    lat = client_location.get("lat") or client_location.get("latitude")
    try:
        lng = float(lng)
        lat = float(lat)
    except (TypeError, ValueError):
        return None
    loc = amap_regeocode_lng_lat(lng, lat)
    if not loc:
        return None
    addr = loc.get("formatted_address") or loc.get("display_city") or ""
    if not addr:
        return None
    return f"用户已授权浏览器定位，大致位置：{addr}（逆地理结果，仅供参考）。"


def is_local_life_food_intent(task: str) -> bool:
    """饿了 / 附近吃什么 等本地生活美食意图（需配合前端传经纬度）。"""
    t = (task or "").strip()
    if len(t) > 160:
        return False
    if "天气" in t and "吃" not in t:
        return False
    keys = (
        "饿", "吃啥", "吃什么", "吃点", "有啥吃", "附近吃", "附近美食", "周边美食",
        "找吃的", "去哪吃", "宵夜", "夜宵", "外卖", "餐厅", "美食推荐", "推荐吃的",
        "小吃", "火锅", "喝一杯", "喝茶", "奶茶", "烧烤", "自助餐", "约饭",
    )
    return any(k in t for k in keys)


def compose_nearby_food_reply(task: str, lng: float, lat: float) -> str:
    """基于高德周边搜生成简短美食推荐文案。"""
    loc = amap_regeocode_lng_lat(lng, lat)
    area = (loc or {}).get("formatted_address") or (loc or {}).get("display_city") or "你附近"
    pois = amap_nearby_dining(lng, lat)
    if not pois:
        return (
            f"根据定位大致在「{area}」附近，但我暂时没能拉到周边餐厅列表（请检查是否已配置高德 AMAP_KEY，"
            "或稍后再试）。你也可以直接说「我在 XX 商场附近想吃火锅」让我帮你参谋。"
        )
    lines = [
        f"根据你的定位（{area}），附近约 {len(pois)} 家餐饮可参考（直线距离由地图估算，到店请以导航为准）：",
        "",
    ]
    for i, p in enumerate(pois, 1):
        dist = p.get("distance_m")
        dist_s = f"约 {dist} m" if dist else ""
        addr = p.get("address")
        tail = f" · {addr}" if addr else ""
        lines.append(f"{i}. **{p['name']}**{tail} {dist_s}".rstrip())
    lines.append("")
    lines.append("想更对口可以说清口味（清淡/辣/面食）或预算，我再帮你缩一圈。")
    return "\n".join(lines)


def _parse_temp_celsius(temp_field: str) -> int | None:
    m = re.search(r"-?\d+", temp_field or "")
    return int(m.group(0)) if m else None


def _parse_wind_power_level(wind_field: str) -> int | None:
    m = re.search(r"(\d+)\s*级", wind_field or "")
    return int(m.group(1)) if m else None


def _parse_humidity_pct(humidity_field: str) -> int | None:
    m = re.search(r"(\d+)", humidity_field or "")
    return int(m.group(1)) if m else None


def weather_outdoor_advice(data: dict) -> str:
    """根据实况生成出行注意事项（规则，不调用 LLM）。"""
    w = data.get("weather") or ""
    temp_s = data.get("temperature") or ""
    wind_s = data.get("wind") or ""
    hum_s = data.get("humidity") or ""
    t = _parse_temp_celsius(temp_s)
    wp = _parse_wind_power_level(wind_s)
    hum = _parse_humidity_pct(hum_s)

    lines = ["", "【出行提示】"]
    if "雨" in w or "雷" in w:
        lines.append("· 降水天气：携带雨具或防水外套，路面湿滑注意鞋底防滑；电子产品尽量防水收纳。")
    if "雪" in w:
        lines.append("· 降雪天气：防寒防滑，驾车预留更长制动距离，台阶与天桥谨防打滑。")
    if ("晴" in w or "多云" in w) and t is not None and t >= 28:
        lines.append("· 高温暴晒：避开正午长时间户外活动，勤补水并做好防晒（帽子/墨镜/防晒霜），谨防中暑。")
    if "雾" in w or "霾" in w:
        lines.append("· 能见度不佳：驾车减速、合理使用灯光；敏感人群减少高强度户外运动。")

    if t is not None:
        if t <= 5:
            lines.append("· 气温很低：厚外套、围巾手套按需穿戴，注意手脚与耳部保暖。")
        elif t <= 12:
            lines.append("· 体感偏凉：推荐叠穿便于穿脱，进出室内外及时增减衣物。")
        elif t >= 32:
            lines.append("· 酷热时段：老人、儿童及体弱者尽量减少暴晒环境下的长距离步行。")

    if wp is not None and wp >= 5:
        lines.append("· 风力较强：远离广告牌与临时围挡，骑行与撑伞注意安全。")
    elif wp is not None and wp >= 3:
        lines.append("· 有风天气：体感可能比气温更凉，可随身带一件薄外套。")

    if hum is not None:
        if hum >= 75:
            lines.append("· 湿度偏高：闷热易倦，注意补水与透气衣物，谨防中暑前兆。")
        elif hum <= 35:
            lines.append("· 空气偏干：多喝水，皮肤保湿；秋冬干燥季静电可能更明显。")

    if len(lines) == 2:
        lines.append("· 天气总体平稳：正常出行即可；仍建议随身带轻便折叠伞，以防局地短时阵雨。")

    return "\n".join(lines)


def is_weather_travel_intent(task: str) -> bool:
    return any(
        k in task
        for k in (
            "旅游",
            "旅行",
            "去玩",
            "出游",
            "度假",
            "攻略",
            "行程",
            "itinerary",
            "玩法",
            "打卡",
            "几日游",
            "几天",
            "一日游",
            "两日游",
            "三日游",
            "建议",
            "怎么安排",
            "安排一下",
        )
    )


def task_should_skip_weather_branch(task: str) -> bool:
    """粘贴/讨论代码时正文里常含「天气」（日志、接口、注释），勿因子串「天气」走查天气分支。"""
    if not task:
        return False
    if "```" in task:
        return True
    nl = task.count("\n")
    code_markers = ("def ", "import ", "class ", "function ", "const ", "SELECT ", "package ", "public static")
    if nl >= 5 and any(m in task for m in code_markers):
        return True
    if "代码" in task and any(
        s in task
        for s in ("咋样", "怎么样", "如何", "看下", "看看", "评价", "review", "优化", "重构", "对吗", "合理吗", "写得", "写的")
    ):
        return True
    if len(task) > 3200:
        return True
    return False


def weather_travel_fallback(city: str, data: dict) -> str:
    """无 LLM 时的简约行程框架。"""
    w = data.get("weather") or ""
    city_label = short_city_label(city)
    lines = [
        "",
        "【出游行程参考（简约版）】",
        "以下按常见节奏拆分，可按体力与兴趣删减；恶劣天气时段优先室内场馆。",
    ]
    if "雨" in w or "雷" in w:
        lines.append("· 上午：博物馆、美术馆或大型商场等室内场所，减少露天换乘。")
        lines.append("· 下午：若雨势减弱，可安排短时户外打卡，务必保持鞋袜干爽。")
        lines.append("· 傍晚：本地美食街区或室内夜市，注意台阶湿滑。")
    elif "晴" in w:
        lines.append("· 上午：地标或公园晨景，气温相对宜人。")
        lines.append("· 中午至午后：炎热时可穿插咖啡馆、展馆避暑歇脚。")
        lines.append("· 傍晚：步行街、河畔或观景台赏夜景，防晒补水别松懈。")
    else:
        lines.append("· 上午：城市文化街区或河畔步道轻松漫步。")
        lines.append("· 下午：公园湖景、特色展览或商圈购物。")
        lines.append("· 傍晚：夜市小吃或江边散步，留意返程交通高峰。")
    lines.append(f"· 通用贴士：用地图 App 关注「{city_label}」实时路况与末班车；饮食清淡补水，量力而行。")
    return "\n".join(lines)


def compose_weather_travel_plan(task: str, city: str, data: dict) -> str | None:
    """结合天气生成简短旅游日程；需配置对话模型。"""
    if not (DASHSCOPE_API_KEY or DEEPSEEK_API_KEY):
        return None
    snippet = json.dumps(data, ensure_ascii=False)
    user = (
        f"用户原话：{task.strip()[:600]}\n"
        f"目的地（查询城市）：{city}\n"
        f"当日实况天气（JSON）：{snippet}\n\n"
        "请用简体中文写一段「出游 / 一日游」实用安排：必须包含【上午】【下午】【傍晚】三个小标题；"
        "每段 2～4 句，要结合上述天气（防晒、雨具、室内外切换、防风保暖等）；"
        "景点举例 2～5 个即可，取该市常见类型（不必编造冷门细节或虚构票价）；"
        "文末一句交通或饮食提醒。总字数约 240～420。不要输出 JSON 或项目符号列表嵌套。"
    )
    messages = [
        {
            "role": "system",
            "content": "你是熟悉国内出行的旅行顾问，语气亲切务实，只输出正文与小标题。",
        },
        {"role": "user", "content": user},
    ]
    text = openai_compat_chat_fallback(messages, temperature=0.62)
    if not text or len(text.strip()) < 120:
        return None
    return text.strip()


def build_weather_reply(task: str, city: str, data: dict) -> str:
    """实况摘要 + 出行提示 +（可选）旅游日程。"""
    reg = (data.get("regionLabel") or "").strip()
    disp = (data.get("displayCity") or "").strip()
    addr = (data.get("formattedAddress") or "").strip()
    lead = ""
    if data.get("locationSource") == "browser_gps":
        if addr:
            lead = f"据定位「{addr[:76]}{'…' if len(addr) > 76 else ''}」附近，"
        else:
            lead = "据当前定位，"
        label = reg or disp or short_city_label(city)
    else:
        label = reg or disp or short_city_label(city)
    base = (
        f"{lead}{label}今天{data['weather']}，气温{data['temperature']}，"
        f"{data['wind']}，湿度{data['humidity']}"
    )
    text = base + weather_outdoor_advice(data)
    data.pop("travelPlanText", None)
    if is_weather_travel_intent(task):
        plan = compose_weather_travel_plan(task, city, data)
        sec = plan if plan else weather_travel_fallback(city, data)
        data["travelPlanText"] = sec.strip()
        text += "\n\n" + data["travelPlanText"]
    return text


# -------------------------- 2. 音乐搜索模块 --------------------------

_ASSISTANT_SONG_TITLE = re.compile(r"《([^》]{1,48})》|「([^」]{1,48})」")


def _assistant_song_titles_in_order(content):
    """从一条回复中按出现顺序列出《》/「」内歌名。"""
    out = []
    for m in _ASSISTANT_SONG_TITLE.finditer(content or ""):
        title = (m.group(1) or m.group(2) or "").strip()
        if title:
            out.append(title[:48])
    return out


def extract_song_title_from_recent_assistant(chat_history):
    """从最近一条小文回复里取《歌名》或「歌名」，用于「那就听这个吧」等指代。"""
    hist = normalize_chat_history(chat_history) if chat_history else []
    for turn in reversed(hist):
        if turn.get("role") != "assistant":
            continue
        titles = _assistant_song_titles_in_order(str(turn.get("content") or ""))
        if titles:
            return titles[0]
    return None


def is_deictic_play_request(task):
    """用户指「刚才那首 / 这个」，需结合上文《》歌名。"""
    t = (task or "").strip()
    if not t:
        return False
    needles = (
        "那就听这个",
        "就听这个",
        "听这个",
        "播这个",
        "放这个",
        "就要这首",
        "就这首",
        "听那首",
        "放那首",
        "刚才那首",
        "你说的那首",
        "听听这个",
        "就听你刚才",
        "就听你说的",
    )
    return any(n in t for n in needles)


def parse_music_navigation(task):
    """仅「切播放列表上一首/下一首」的短指令；含具体歌名（如换一首稻香）返回 None，走搜索。"""
    raw = (task or "").strip()
    if not raw:
        return None
    compact = re.sub(r"[，。,\s]+", "", raw)
    compact = re.sub(r"^(好[吧的呀]?|行|嗯|哦|呃|哎|那)+", "", compact)
    m_next = re.match(
        r"^(?:我要|我想|帮我|请|那)?(换一首|换首歌|换一曲|再换一首|再换|下一首|切歌|下首歌|再来一首|随机一首|随便换)([吧呢啊呀嘛呗]*)$",
        compact,
    )
    if m_next:
        return "next"
    # 「再换」「换」等极短切歌（整句即此，避免「再换工作」误触）
    if re.match(r"^(?:再)?换[吧呢啊呀嘛呗哇]*$", compact) and len(compact) <= 5:
        return "next"
    m_prev = re.match(
        r"^(?:我要|我想|帮我|请)?(上一首|前一首|上一曲|上首歌)([吧呢啊呀嘛呗]*)$",
        compact,
    )
    if m_prev:
        return "prev"
    return None


def is_music_language_followup(task, chat_history):
    """上一轮小文在聊歌（含《》）时，「英文的」「中文的吧」等短句走点歌而非闲聊。"""
    if not chat_history:
        return False
    t = (task or "").strip()
    if len(t) > 24:
        return False
    if not re.match(
        r"^(英文|英语|中文|汉语|国语|粤语)(?:(?:的|版|歌)+)?[吧呢啊呀嘛呗哇…。.…~～]*$",
        t,
        re.I,
    ):
        return False
    hist = normalize_chat_history(chat_history)
    for turn in reversed(hist):
        if turn.get("role") != "assistant":
            continue
        body = str(turn.get("content") or "")
        if "《" in body and "》" in body:
            return True
        if any(k in body for k in ("中文版", "英文版", "国语版", "粤语版", "还是英文", "还是中文")):
            return True
        break
    return False


def resolve_music_followup_search_query(task, chat_history):
    """根据当前短句 + 最近小文里的《》拼出搜索关键词（如 小幸运 英文）。"""
    hist = normalize_chat_history(chat_history) if chat_history else []
    last_assistant = ""
    for turn in reversed(hist):
        if turn.get("role") == "assistant":
            last_assistant = str(turn.get("content") or "")
            break
    if not last_assistant:
        return None

    raw_task = (task or "").strip()
    want_en = bool(re.search(r"英文|英语|english", raw_task, re.I))
    want_cn = bool(re.search(r"中文|汉语|国语|chinese", raw_task, re.I)) and not want_en

    m_book = re.search(r"《([^》]{1,48})》", raw_task)
    explicit = m_book.group(1).strip() if m_book else None
    if not explicit:
        m_tail = re.search(
            r"(?:英文|英语|中文|汉语|国语)(?:版|的)?\s*([\u4e00-\u9fa5·]{2,12})\s*$",
            raw_task,
        )
        if m_tail:
            explicit = m_tail.group(1).strip()

    titles = _assistant_song_titles_in_order(last_assistant)
    base = explicit
    if not base and titles:
        if want_en and len(titles) >= 2:
            base = titles[-1]
        else:
            base = titles[0]

    if not base:
        return None

    parts = [base]
    if want_en:
        parts.append("英文")
    elif want_cn:
        parts.append("中文")
    return " ".join(parts).strip()


def extract_music_query(task, chat_history=None):
    """从自然语言里抽出用于模糊搜索的歌名/关键词。"""
    t0 = task.strip()
    if chat_history and is_deictic_play_request(t0):
        hinted = extract_song_title_from_recent_assistant(chat_history)
        if hinted:
            return hinted
        # 上文没有《》歌名时，不把「那就听这个吧」整句当关键词去搜
        return "流行音乐"

    t = t0
    m = re.search(r"《([^》]+)》", t)
    if m:
        return m.group(1).strip()
    m = re.search(r"「([^」]+)」", t)
    if m:
        return m.group(1).strip()

    t = re.sub(r"^(用|使用)?(汽水音乐|汽水|网易云音乐|网易云|QQ音乐|酷狗音乐|酷我音乐)(来|给我)?", "", t).strip()
    t = re.sub(r"^(用|使用)", "", t).strip()

    prefixes = (
        "给我唱首歌吧", "给我唱首歌", "给我唱一首吧", "给我唱一首", "给我唱个歌", "给我唱吧", "给我唱",
        "唱首歌吧", "唱首歌", "唱一首吧", "唱一首", "唱个歌", "你唱首歌吧", "你唱一首",
        "给我放一首", "给我放首歌", "给我放", "给我来一首", "给我播",
        "随便放一首", "随便放点", "随便放", "放点音乐", "放点歌", "放点",
        "播放一首", "播放首歌", "播放音乐", "播放",
        "放一首", "放首歌", "放首歌吧", "放首", "放点儿", "放点儿歌",
        "来一首", "来首歌", "换一首", "播一首",
        "我想听一首", "我想听歌", "我想听", "我要听", "我要听歌",
        "听一首", "听歌", "听一下", "听听",
        "搜一首", "搜一下", "搜首歌",
        "来点音乐", "来点歌", "来点",
        "听音乐", "听歌儿",
    )
    for p in sorted(prefixes, key=len, reverse=True):
        if t.startswith(p):
            t = t[len(p) :].strip()
            break

    noise_end = ("这首歌", "这首歌吧", "吧", "呗", "嘛")
    for suf in sorted(noise_end, key=len, reverse=True):
        if t.endswith(suf) and len(t) > len(suf):
            t = t[: -len(suf)].strip()

    strip_words = ("一首", "首歌", "音乐", "曲子", "这首歌")
    for w in strip_words:
        if t == w:
            t = ""
            break

    t = re.sub(r"[吧呢啊呀哇]+$", "", t).strip()
    # 整句只剩「给我唱首歌」类套话、无具体歌名时，按随机流行搜，避免把整句当歌名去搜
    _vague_meta = re.compile(
        r"^(给?我)?(你)?(能|会)?(给?我)?(唱|来|放|播)?(一|两)?(首|个)?(歌|曲)?(吧|吗|呢|呀|嘛|呗|哇)?$"
    )
    if not t or _vague_meta.fullmatch(t):
        t = ""
    if not t:
        t = "流行音乐"
    return t


def search_itunes_preview(keyword):
    """搜索 Apple iTunes 试听源，返回可直接被浏览器 <audio> 播放的 previewUrl。"""
    try:
        resp = requests.get(
            "https://itunes.apple.com/search",
            params={"term": keyword, "media": "music", "entity": "song", "limit": 8, "country": "CN"},
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        results = data.get("results") or []
        for item in results:
            preview_url = item.get("previewUrl")
            if not preview_url or not preview_url.startswith("http"):
                continue
            title = item.get("trackName") or keyword
            artist = item.get("artistName") or ""
            label = f"{title}" + (f" — {artist}" if artist else "")
            logger.info("Music iTunes preview hit: %s", label)
            return preview_url, label
    except Exception as e:
        logger.warning("iTunes preview search failed: %s", e)
    return None, None


def search_netease_cloud(keyword):
    """网易云官方搜索 + 外链试听（模糊匹配第一条）。"""
    try:
        r = requests.get(
            "https://music.163.com/api/cloudsearch/pc",
            params={"s": keyword, "type": 1, "limit": 8, "offset": 0},
            headers=NETEASE_HEADERS,
            timeout=REQUEST_TIMEOUT,
        )
        r.raise_for_status()
        data = r.json()
        songs = (data.get("result") or {}).get("songs") or []
        if not songs:
            return None, None
        song = songs[0]
        sid = song.get("id")
        if not sid:
            return None, None
        name = song.get("name") or keyword
        artists = song.get("ar") or []
        an = artists[0].get("name", "") if artists else ""
        label = f"{name}" + (f" — {an}" if an else "")
        outer = f"https://music.163.com/song/media/outer/url?id={sid}.mp3"
        logger.info("Music NetEase search hit: %s -> id=%s", label, sid)
        return outer, label
    except Exception as e:
        logger.warning("NetEase cloudsearch failed: %s", e)
        return None, None


def build_qishui_music_urls(song_query):
    """生成汽水音乐官方网页链接。

    说明：汽水音乐会员内容不能通过后端直接破解成 mp3 外链；这里采用官方 Web 页面嵌入。
    用户在浏览器中登录自己的汽水音乐账号后，会员权益由汽水音乐官方页面处理。
    如果用户直接粘贴了 music.douyin.com/qishui/song/... 链接，就优先使用该歌曲页；否则生成搜索页。
    """
    url_match = re.search(r"https?://music\.douyin\.com/qishui/[^\s\"'<>]+", song_query)
    if url_match:
        url = url_match.group(0)
        return url, url
    keyword = urllib.parse.quote(song_query or "流行音乐")
    search_url = f"https://music.douyin.com/qishui/search?keyword={keyword}"
    return search_url, search_url


def search_music_url(task, chat_history=None, explicit_query=None):
    """多级降级：先搜 iTunes 试听,再搜网易云,再搜免费接口,最后兜底默认音乐。"""
    if explicit_query and str(explicit_query).strip():
        song_query = str(explicit_query).strip()
    else:
        song_query = extract_music_query(task, chat_history)
    wants_qishui = "汽水" in (task or "") or "music.douyin.com/qishui" in (task or "")
    qishui_url, qishui_embed_url = build_qishui_music_urls(song_query)

    if wants_qishui:
        return "", song_query, "qishui", qishui_url, qishui_embed_url

    music_url, label = search_itunes_preview(song_query)
    if music_url:
        return music_url, label, "audio", "", ""

    try:
        url = f"https://api.uomg.com/api/play/netease?name={urllib.parse.quote(song_query)}"
        resp = requests.get(url, timeout=REQUEST_TIMEOUT)
        data = resp.json()
        if data.get("code") == 1 and data.get("data"):
            mu = data["data"].get("url")
            if mu and mu.startswith("http"):
                logger.info("Music found via UOMG: %s", song_query)
                return mu, song_query, "audio", "", ""
    except Exception as e:
        logger.warning("UOMG API Failed: %s", e)

    try:
        url = f"https://api.lolimi.cn/API/yiny/?word={urllib.parse.quote(song_query)}&n=1"
        resp = requests.get(url, timeout=REQUEST_TIMEOUT)
        data = resp.json()
        if data.get("code") == 200 and data.get("data"):
            item = data["data"][0] if isinstance(data["data"], list) else data["data"]
            mu = item.get("url") or item.get("mp3")
            if mu and mu.startswith("http"):
                logger.info("Music found via LOLIMI: %s", song_query)
                return mu, song_query, "audio", "", ""
    except Exception as e:
        logger.warning("LOLIMI API Failed: %s", e)

    fallback_map = {
        "稻香": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3",
        "晴天": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-2.mp3",
        "周杰伦": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-3.mp3",
        "流行": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-4.mp3",
        "默认": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-5.mp3",
    }
    for key, u in fallback_map.items():
        if key != "默认" and key in song_query:
            return u, song_query, "audio", "", ""
    return fallback_map["默认"], song_query, "audio", "", ""

# -------------------------- 3. AI 绘画模块 --------------------------
def extract_image_prompt(task):
    """保留用户画画描述为主，去掉指令性前缀。"""
    t = task.strip()
    # 优先提取书名号/引号内的内容
    m = re.search(r"[《「]([^»」]+)[»」]", t)
    if m:
        return m.group(1).strip()[:1800]

    # 去掉礼貌用语
    t = re.sub(r"^(帮我|请|给我|我想看|我要)\s*", "", t)

    # 循环去掉动词前缀，但如果去掉后只剩「图片/图像/照片」等词，则保留原意
    verbs = r"^(画|生成|制作|绘制|出图|作图|弄|搞)(一张|一幅|一个|几张|下|点)?\s*"
    match = re.match(verbs, t)
    if match:
        potential_t = re.sub(verbs, "", t).strip()
        # 如果去掉动词后，剩下的词太短或者是纯泛指词，就不要乱删
        if len(potential_t) > 1 and potential_t not in ["图片", "图像", "照片", "头像", "图"]:
            t = potential_t

    # 去掉后缀，同样遵循保留逻辑
    suffixes = r"(的头像|的图片|的图像|的照片|的画|的风格)$"
    if re.search(suffixes, t):
        potential_t = re.sub(suffixes, "", t).strip()
        if len(potential_t) > 1:
            t = potential_t

    t = re.sub(r"\s+", " ", t).strip()
    if not t or t in ["图片", "图像", "照片", "头像", "图"]:
        t = "精美的风景画"  # 默认 Prompt
    return t[:1800]


def dashscope_submit_image(prompt):
    """提交阿里云百炼文生图任务，立即返回 task_id（不等待完成）。"""
    if not DASHSCOPE_API_KEY:
        return None
    submit_url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text2image/image-synthesis"
    headers = {
        "Authorization": f"Bearer {DASHSCOPE_API_KEY}",
        "Content-Type": "application/json",
        "X-DashScope-Async": "enable",
    }
    body = {
        "model": DASHSCOPE_IMAGE_MODEL,
        "input": {"prompt": prompt},
        "parameters": {"style": "<auto>", "size": IMAGE_SIZE, "n": 1},
    }
    try:
        resp = requests.post(submit_url, json=body, headers=headers, timeout=30)
        data = resp.json()
        if resp.status_code != 200:
            logger.error("Image submit HTTP %s: %s", resp.status_code, data)
            return None
        task_id = (data.get("output") or {}).get("task_id")
        if not task_id:
            logger.error("Image submit no task_id: %s", data)
            return None
        logger.info("Image task submitted: %s", task_id)
        return task_id
    except Exception as e:
        logger.error("dashscope_submit_image: %s", e)
        return None


def dashscope_poll_image(task_id):
    """查询单次任务状态，返回 (status, image_url)。
    status: 'pending' | 'succeeded' | 'failed',
    前端每隔 1 秒查一次是否生成完成
    """
    task_get = f"https://dashscope.aliyuncs.com/api/v1/tasks/{task_id}"
    headers_get = {"Authorization": f"Bearer {DASHSCOPE_API_KEY}"}
    try:
        tr = requests.get(task_get, headers=headers_get, timeout=15)
        td = tr.json()
        tout = td.get("output") or {}
        status = tout.get("task_status", "")
        if status == "SUCCEEDED":
            for item in tout.get("results") or []:
                u = item.get("url")
                if u:
                    return "succeeded", u
            return "failed", None
        if status in ("FAILED", "CANCELED", "UNKNOWN"):
            logger.error("Image task %s: %s", status, td)
            return "failed", None
        return "pending", None
    except Exception as e:
        logger.error("dashscope_poll_image: %s", e)
        return "failed", None


def dashscope_text_to_image(prompt):
    """同步版（用于降级兜底）：提交并轮询，直到完成或超时。"""
    if not DASHSCOPE_API_KEY:
        return None
    task_id = dashscope_submit_image(prompt)
    if not task_id:
        return None
    deadline = time.time() + IMAGE_TASK_TIMEOUT
    while time.time() < deadline:
        status, url = dashscope_poll_image(task_id)
        if status == "succeeded":
            logger.info("DashScope image ready: %s", task_id)
            return url
        if status == "failed":
            return None
        time.sleep(DASHSCOPE_TASK_POLL_INTERVAL)
    logger.error("Image task polling timeout: %s", task_id)
    return None


def generate_image(prompt):
    """优先百炼文生图，失败则尝试免费接口。"""
    url = dashscope_text_to_image(prompt)
    if url:
        return url

    try:
        url = f"https://api.vvhan.com/api/ai/photo?prompt={urllib.parse.quote(prompt)}"
        resp = requests.get(url, timeout=15)
        data = resp.json()
        if data.get("success") and data.get("url"):
            logger.info("Image via vvhan fallback")
            return data["url"]
    except Exception as e:
        logger.error("vvhan Image Error: %s", e)

    return "https://via.placeholder.com/400x400?text=AI+Image+Failed"

# -------------------------- 4. 通用对话模块 --------------------------
def split_text_chunks(text, chunk_size=650):
    text = re.sub(r"\s+", " ", text or "").strip()
    return [text[i:i + chunk_size] for i in range(0, len(text), chunk_size) if text[i:i + chunk_size].strip()]


def load_project_knowledge():
    """加载项目 README 作为轻量知识库，不引入额外向量库依赖。"""
    if session.KNOWLEDGE_SNIPPETS:
        return session.KNOWLEDGE_SNIPPETS

    candidates = [
        REPO_ROOT / "xiao-wen-ai" / "README.md",
        REPO_ROOT / "AI与前端项目汇总.md",
    ]
    snippets = []
    for path in candidates:
        if not path.exists():
            continue
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
            for idx, chunk in enumerate(split_text_chunks(content)):
                snippets.append({"source": path.name, "index": idx + 1, "text": chunk})
        except Exception as e:
            logger.warning("load knowledge failed: %s", e)
    session.KNOWLEDGE_SNIPPETS = snippets[:MAX_KNOWLEDGE_SNIPPETS]
    return session.KNOWLEDGE_SNIPPETS


def knowledge_search(query, limit=4):
    snippets = load_project_knowledge()
    tokens = [t for t in re.split(r"\W+", query.lower()) if len(t) >= 2]
    cn_terms = re.findall(r"[\u4e00-\u9fff]{2,}", query)
    terms = set(tokens + cn_terms)
    scored = []
    for item in snippets:
        text = item["text"].lower()
        score = sum(text.count(term.lower()) for term in terms)
        if score:
            scored.append((score, item))
    if not scored:
        scored = [(1, item) for item in snippets[:limit]]
    scored.sort(key=lambda x: x[0], reverse=True)
    return [item for _, item in scored[:limit]]


def ai_answer_with_knowledge(query):
    refs = knowledge_search(query)
    context = "\n\n".join(f"【{r['source']}#{r['index']}】{r['text']}" for r in refs)
    if not DASHSCOPE_API_KEY and not DEEPSEEK_API_KEY:
        brief = refs[0]["text"][:360] if refs else "知识库暂时为空。"
        return (
            "我检索到了项目知识库，但对话模型未配置（请在 .env 配置 DASHSCOPE_API_KEY 或 DEEPSEEK_API_KEY）。"
            f"相关内容摘要：{brief}",
            refs,
        )

    prompt = (
        "你是小文项目知识库助手。请只根据给定资料回答用户问题，"
        "如果资料不足就说明不足；回答简洁清晰，并在末尾列出参考来源。\n\n"
        + current_datetime_context_for_llm()
    )
    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": f"资料：\n{context}\n\n问题：{query}"},
    ]
    text = openai_compat_chat_fallback(messages)
    if text:
        return text, refs
    return "知识库问答暂时失败，请稍后重试。", refs


def is_knowledge_intent(task):
    return any(x in task for x in ["知识库", "根据项目", "项目文档", "README", "文档里", "资料里"])


def extract_image_url(task):
    m = re.search(r"https?://\S+", task)
    return m.group(0).strip("。,.，") if m else ""


def is_image_understanding_intent(task):
    return any(x in task for x in ["分析图片", "识别图片", "看图", "图片理解", "描述图片"])


def call_vision_model(image_content, prompt_text):
    if not DASHSCOPE_API_KEY:
        return MSG_VISION_NEED_DASHSCOPE
    try:
        headers = {"Authorization": f"Bearer {DASHSCOPE_API_KEY}", "Content-Type": "application/json"}
        body = {
            "model": DASHSCOPE_VL_MODEL,
            "messages": [
                {"role": "user", "content": [
                    image_content,
                    {"type": "text", "text": prompt_text},
                ]}
            ],
        }
        resp = requests.post(DASHSCOPE_CHAT_URL, json=body, headers=headers, timeout=CHAT_TIMEOUT)
        data = resp.json()
        if resp.status_code != 200:
            logger.error("vision model HTTP %s: %s", resp.status_code, data)
            return "图片理解失败：视觉模型接口返回异常。"
        choices = data.get("choices") or []
        content = (choices[0].get("message") or {}).get("content") if choices else ""
        return content.strip() if content else "没有识别到有效图片内容。"
    except Exception as e:
        logger.error("call_vision_model error: %s", e)
        return "图片理解失败，请稍后重试。"


def ai_understand_image(task):
    image_url = extract_image_url(task)
    if not image_url:
        return "请在指令里带上图片链接，例如：分析图片 https://example.com/a.jpg", None
    answer = call_vision_model(
        {"type": "image_url", "image_url": {"url": image_url}},
        "请用中文描述这张图片的主要内容、可能场景和可用作什么文案。",
    )
    return answer, image_url


# 摄像头人像：肤质 / 气色 / 生活方式线索（非医疗诊断）
FACE_WELLNESS_PROMPT = """你是友善的皮肤护理与形象顾问。用户上传了一张来自摄像头的正面人像截图。

【硬性约束】
- 这不是医学或精神科诊断；不得断言对方患有某种皮肤病或精神疾病。
- 涉及「精神状态」时，只能基于神态、眼神、气色等给出温和的主观印象与可能的生活方式线索，并明确标注仅供参考。
- 若画面中没有人脸、人脸过小或严重模糊逆光，请简短说明并建议重新对焦、正对光源后再拍。
- 语气温暖、鼓励，不用羞辱或夸大负面的表述。

【输出格式】请严格使用中文；每一小节先单独一行写标题（必须带「】」，便于阅读），空一行后再写正文：
【整体印象】
简短、积极的整体评价（2～4 句）。

【可见肤质与气色】
客观描述照片中可见的肤质与气色（不确定处用「可能」「似乎」）；避免定性为疾病名称。

【神态与状态（主观参考）】
从神态、眼神、面部放松度等推测疲劳感、情绪氛围或作息线索；段末必须写一句：以上内容仅为基于画面的主观联想，不能代替专业评估。

【护肤小知识】
结合观察给出 2～4 条通俗理论要点（例如：皮肤屏障与保湿、适度清洁、防晒、熬夜与暗沉的关系等），每条一两句话。

【护理与日常补救】
分两部分：（1）可操作的护肤步骤建议（晨/晚可区分）；（2）作息、饮水、防晒、卸妆等生活习惯提醒。

【何时建议就医】
若存在持续严重痤疮、红肿热痛、大面积脱皮或长期不愈等情况，提醒及时就诊皮肤科。

文末单独一行写：【免责】以上内容仅供日常护理与自我管理参考，不构成医疗、心理咨询或诊断建议。"""


def analyze_uploaded_image(file_storage, question="", kind=""):
    extras = {}
    if not file_storage:
        return "没有收到图片文件。", [], extras
    mime = file_storage.mimetype or ""
    if not mime.startswith("image/"):
        return "请上传 PNG、JPG、JPEG、WebP 等图片文件。", [], extras
    raw = file_storage.read()
    if not raw:
        return "图片文件为空，请重新上传。", [], extras
    if len(raw) > MAX_UPLOAD_IMAGE_BYTES:
        return f"图片太大，请上传小于 {MAX_UPLOAD_IMAGE_BYTES // 1024 // 1024}MB 的图片。", [], extras
    encoded = base64.b64encode(raw).decode("ascii")
    data_url = f"data:{mime};base64,{encoded}"

    kind_norm = (kind or "").strip().lower()
    if kind_norm == "face_wellness":
        prompt = FACE_WELLNESS_PROMPT
        q = (question or "").strip()
        if q:
            prompt = f"{prompt}\n\n【用户补充关注点】{q}"
        flow = workflow_steps(
            ("接收人像抓拍", f"{file_storage.filename or '摄像头截图'} · {mime}"),
            ("转为 Base64", "本地抓拍已送入视觉模型"),
            ("调用视觉模型", DASHSCOPE_VL_MODEL),
            ("生成洞察", "肤质护理与生活状态参考（非医疗诊断）"),
        )
        extras = {"mode": "vision_face", "modeLabel": "肤质与状态洞察"}
    else:
        prompt = (question or "").strip() or "请用中文分析这张图片：描述主体、场景、细节、可能用途，并给出一句适合配图的文案。"
        flow = workflow_steps(
            ("接收图片", f"{file_storage.filename or '本地图片'} · {mime}"),
            ("转为 Base64", "浏览器上传/拖拽/粘贴的本地图片已转为可识别数据"),
            ("调用视觉模型", DASHSCOPE_VL_MODEL),
            ("返回分析", "展示图片内容理解与文案建议"),
        )

    answer = call_vision_model({"type": "image_url", "image_url": {"url": data_url}}, prompt)
    return answer, flow, extras


def normalize_chat_history(history):
    """清洗前端传入的对话历史，只保留模型需要的 user / assistant 文本。"""
    return normalize_messages(history)[-MAX_CHAT_HISTORY_MESSAGES:]


def lunar_year_anchor_facts_for_llm(lunar_now_naive):
    """按当前日期所属农历年，列出若干农历月日→公历日期，避免模型心算农历生日等到错误公历。"""
    if ZhDate is None:
        return ""
    try:
        ly = ZhDate.from_datetime(lunar_now_naive).lunar_year
    except Exception:
        return ""
    # （农历月，农历日，中文简称）
    anchors = [
        (1, 1, "正月初一"),
        (3, 26, "三月二十六"),
        (5, 5, "五月初五"),
        (8, 15, "八月十五"),
    ]
    lines = [
        f"【农历日与公历对照（历法库换算，禁止心算或凭训练记忆换算）】"
        f"当前语境下的农历年为农历{ly}年（与用户口中的「今年阴历」一致时优先采用）。"
        f"用户问「农历某月某日是公历哪天」「阴历生日是哪天」等，必须使用下列公历日期：",
    ]
    for m, d, label in anchors:
        try:
            sol = ZhDate(ly, m, d).to_datetime()
            lines.append(f"农历{ly}年{label} → 公历{sol.year}年{sol.month}月{sol.day}日")
        except TypeError:
            continue
    return "\n".join(lines)


def current_datetime_context_for_llm():
    """注入「此刻」真实日期时间，避免模型编造「今天」或沿用过时年份；农历由 zhdate 换算写入提示。

    注意：ZhDate 内部使用 naive datetime，须传入 ``lunar_now = now.replace(tzinfo=None)``（本地墙钟），
    勿把 timezone-aware 与库内 naive 混算。
    """
    tz_name = LOCAL_TIMEZONE or "Asia/Shanghai"
    try:
        if ZoneInfo is not None:
            now = datetime.now(ZoneInfo(tz_name))
        else:
            now = datetime.now()
    except Exception:
        now = datetime.now()
        tz_name = "local"
    weekdays = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
    wd = weekdays[now.weekday()]
    parts = [
        f"【当前真实时间】{now.year}年{now.month}月{now.day}日 {wd} {now.strftime('%H:%M')}（时区：{tz_name}）。",
        "涉及「今天」「现在」「今年」「本周」「距离某日还有几天」等公历推算时，必须严格以上述日期为准，",
        "禁止使用训练数据里的过时年份或虚构「今天是几月几日」。",
    ]
    if ZhDate is not None:
        try:
            # zhdate 内部用 naive datetime 与春节日期做差；ZoneInfo Aware 会触发 naive/aware 相减错误
            lunar_now = now.replace(tzinfo=None) if now.tzinfo else now
            lunar = ZhDate.from_datetime(lunar_now)
            parts.append(
                f"【农历（服务端历法换算，回答「农历/阴历/初几/闰月」时必须与此完全一致，禁止自编）】{lunar.chinese()}；"
                f"简写：{lunar}。"
            )
            anchor_txt = lunar_year_anchor_facts_for_llm(lunar_now)
            if anchor_txt:
                parts.append("\n" + anchor_txt)
        except Exception as e:
            logger.warning("农历换算失败: %s", e)
            parts.append("【农历】换算异常，请勿编造农历日期；可只回答公历或说明无法给出农历。")
    else:
        parts.append("【农历】环境未安装 zhdate，请勿编造农历月日；可只回答公历。")
    return "".join(parts)


def remember_chat_turn(user_text, assistant_text):
    """服务端保存短期上下文，便于刷新前端后仍能追问上一轮内容。"""
    get_dialogue_manager().record_turn(user_text, assistant_text)


def ai_chat(query, history=None, location_hint=None, user_id=None, user_preferences=None):
    from logic.user_preferences import build_preference_prompt_addon

    dm = get_dialogue_manager()
    pref_addon = build_preference_prompt_addon(user_preferences)
    system_prompt = (
        "你是智能语音助手「小文」。用自然、口语化的中文回答，适合朗读；"
        "回答尽量控制在几句以内，除非用户明确要求长文（如详细讲故事）。"
        "用户可能会问各地美食、讲笑话、讲故事、闲聊等，请友好作答。\n\n"
        + current_datetime_context_for_llm()
    )
    state_hint = dm.state_hint_for_system()
    if state_hint:
        system_prompt += "\n\n" + state_hint
    if pref_addon:
        system_prompt += "\n\n【用户偏好】\n" + pref_addon
    if location_hint:
        system_prompt += "\n\n" + str(location_hint).strip()
    if user_id:
        try:
            prefs = load_user_preferences(int(user_id))
            personalize = build_personalized_system_prompt(prefs)
            if personalize:
                system_prompt += personalize
        except Exception as e:
            logger.warning("偏好注入失败(user_id=%s): %s", user_id, e)
    messages = [
        {"role": "system", "content": system_prompt},
        *dm.build_context_messages(history),
        {"role": "user", "content": query},
    ]

    text = openai_compat_chat_fallback(messages)
    if text:
        return text

    try:
        url = f"https://api.lolimi.cn/API/chatGPT/q?msg={urllib.parse.quote(query)}"
        resp = requests.get(url, timeout=REQUEST_TIMEOUT)
        data = resp.json()
        if data.get('code') == 200 and data.get('data'):
            return data['data']
    except Exception as e:
        logger.error(f"Chat API Error: {e}")
    return MSG_LLM_NOT_CONFIGURED

def translate_selected_text(text, target_lang):
    """将选中文字翻译为中文或英文，保留原意并只返回译文。"""
    target_name = "英文" if target_lang == "en" else "中文"
    messages = [
        {
            "role": "system",
            "content": f"你是专业翻译助手。请把用户提供的文本翻译成{target_name}，只输出译文，不要解释。",
        },
        {"role": "user", "content": text},
    ]
    out = openai_compat_chat_fallback(messages, temperature=0.2)
    if out:
        return out
    if not DASHSCOPE_API_KEY and not DEEPSEEK_API_KEY:
        return MSG_TRANSLATE_NOT_CONFIGURED
    return "翻译失败：模型服务暂时不可用。"


# -------------------------- 5. 本地应用启动模块 --------------------------
def extract_app_name(task):
    """从「打开记事本 / 启动计算器」等自然语言中提取应用名称。"""
    t = task.strip().lower()
    for prefix in ["帮我打开", "请打开", "打开", "启动", "运行", "开启", "帮我启动"]:
        if t.startswith(prefix):
            return t[len(prefix):].strip()
    return t.strip()


def supported_app_message():
    """返回当前可打开应用列表说明。"""
    app_names = [
        "记事本", "计算器", "画图", "截图工具", "命令行", "终端",
        "文件管理器", "Edge 浏览器", "Chrome 浏览器", "微信", "QQ", "网易云", "抖音", "VSCode",
    ]
    extra = ""
    ua = load_user_apps()
    if ua:
        extra = "\n\n你在本机添加的白名单应用：" + "、".join(sorted(ua.keys())) + "。"
    return (
        "我目前可以帮你打开这些电脑应用：\n"
        f"{ '、'.join(app_names) }。{extra}\n"
        "你可以这样说：打开记事本、启动计算器、打开文件管理器、打开 VSCode、打开抖音（本机客户端）；"
        "需要抖音网页版可说「打开抖音网页」。"
        "在首页还可点「浏览电脑添加应用」，选好程序并起名后，即可说「打开【你起的名字】」。"
    )


def is_app_list_query(task):
    """判断用户是否在问「能帮我打开什么 / 支持哪些应用」等清单问题，而非「打开某某」具体指令。"""
    t = task.strip().lower()
    # 强匹配：口语里常不带「软件」「应用」二字，不能只依赖后者
    strong = (
        "可以帮我打开什么",
        "能帮我打开什么",
        "你可以帮我打开什么",
        "你都可以帮我打开什么",
        "你都会帮我打开什么",
        "帮我打开什么",
        "帮我打开哪些",
        "帮我启动什么",
        "打开什么应用",
        "打开什么软件",
        "打开什么程序",
        "打开啥应用",
        "打开啥软件",
        "能打开什么",
        "可以打开什么",
        "都能打开什么",
        "都可以打开什么",
        "都会打开什么",
        "打开哪些应用",
        "打开哪些软件",
        "打开哪些程序",
        "能打开哪些",
        "可以打开哪些",
        "支持打开什么",
        "支持打开哪些",
        "会打开什么",
        "可以启动什么",
        "能启动什么",
        "可以打开啥",
        "能打开啥",
        "哪些应用能打开",
        "哪些软件能打开",
        "能帮我打开啥",
    )
    if any(p in t for p in strong):
        return True
    # 弱匹配：泛问 + 明确提到应用类名词
    if any(x in t for x in ["可以打开什么", "能打开什么", "支持打开什么", "可以启动什么", "能启动什么"]):
        if any(x in t for x in ["应用", "软件", "程序", "app"]):
            return True
    return False


def _registry_user_desktop_dir():
    """注册表里的真实桌面路径（用户把桌面挪到 D: 等时，仅扫 ~/Desktop 会漏掉）。"""
    if os.name != "nt":
        return None
    import winreg

    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders",
        )
        try:
            val, _ = winreg.QueryValueEx(key, "Desktop")
        finally:
            key.Close()
        if not isinstance(val, str) or not val.strip():
            return None
        p = Path(os.path.expandvars(val.strip().strip('"')))
        return p if p.is_dir() else None
    except OSError:
        return None


def find_windows_shortcut(keyword):
    """在当前用户桌面、公共桌面和开始菜单中查找应用快捷方式。"""
    home = Path.home()
    search_dirs = []
    reg_desk = _registry_user_desktop_dir()
    if reg_desk is not None:
        search_dirs.append(reg_desk)
    search_dirs.extend(
        [
            home / "Desktop",
            home / "桌面",
            home / "OneDrive" / "Desktop",
            home / "OneDrive" / "桌面",
            Path(os.environ.get("PUBLIC", "C:/Users/Public")) / "Desktop",
            Path(os.environ.get("PUBLIC", "C:/Users/Public")) / "公共桌面",
            Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs",
            Path(os.environ.get("PROGRAMDATA", "C:/ProgramData")) / "Microsoft" / "Windows" / "Start Menu" / "Programs",
        ]
    )
    seen = set()
    unique_dirs = []
    for directory in search_dirs:
        if directory is None:
            continue
        s = str(directory).strip()
        if not s:
            continue
        if not directory.exists():
            continue
        try:
            key = str(directory.resolve())
        except OSError:
            key = s
        if key not in seen:
            seen.add(key)
            unique_dirs.append(directory)

    keyword_lower = keyword.lower()
    for directory in unique_dirs:
        try:
            for shortcut in directory.rglob("*.lnk"):
                try:
                    if keyword_lower in shortcut.stem.lower():
                        return shortcut
                except OSError:
                    continue
        except OSError:
            continue
    return None


def launch_shortcut(keyword):
    """打开桌面或开始菜单中的快捷方式。"""
    shortcut = find_windows_shortcut(keyword)
    if not shortcut:
        return False
    try:
        os.startfile(str(shortcut))
        return True
    except OSError as e:
        logger.warning("startfile shortcut failed %s: %s", shortcut, e)
        return False


def _start_exe_best_effort(exe_path):
    """启动白名单内的 .exe：优先系统关联，失败再直接起进程。"""
    p = str(exe_path)
    try:
        os.startfile(p)
        return True
    except OSError:
        try:
            subprocess.Popen([p], shell=False)
            return True
        except OSError as e:
            logger.warning("Popen exe failed %s: %s", p, e)
            return False


def launch_local_app(task):
    """打开本机白名单应用。返回 (是否成功, 提示信息)。"""
    app_name = extract_app_name(task)
    if not app_name:
        return False, "请告诉我要打开哪个应用，例如：打开记事本、打开计算器。"

    matched_name = None
    command = None
    for name, cmd in merge_launchers().items():
        if name.lower() in app_name or app_name in name.lower():
            matched_name = name
            command = cmd
            break

    if not command:
        supported = "、".join(sorted(merge_launchers().keys()))
        return False, f"暂时不支持打开「{app_name}」。当前支持：{supported}。"

    try:
        if command.startswith("shortcut:"):
            keyword = command.split(":", 1)[1]
            if launch_shortcut(keyword):
                return True, f"已为你打开：{matched_name}"
            return False, f"没有在桌面或开始菜单找到「{keyword}」快捷方式，请确认快捷方式名称包含“{keyword}”。"

        if command.startswith("resolve:"):
            kind = command.split(":", 1)[1].strip()
            kind_lower = kind.lower()
            if kind_lower == "douyin":
                try:
                    exe = resolve_douyin_exe()
                    if exe is not None and _start_exe_best_effort(exe):
                        disp = "抖音" if matched_name == "douyin" else matched_name
                        return True, f"已为你打开：{disp}"
                    for sk in ("抖音", "Douyin", "douyin", "抖音短视频"):
                        if launch_shortcut(sk):
                            disp = "抖音" if matched_name == "douyin" else matched_name
                            return True, f"已为你打开：{disp}"
                    return False, (
                        "未找到本机「抖音」客户端（已查 PATH、注册表 App Paths/卸载信息、ByteDance 目录、桌面/开始菜单）。"
                        "可在 backend/.env 设置 DOUYIN_EXE_PATH=D:\\\\1\\\\douyin\\\\douyin.exe 后重启后端。"
                        "需要网页版请说：打开抖音网页。"
                    )
                except Exception as e:
                    logger.exception("打开抖音时异常: %s", e)
                    return False, (
                        "启动抖音时发生内部错误（详情已写入后端日志）。"
                        "请先在 backend/.env 设置 DOUYIN_EXE_PATH 为你的 douyin.exe 完整路径并重启后端后再试。"
                    )
            if kind_lower == "netease":
                exe = resolve_netease_cloud_exe()
                if exe is not None and _start_exe_best_effort(exe):
                    return True, f"已为你打开：{matched_name}"
                for sk in ("网易云音乐", "CloudMusic", "cloudmusic", "网易云"):
                    if launch_shortcut(sk):
                        return True, f"已为你打开：{matched_name}"
                try:
                    subprocess.Popen("start cloudmusic", shell=True)
                    return True, f"已为你打开：{matched_name}"
                except OSError as e:
                    logger.warning("netease start cloudmusic failed: %s", e)
                return False, (
                    "未能启动网易云音乐：未在默认安装路径找到程序，且开始菜单中无匹配快捷方式。"
                    "请确认已安装 PC 客户端，或使用官网安装包修复安装。"
                )
            if kind_lower in ("wechat", "qq"):
                exe = resolve_tencent_wechat_exe() if kind_lower == "wechat" else resolve_tencent_qq_exe()
                if exe is not None and _start_exe_best_effort(exe):
                    disp = "QQ" if matched_name == "qq" else matched_name
                    return True, f"已为你打开：{disp}"
                if kind_lower == "wechat":
                    shortcut_try = ("微信", "WeChat", "wechat")
                else:
                    shortcut_try = ("QQ", "qq")
                for sk in shortcut_try:
                    if launch_shortcut(sk):
                        disp = "QQ" if matched_name == "qq" else matched_name
                        return True, f"已为你打开：{disp}"
                label = "微信" if kind_lower == "wechat" else "QQ"
                reinstall = "或重装微信到默认目录后再试。" if kind_lower == "wechat" else "或重装 QQ 到默认目录后再试。"
                return False, (
                    f"未找到「{label}」可用的安装路径或快捷方式（已查注册表、Program Files、开始菜单）。"
                    f"若本机已安装，请确认开始菜单里有名称含「{label}」或「WeChat」的快捷方式；"
                    f"{reinstall}"
                )
            return False, f"内部配置异常：未知的 resolve 类型「{kind}」。"

        if command.startswith("exe:"):
            exe_p = command[4:].strip()
            pp = Path(exe_p)
            if pp.is_file() and _start_exe_best_effort(pp):
                return True, f"已为你打开：{matched_name}"
            return False, (
                f"「{matched_name}」的程序文件已不存在或无法启动。"
                "请到小文首页重新用「浏览电脑添加应用」选择该程序。"
            )

        # Windows 内置 start 需要 shell=True；白名单固定命令，避免执行用户输入。
        subprocess.Popen(command, shell=True)
        disp = "QQ" if matched_name == "qq" else matched_name
        return True, f"已为你打开：{disp}"
    except Exception as e:
        logger.exception("Launch app failed: %s", e)
        return False, f"打开「{matched_name}」失败，可能是应用未安装或不在系统 PATH 中。"


def wants_douyin_web_open(task: str) -> bool:
    """用户明确要网页/在线版抖音时返回 True；仅「打开抖音」应优先本机客户端。"""
    if "抖音" not in task and "douyin" not in task.lower():
        return False
    t = task.strip().lower()
    if "douyin.com" in t or "www.douyin" in t:
        return True
    if any(p in t for p in ("网页版", "抖音网页", "抖音网站", "网页抖音", "抖音官网")):
        return True
    if ("网页" in t or "网站" in t) and ("抖音" in task or "douyin" in t):
        return True
    if "浏览器" in t and ("抖音" in task or "douyin" in t):
        return True
    return False


# -------------------------- 6. 模拟世界对话模块 --------------------------
def detect_world_theme(task):
    if any(x in task for x in ["修仙", "仙侠", "玄幻"]):
        return "修仙"
    if any(x in task for x in ["末日", "废土", "丧尸"]):
        return "末日"
    if any(x in task for x in ["奇幻", "魔法", "异世界"]):
        return "奇幻"
    return random.choice(list(WORLD_THEMES.keys()))


def is_world_exit_intent(task):
    return any(x in task.strip() for x in [
        "退出模拟", "结束模拟", "离开模拟", "退出世界", "结束世界", "离开世界",
        "退出生存", "结束生存", "停止模拟", "回到小文", "返回助手", "退出修仙",
    ])


def is_world_create_intent(task):
    t = task.strip()
    create_hit = any(x in t for x in ["世界", "模拟", "生存", "出生", "开局", "角色扮演", "冒险"])
    theme_hit = any(x in t for x in ["修仙", "仙侠", "玄幻", "末日", "废土", "丧尸", "奇幻", "魔法", "异世界"])
    return (create_hit and theme_hit) or any(x in t for x in ["帮我出生在那里", "出生在那里", "我想在这里生存"])


def is_image_lookup_intent(task):
    """用户想在网上找实物图（与 AI 文生图区分）。例如：能找出图片吗、想看看长什么样。"""
    if extract_image_url(task):
        return False
    t = task.strip().lower()
    if any(x in t for x in ["生成图片", "生成一张", "画一张", "给我画", "ai画", "文生图"]):
        return False
    keys = [
        "找出图片", "找图片", "搜图片", "搜图", "图片搜索", "网上图片",
        "想看看图", "想看图片", "看一下图片", "看图片", "找张图", "找几张图",
        "有图片吗", "有没有图", "有没有照片", "实物图", "长什么样", "什么样子", "长啥样",
        "配个图", "配图看看", "搜一下图",
    ]
    if any(k in t for k in keys):
        return True
    if any(k in t for k in ["想看看", "想看一下", "看一下", "看看"]) and any(
        k in t for k in ["图", "照片", "啥样", "什么样", "样子"]
    ):
        return True
    return False


def extract_entity_from_assistant_reply(content):
    """从上一轮闲聊回复里抽出菜名/事物名（**粗体**、《》、“试试××”等）。"""
    if not content:
        return None
    text = content.strip()
    for pattern in (
        r"\*\*([^*]{2,40})\*\*",
        r"《([^》]{2,40})》",
        r"「([^」]{2,40})」",
    ):
        found = re.findall(pattern, text)
        if found:
            cand = found[-1].strip()
            if len(cand) >= 2:
                return cand[:40]
    m = re.search(
        r"(?:那)?(?:试试|推荐|尝尝|不如|点一份|来一份|可以(?:试试)?)[:：]?\s*"
        r"([^，,。！？\n*《》*「」]{2,30})",
        text,
    )
    if m:
        return m.group(1).strip()[:40]
    return None


def merge_chat_history_for_lookup(chat_history):
    """优先用前端传来的 history，否则用服务端 DialogueManager 存储。"""
    return get_dialogue_manager().resolve_history(chat_history)


def _weather_resolve_from_gps(client_location, task: str) -> tuple[str, bool, str | None, dict | None] | None:
    """当前句未写城市时，用浏览器经纬度逆地理；成功返回四元组，否则 None。"""
    if not (client_location and isinstance(client_location, dict) and "天气" in task):
        return None
    lng = client_location.get("lng") or client_location.get("longitude")
    lat = client_location.get("lat") or client_location.get("latitude")
    try:
        lng_f = float(lng)
        lat_f = float(lat)
    except (TypeError, ValueError):
        return None
    if not (-180 <= lng_f <= 180 and -90 <= lat_f <= 90):
        return None
    geo = amap_regeocode_lng_lat(lng_f, lat_f)
    if not geo or not geo.get("adcode"):
        return None
    key = (geo.get("card_title") or geo.get("region_label") or geo.get("display_city") or "当地")[:40]
    return key, True, geo["adcode"], geo


def resolve_weather_city(task: str, chat_history=None, client_location=None) -> tuple[str, bool, str | None, dict | None]:
    """解析要查天气的城市展示名；第二项 True 表示由对话上文或定位推断；第三项 adcode；第四项逆地理详情（仅定位）。
    当前句未点名城市时，**优先浏览器定位**，避免历史里小文提到「北京」等覆盖真实位置。"""
    inline = infer_city_from_single_task(task)
    if inline:
        return inline, False, None, None
    cand = extract_city_candidate(task)
    if cand:
        return cand, False, None, None

    gps_hit = _weather_resolve_from_gps(client_location, task)
    if gps_hit:
        return gps_hit

    hist = merge_chat_history_for_lookup(chat_history)
    inferred = infer_city_from_chat_history(hist, include_assistant=False)
    if inferred:
        return inferred, True, None, None

    return "北京", False, None, None


def extract_city(task):
    """兼容旧调用：无对话上下文时解析城市。"""
    city, _, _, _ = resolve_weather_city(task, None, None)
    return city


def extract_image_search_query(task, chat_history):
    """结合当前指令与上一轮小文回复，得到图片搜索关键词。"""
    history = merge_chat_history_for_lookup(chat_history)
    last_asst = None
    for m in reversed(history):
        if m.get("role") == "assistant":
            last_asst = m.get("content") or ""
            break
    q = extract_entity_from_assistant_reply(last_asst)
    if q:
        return q
    t = task.strip()
    m = re.match(
        r"^([\u4e00-\u9fa5A-Za-z0-9·\s]{2,32})(?:的)?(?:图片|照片|图)\s*$",
        t,
    )
    if m:
        return re.sub(r"\s+", "", m.group(1).strip())[:40]
    stripped = t
    for phrase in (
        "能找出图片吗",
        "找出图片",
        "找图片",
        "搜图片",
        "搜图",
        "我想看看",
        "想看看",
        "想看一下",
        "看一下",
        "有图片吗",
        "有没有图片",
        "帮我找",
        "请帮我",
        "帮我搜",
        "一下",
        "吗",
        "呢",
        "哈哈",
        "的",
    ):
        stripped = stripped.replace(phrase, "")
    stripped = re.sub(r"[\s，,。.!！?？]+", "", stripped)
    if 4 <= len(stripped) <= 28:
        return stripped
    return None


def is_image_intent(task):
    t = task.strip()
    if is_world_create_intent(t):
        return False
    if is_image_lookup_intent(t):
        return False
    image_words = ["画", "绘", "出图", "作图", "图片", "照片", "图像", "头像"]
    generate_image_words = ["生成图片", "生成一张", "生成一幅", "生成照片", "生成头像", "生成图像"]
    return any(x in t for x in image_words) or any(x in t for x in generate_image_words)


def current_mode_payload(extra=None):
    if session.WORLD_STATE is None:
        payload = {"mode": "normal", "modeLabel": "普通助手"}
    else:
        payload = {
            "mode": "world",
            "modeLabel": f"{session.WORLD_STATE['theme']}世界中",
            "worldState": public_world_state(session.WORLD_STATE),
            "quickActions": ["查看状态", "继续探索", "采集资源", "休息", "退出模拟"],
        }
    if extra:
        payload.update(extra)
    return payload


def create_world(task):
    theme = detect_world_theme(task)
    data = WORLD_THEMES[theme]
    seed = random.randint(100000, 999999)
    rng = random.Random(seed)
    return {
        "theme": theme,
        "seed": seed,
        "core": rng.choice(data["cores"]),
        "location": rng.choice(data["birthplaces"]),
        "day": 1,
        "time": "清晨",
        "hp": 100,
        "energy": 80,
        "hunger": 28,
        "safety": rng.randint(42, 72),
        "luck": rng.randint(8, 28),
        "hostility": rng.randint(10, 35),
        "realm": "凡人" if theme == "修仙" else "新手幸存者",
        "inventory": rng.sample(data["resources"], 2),
        "scene": rng.choice(data["scenes"]),
        "last_action": "出生",
    }


def public_world_state(state):
    return {
        "theme": state["theme"],
        "seed": state["seed"],
        "core": state["core"],
        "day": state["day"],
        "time": state["time"],
        "hp": state["hp"],
        "energy": state["energy"],
        "hunger": state["hunger"],
        "safety": state["safety"],
        "luck": state["luck"],
        "hostility": state["hostility"],
        "realm": state["realm"],
        "location": state["location"],
        "inventory": state["inventory"],
    }


def _world_lexicon(theme: str) -> dict:
    if theme == "修仙":
        return {
            "divider": "──────── 身念札记 ────────",
            "time": "【时日】",
            "vitals": "【三元】",
            "hp_l": "生机",
            "en_l": "气机",
            "hun_l": "腹虚",
            "world": "【天地轴】",
            "seed_l": "灵机种子",
            "core_l": "世潮",
            "self": "【根骨名相】",
            "safe_l": "安危",
            "luck_l": "机缘",
            "host_l": "戾影",
            "loc": "【足迹】",
            "bag": "【行囊】",
            "empty_bag": "（空空如也）",
        }
    if theme == "末日":
        return {
            "divider": "──────── 体征记录 ────────",
            "time": "【日程】",
            "vitals": "【体征】",
            "hp_l": "生命",
            "en_l": "体力",
            "hun_l": "饥饿",
            "world": "【废土档案】",
            "seed_l": "局势编号",
            "core_l": "主轴",
            "self": "【幸存体征】",
            "safe_l": "安危",
            "luck_l": "运气",
            "host_l": "威胁",
            "loc": "【坐标】",
            "bag": "【背包】",
            "empty_bag": "（什么也没有）",
        }
    return {
        "divider": "──────── 旅途札记 ────────",
        "time": "【时日】",
        "vitals": "【状态】",
        "hp_l": "生命",
        "en_l": "精力",
        "hun_l": "饥渴",
        "world": "【世界】",
        "seed_l": "命运种子",
        "core_l": "主轴",
        "self": "【身份】",
        "safe_l": "安危",
        "luck_l": "机缘",
        "host_l": "敌意",
        "loc": "【位置】",
        "bag": "【行囊】",
        "empty_bag": "（空空如也）",
    }


def world_status_text(state):
    theme = state["theme"]
    L = _world_lexicon(theme)
    inv = "、".join(state["inventory"]) if state["inventory"] else L["empty_bag"]
    return (
        f"{L['divider']}\n"
        f"{L['time']}　第 {state['day']} 天 · {state['time']}\n"
        f"{L['vitals']}　{L['hp_l']} {state['hp']}　·　{L['en_l']} {state['energy']}　·　{L['hun_l']} {state['hunger']}\n"
        f"{L['world']}　{theme}　·　{L['seed_l']} {state['seed']}　·　{L['core_l']} {state['core']}\n"
        f"{L['self']}　{state['realm']}　·　{L['safe_l']} {state['safety']}　·　{L['luck_l']} {state['luck']}　·　{L['host_l']} {state['hostility']}\n"
        f"{L['loc']}　{state['location']}\n"
        f"{L['bag']}　{inv}"
    )


def world_suggestions(state):
    base = ["继续探索", "查看状态", "退出模拟"]
    if state["hunger"] >= 60:
        return ["找点吃的", "休息恢复", "查看背包"]
    if state["energy"] <= 30:
        return ["休息", "查看状态", "谨慎观察附近"]
    if state["theme"] == "修仙":
        return ["修炼", "探索附近", "采集资源"]
    return base


def _intro_atmosphere(theme: str, state: dict) -> str:
    loc, core, seed = state["location"], state["core"], state["seed"]
    sc = state.get("scene", loc)
    if theme == "修仙":
        return (
            f"一缕若有若无的清气在「{loc}」盘旋，像有人在很远的地方敲了一下磬。"
            f"你吸气时，仿佛能感到这片乾坤此刻被「{core}」轻轻牵着脉动；"
            f"冥冥中编号 {seed} 的世界种子在识海里微微发烫——故事从这里落笔。"
            f"眼前景物沉淀为「{sc}」该有的轮廓：风声、草木与远处断续的人语，都在等你迈出下一步。"
        )
    if theme == "末日":
        return (
            f"灰尘与铁锈的气味缠在「{loc}」的墙角，远处警报残响若有若无。"
            f"这片废土的主轴是「{core}」，局势编号 {seed} 像一枚冷冷打在手臂上的烙印。"
            f"你立足之处——「{sc}」——安静得过分，安静里却藏着下一声嘶吼。"
        )
    return (
        f"银辉或烽火在天际交界徘徊，「{loc}」的石缝间渗出古老的潮气。"
        f"传说与阴谋绕着「{core}」旋转，命运种子 {seed} 在你掌心隐隐共振。"
        f"眼前的「{sc}」像一页尚未写满的地图，等你用脚步填满。"
    )


def render_world_intro(state):
    suggestions = "、".join(world_suggestions(state))
    inv = "、".join(state["inventory"])
    body = _intro_atmosphere(state["theme"], state)
    return (
        f"已为你生成一个【{state['theme']}】文字模拟世界。\n\n"
        f"{body}\n\n"
        f"【档案摘要】世界编号：{state['seed']}　｜　主轴：{state['core']}\n"
        f"【出生地点】{state['location']}　｜　【当前场景】{state['scene']}\n"
        f"【初始资源】{inv}\n\n"
        f"模拟世界已锁定：后续对话都发生在此界，直至你输入「退出模拟」。\n\n"
        f"{world_status_text(state)}\n\n"
        f"【行动建议】{suggestions}"
    )


def world_fallback_narrative(theme: str, action: str, event: str, changes: list[str], state: dict) -> str:
    """LLM 不可用时，用主题化散文写本轮际遇（不含底部札记面板）。"""
    loc = state["location"]
    ch0 = changes[0] if changes else ""

    def _join_rest():
        if len(changes) <= 1:
            return ""
        return "\n\n" + "\n\n".join(changes[1:])

    if action == "story_crisis":
        hook = random.choice(
            [
                "生死像被人猛地翻了一页，喧哗与寂静同时灌进耳膜，你觉得自己在坠落，又被什么东西拽住。",
                "肋骨里泛起钝痛，视线边缘发白，世界却在此刻格外澄澈——像暴风雨眼里那一瞬的空白。",
            ]
        )
        return hook + "\n\n" + "\n\n".join(changes) if changes else hook
    if action == "story_hurt":
        hook = "痛楚来得结实而不讲理，像有人把现实狠狠拍在你胸口。"
        return hook + "\n\n" + "\n\n".join(changes) if changes else hook
    if action == "story_awaken":
        hook = "识海里像是擦亮了一根火柴，昏暗处忽然有了轮廓。"
        return hook + "\n\n" + "\n\n".join(changes) if changes else hook

    if theme == "修仙":
        if action == "explore":
            o = random.choice(
                [
                    "山岚贴着脊背流过，远处钟磬若有若无，像云端有人轻轻咳了一声。",
                    "脚下的苔痕深浅不一，灵气在石板缝里游走，凉得像一条细细的蛇。",
                    "你越过一段碎石坡，袖口红绳被风掀起，鼻端尽是草木与淡淡血腥搅在一起的气息。",
                ]
            )
            weave = (
                f"{o}\n\n"
                f"半途乾坤似轻轻一拧——{event}——雨意或灵机擦过你鬓角，经脉也跟着微微一跳。\n\n"
                f"待心神落定，路途已把你领到「{loc}」：这里的山势、风声与远处人语，都和先前那一截截然不同。"
            )
            return weave + _join_rest()
        if action == "observe":
            return (
                random.choice(
                    [
                        "你屏息而立，把呼吸放得极轻，像怕惊动空气里的灵机。",
                        "你没有急着迈步，先让五感沉下去：泥土潮气、远处兽吼、偶尔掠过的剑光残影。",
                    ]
                )
                + f"\n\n天地间掠过一丝异样——{event}——像是这片天地在提醒你：故事仍在推进。\n\n"
                + (ch0 if ch0 else "你把地形、气味与远处的动静一一记在心里。")
                + _join_rest()
            )
        if action == "cultivate":
            return (
                f"你盘膝坐下，引气归元，识海里杂念如潮汐退去。\n\n"
                f"吐纳之间，外界忽然浮起一抹征兆——{event}——像有人在很远的地方与你同频呼吸。\n\n"
                + ch0
                + _join_rest()
            )
        if action == "rest":
            return (
                "你找到一处背风的角落，把疲惫的身体交给大地，泥土的凉意从脊背渗进来。\n\n"
                f"半梦半醒间，天意似轻轻一掠——{event}——让你心头既是警醒，又稍稍松弛。\n\n"
                + ch0
                + _join_rest()
            )
        if action == "gather":
            return (
                f"你俯身细察每一处可疑的凹陷与草根翻起的痕迹，掌心沾满湿泥与碎叶。\n\n"
                f"就在指尖将要收回的刹那——{event}——仿佛天地顺手推了你一把。\n\n"
                + ch0
                + _join_rest()
            )
        if action == "eat":
            return (
                "你按捺住腹中的空虚，从行囊里摸索可以入口的东西。\n\n"
                f"咀嚼声里，外界掠过一丝不协调的动静——{event}——提醒你这片世界并不温柔。\n\n"
                + ch0
                + _join_rest()
            )
        if action == "fight":
            return (
                "风声陡紧，你合身扑上，气血在经脉里撞出炽热的回响。\n\n"
                f"交锋的间隙，像有天象余波扫过——{event}——让人分不清是劫数还是转机。\n\n"
                + ch0
                + _join_rest()
            )
        if action == "trade":
            return (
                "人声与货物混杂，你在摊位与目光之间来回试探，讨价还价的底气藏在袖里。\n\n"
                f"市集中忽然起了一阵骚动——{event}——让你下意识攥紧了随身之物。\n\n"
                + ch0
                + _join_rest()
            )
        if action == "survive_day":
            return (
                "你把昼夜当成一道窄门，每一步都踩在刀锋般的寂静里。\n\n"
                f"日出之前，天地似乎有意折腾行人——{event}——你在疲惫里把它嚼碎吞下。\n\n"
                + ch0
                + _join_rest()
            )

    if theme == "末日":
        if action == "explore":
            return (
                random.choice(
                    [
                        "混凝土裂缝里渗出霉味，你贴着墙根前进，耳朵捕捉每一丝异常。",
                        "废弃招牌在风中摇晃，铁锈刮擦声像某种动物的低笑。",
                    ]
                )
                + f"\n\n废墟上空掠过一阵不安——{event}——你脖颈后的汗毛齐齐竖起。\n\n"
                f"你绕开可疑的阴影，最终把自己挪到「{loc}」：这里的寂静与危险浓度，都与刚才不同。"
                + _join_rest()
            )

    if action in ("explore", "observe"):
        return (
            f"风换了方向，脚下的质感也不再相同。\n\n"
            f"半途像是有人在天幕上敲了一下——{event}——余韵落在你的肩膀上。\n\n"
            + (ch0 if ch0 else f"你打量着「{loc}」，把可疑之处默默记下。")
            + _join_rest()
        )

    lines = [f"命运掠过一丝涟漪——{event}——像在给这趟旅途盖章。"]
    if ch0:
        lines.append(ch0)
    lines.extend(changes[1:])
    return "\n\n".join(lines)


def advance_world_time(state):
    order = ["清晨", "上午", "正午", "下午", "傍晚", "深夜"]
    idx = order.index(state["time"]) if state["time"] in order else 0
    next_idx = (idx + 1) % len(order)
    state["time"] = order[next_idx]
    if next_idx == 0:
        state["day"] += 1


def clamp_world_state(state):
    for key in ["hp", "energy", "safety", "luck", "hostility"]:
        state[key] = max(0, min(100, state[key]))
    state["hunger"] = max(0, min(100, state["hunger"]))


def classify_world_action(task):
    """根据关键词路由行动；长叙述优先识别「剧情逆境/觉醒」，避免「被打」误匹配成主动「战斗」。"""
    t = task.strip()
    # 长段落网文体：多句号 + 修仙意象词叠出现时，按「绝境+转机」结算（便于承接千字叙事）
    if (
        len(t) >= 140
        and ("。" in t or "\n" in t)
        and sum(1 for k in ("血", "玉", "佩", "昏", "裂", "传承", "肋骨", "灵气", "修仙", "秘境", "光柱") if k in t) >= 3
    ):
        return "story_crisis"
    if any(x in t for x in ["状态", "背包", "我现在", "当前情况", "情况", "属性"]):
        return "status"
    if any(x in t for x in ["吃", "食物", "找点吃", "找吃的", "吃东西"]):
        return "eat"
    if any(x in t for x in ["采集", "搜索", "找资源", "捡", "收集", "搜山洞", "搜附近"]):
        return "gather"
    if any(x in t for x in ["修炼", "打坐", "突破", "学旧丹方", "学丹方", "研究玉简"]):
        return "cultivate"
    if any(x in t for x in ["休息", "睡", "恢复", "苟", "躲起来"]):
        return "rest"

    hurt_like = any(
        x in t
        for x in [
            "被打", "挨揍", "被揍", "挨打", "打个半死", "半死", "重伤", "遇袭", "遭殴", "被围", "身受",
            "肋骨", "血沫", "濒死", "昏沉", "青石", "拳脚",
        ]
    )
    crisis_like = hurt_like or ("冲突" in t and any(x in t for x in ["受伤", "不敌", "吃亏", "惨败"]))
    awaken_like = any(x in t for x in ["玉佩", "古玉", "玉符", "玉简", "信物", "随身"]) and any(
        x in t for x in ["激活", "觉醒", "发光", "认主", "裂开", "发烫", "异动", "碎裂", "光粒", "传承"]
    )
    if crisis_like and awaken_like:
        return "story_crisis"
    if awaken_like and not hurt_like:
        return "story_awaken"
    if hurt_like or crisis_like:
        return "story_hurt"

    if any(x in t for x in ["战斗", "攻击", "迎战", "猎杀", "开打", "切磋", "出手", "揍人", "杀敌"]):
        return "fight"
    if "打" in t and all(x not in t for x in ("被打", "挨揍", "被揍", "挨打", "揍我", "打我")):
        return "fight"

    if any(x in t for x in ["交易", "卖", "买", "去宗门", "宗门", "小镇", "集市"]):
        return "trade"
    if any(x in t for x in ["生存", "过一天", "一天"]):
        return "survive_day"
    if any(x in t for x in ["继续", "附近", "向北", "向南", "向东", "向西", "走", "前进", "探索", "冒险", "看看周围"]):
        return "explore"
    return "observe"


def _world_event_header(task: str, action: str, data: dict, rng_event: str) -> str:
    """长叙述或剧情类行动不用随机「宗门广播」，避免与玩家故事脱节。"""
    if action in ("story_hurt", "story_awaken", "story_crisis"):
        if action == "story_crisis":
            return "【际遇】生死一念间，旧物与你同时回应了这场劫数。"
        if action == "story_hurt":
            return "【际遇】冲突与伤势真实落在你身上，四周的修仙传说此刻都退成背景音。"
        return "【际遇】灵机一动，似乎有什么在回应你的念头。"
    if len(task.strip()) >= 42:
        return "【际遇】你的叙述牵动了这条故事线，余波正在世界里漾开。"
    return f"【世界事件】{rng_event}"


_WORLD_SHORT_LLM_ACTIONS = frozenset(
    {"explore", "observe", "rest", "cultivate", "gather", "eat", "fight", "trade", "survive_day"}
)


def _world_llm_eligible(task: str, action: str) -> bool:
    """长叙述或剧情类输入可走模型润色；常见短指令（如「探索附近」）也可润色。"""
    if not WORLD_SIM_LLM:
        return False
    if not (DASHSCOPE_API_KEY or DEEPSEEK_API_KEY):
        return False
    t = task.strip()
    if action in ("story_hurt", "story_awaken", "story_crisis"):
        return len(t) >= 36
    if action in _WORLD_SHORT_LLM_ACTIONS:
        return len(t) >= 4
    return len(t) >= WORLD_SIM_LLM_MIN_LEN


def compose_world_immersive_reply(task: str, action: str, state: dict, changes: list[str], header: str) -> str | None:
    """用对话模型把结算要点写成沉浸式段落；失败返回 None，调用方回退模板。"""
    t = task.strip()[:6000]
    short_input = len(t) < WORLD_SIM_LLM_MIN_LEN
    pub = json.dumps(public_world_state(state), ensure_ascii=False)
    change_block = "\n".join(changes) if changes else "（本轮仅有时间与心境的细微推移）"
    length_line = (
        "请写一段约 260～520 字的简体中文沉浸式描写：听觉、触觉、气味、光线、体内感受与情绪起伏；"
        if short_input
        else "请写一段约 400～900 字的简体中文沉浸式描写：听觉、触觉、气味、光线、体内感受与情绪起伏；"
    )
    short_hint = ""
    if short_input:
        short_hint = (
            "\n\n玩家原句很短或仅为动作指令：请你补足合理的前因、路途与体感细节，使段落自成一章；"
            "不得与 JSON 设定矛盾，也不可否认结算要点里的后果。"
        )
    user_content = (
        f"【际遇标题】{header}\n\n"
        f"【玩家叙述】\n{t}\n\n"
        f"【必须融入叙事的结算要点】（不可自相矛盾，可用隐喻但不要否认这些后果）：\n{change_block}\n\n"
        f"【当前公开状态 JSON】{pub}\n\n"
        f"{length_line}"
        "节奏要有张弛，承接玩家原文剧情；主题气质须贴合 JSON 里的 theme。"
        "不要输出项目符号、编号、JSON 或面板；不要用「系统提示」「数值」等破壁词。"
        "若原文有人名可沿用；否则以「你」为主视角。"
        f"{short_hint}"
    )
    messages = [
        {
            "role": "system",
            "content": (
                "你是长篇网文与文字 RPG 合一的叙事引擎，擅长仙侠、废土、奇幻的临场散文。"
                "你只输出一段连续正文，不允许前言后语。"
            ),
        },
        {"role": "user", "content": user_content},
    ]
    text = openai_compat_chat_fallback(messages, temperature=0.82)
    min_ok = 56 if short_input else 80
    if not text or len(text.strip()) < min_ok:
        return None
    return text.strip()


def apply_world_action(task):
    if session.WORLD_STATE is None or any(x in task for x in ["生成", "创建", "新开", "重新", "开一个", "来一个"]):
        session.WORLD_STATE = create_world(task)
        return render_world_intro(session.WORLD_STATE)

    state = session.WORLD_STATE
    data = WORLD_THEMES[state["theme"]]
    event = random.choice(data["events"])
    found = random.choice(data["resources"])
    scene = random.choice(data["scenes"])
    action = classify_world_action(task)
    changes = []

    if action == "status":
        st_flavor = (
            "你收束心神，默默自检周身气机与行囊分量。"
            if state["theme"] == "修仙"
            else "你压低呼吸，迅速盘点体征与随身物资。"
        )
        return f"{st_flavor}\n\n{world_status_text(state)}\n\n【行动建议】{ '、'.join(world_suggestions(state)) }"

    if action == "story_hurt":
        dmg = random.randint(16, 34)
        state["hp"] -= dmg
        state["energy"] -= random.randint(8, 20)
        state["hostility"] += random.randint(2, 8)
        state["safety"] = max(0, state["safety"] - random.randint(4, 14))
        changes.append(f"冲突在你身上兑现成实在的伤势：生命 -{dmg}；敌意在抬头。")
    elif action == "story_awaken":
        state["luck"] += random.randint(6, 18)
        state["energy"] += random.randint(6, 16)
        if state["theme"] == "修仙" and random.random() < 0.5:
            state["realm"] = random.choice(["感应气机", "炼气入门", "初入道途", "脉象自明"])
            changes.append(f"灵机轻引，你的境界感更接近「{state['realm']}」。")
        else:
            changes.append("你感到疲惫里多了一丝清明。")
        charm = "温润灵玉（微光）"
        if charm not in state["inventory"] and len(state["inventory"]) < 12:
            state["inventory"].append(charm)
            changes.append(f"随身的旧物似乎与天地轻应了一下：{charm} 已能被你清晰感知。")
    elif action == "story_crisis":
        dmg = random.randint(20, 40)
        state["hp"] -= dmg
        state["luck"] += random.randint(10, 24)
        state["energy"] += random.randint(4, 14)
        state["hostility"] += random.randint(1, 6)
        changes.append(f"你在绝境里重伤倒地边缘（生命 -{dmg}），一线异样暖流却从随身之物涌出。")
        if state["theme"] == "修仙" and random.random() < 0.55:
            state["realm"] = random.choice(["炼气一层", "感应经脉", "初入道途", "残脉复燃"])
            changes.append(f"气机驳杂中有灵光一闪：当前心境更接近「{state['realm']}」。")
        jade = "随身玉佩（灵性初显）"
        if jade not in state["inventory"] and len(state["inventory"]) < 12:
            state["inventory"].append(jade)
            changes.append("玉佩轻颤，像在血腥味里第一次醒来。")
    elif action == "eat":
        edible = next((x for x in state["inventory"] if any(k in x for k in ["果", "饼干", "罐头", "面包", "灵泉水", "药水"])), None)
        if edible:
            state["inventory"].remove(edible)
            state["hunger"] -= random.randint(18, 32)
            state["energy"] += random.randint(6, 12)
            changes.append(f"你使用了「{edible}」，饥饿下降，精力略有恢复。")
        else:
            state["hunger"] += 8
            changes.append("你翻遍背包，没有找到合适的食物。")
    elif action == "gather":
        state["inventory"].append(found)
        state["energy"] -= random.randint(6, 14)
        state["hunger"] += random.randint(4, 9)
        state["luck"] += random.randint(1, 4)
        changes.append(f"你仔细搜寻四周，获得了：{found}。")
    elif action == "cultivate":
        state["energy"] -= random.randint(10, 18)
        state["hunger"] += random.randint(3, 8)
        state["luck"] += random.randint(2, 7)
        if state["theme"] == "修仙" and random.random() < 0.42:
            state["realm"] = random.choice(["炼气一层", "炼气二层", "炼气三层", "初入道途", "炼气四层"])
            changes.append(f"你引气入体，境界有所变化：{state['realm']}。")
        else:
            changes.append("你沉下心修行，感知力变得更敏锐。")
    elif action == "rest":
        state["energy"] += random.randint(18, 30)
        state["hp"] += random.randint(6, 16)
        state["hunger"] += random.randint(5, 12)
        state["safety"] += random.randint(1, 6)
        changes.append("你找到相对安全的角落休息，状态有所恢复。")
    elif action == "fight":
        damage = random.randint(8, 24) + max(state["hostility"] // 20, 0)
        state["hp"] -= damage
        state["energy"] -= random.randint(8, 16)
        state["hostility"] += random.randint(4, 10)
        if random.random() < 0.58:
            state["inventory"].append(found)
            changes.append(f"你冒险迎战，受伤 {damage} 点，但获得了：{found}。")
        else:
            changes.append(f"你勉强脱身，生命下降 {damage} 点。")
    elif action == "trade":
        if state["inventory"]:
            sold = state["inventory"].pop(0)
            state["inventory"].append(found)
            state["safety"] += random.randint(2, 8)
            changes.append(f"你用「{sold}」换到了「{found}」，也打听到一些本地消息。")
        else:
            changes.append("你没有可交易的物品，只能先观察人群和行情。")
    elif action == "survive_day":
        state["day"] += 1
        state["time"] = "清晨"
        state["energy"] -= random.randint(12, 25)
        state["hunger"] += random.randint(18, 30)
        if random.random() < 0.45:
            state["inventory"].append(found)
            changes.append(f"你谨慎度过一天，并找到：{found}。")
        else:
            loss = random.randint(5, 18)
            state["hp"] -= loss
            changes.append(f"这一天并不安稳，你损失 {loss} 点生命。")
    elif action == "explore":
        state["location"] = scene
        state["scene"] = scene
        state["energy"] -= random.randint(8, 16)
        state["hunger"] += random.randint(4, 10)
        state["safety"] -= random.randint(2, 8)
        state["luck"] += random.randint(1, 5)
        changes.append(f"你离开原地，来到：{scene}。")
    else:
        state["energy"] -= 2
        state["hunger"] += 2
        changes.append("你观察周围，记下了地形、气味和远处的动静。")

    if action != "survive_day":
        advance_world_time(state)

    if state["hunger"] >= 80:
        state["hp"] -= 8
        changes.append("饥饿正在拖垮你，生命下降。")
    if state["energy"] <= 0:
        state["hp"] -= 8
        changes.append("精力耗尽让你状态变差，生命额外下降。")
    if state["safety"] <= 20 and random.random() < 0.35:
        state["hostility"] += 8
        changes.append("附近变得很不安全，敌意正在上升。")

    clamp_world_state(state)

    if state["hp"] <= 0:
        ending = "你倒在了这片世界里。本次模拟结束。输入“重新生成一个世界”可以重开。"
        session.WORLD_STATE = None
        return "\n".join(changes + [ending])

    header = _world_event_header(task, action, data, event)
    tail = f"{world_status_text(state)}\n\n【行动建议】{ '、'.join(world_suggestions(state)) }"
    if _world_llm_eligible(task, action):
        immersive = compose_world_immersive_reply(task, action, state, changes, header)
        if immersive:
            return f"{immersive}\n\n{tail}"
    narrative = world_fallback_narrative(state["theme"], action, event, changes, state)
    return f"{narrative}\n\n{tail}"


# -------------------------- 6.5 数据图表生成模块 --------------------------
# 作用：把用户输入的自然语言数据或上传的数据文件转换成前端可直接渲染的图表结构。
# 用到的东西：
# - re：从“月份:数值”这类文本中提取标签和值；
# - csv + io：读取 CSV / TXT / TSV 等表格文本；
# - openpyxl：读取 Excel 的前两列数据；
# - chartData JSON：后端不直接画图，只返回标准数据，由前端 ChartPanel 负责展示。
def is_chart_intent(task):
    """判断用户是否想生成图表。命中后会进入数据可视化流程。"""
    t = task.strip().lower()
    chart_words = [
        "图表", "折线图", "线形图", "线型图", "线性图", "线性图表", "柱状图", "条形图", "柱形图", "趋势图",
        "可视化", "数据分析", "统计图", "数据图", "画图", "作图", "生成图",
    ]
    if any(word in t for word in chart_words):
        return True
    # 「生成/模拟…数据」且同时要图（如：帮我生成一份数据和图表）
    has_viz = any(
        x in t
        for x in ["图表", "柱状", "折线", "条形", "线性", "可视化", "趋势", "统计图", "图"]
    )
    has_data_ask = any(
        x in t
        for x in [
            "生成数据", "一份数据", "模拟数据", "示例数据", "演示数据",
            "样本数据", "随机数据", "假数据", "测试数据",
        ]
    )
    if has_viz and has_data_ask:
        return True
    if has_viz and "数据" in t and any(x in t for x in ["生成", "做", "来", "给", "帮我", "请"]):
        return True
    return False


def detect_chart_type(task, default="bar"):
    """根据用户指令选择图表类型：趋势类用折线图，对比类默认用柱状图。"""
    t = task.strip()
    # 「线性图表」等口语未写「折线」时也应归为折线；排除「非线性」以免误匹配子串「线性」
    if any(x in t for x in ["折线", "线形", "线型", "趋势", "曲线图", "line"]):
        return "line"
    if "非线性" not in t and "线性" in t:
        return "line"
    if any(x in t for x in ["条形", "柱状", "柱形", "bar"]):
        return "bar"
    return default


def normalize_label_value(label, value):
    """把原始标签和值统一清洗成 {label, value}，过滤空标签和非数字值。"""
    label = str(label).strip().strip('"\'，,;；:：')
    try:
        number = float(str(value).strip().replace(",", ""))
    except (TypeError, ValueError):
        return None
    if not label or label in ["数据", "数值", "值"]:
        return None
    return {"label": label, "value": round(number, 4)}


def parse_chart_data_from_text(text):
    """从自然语言文本中提取图表数据，支持“一月:120 二月:180”或纯数字序列。"""
    clean = text.strip()
    points = []

    pair_patterns = [
        r"([\u4e00-\u9fa5A-Za-z0-9_./-]{1,24})\s*[:：=]\s*(-?\d+(?:\.\d+)?)",
        r"([\u4e00-\u9fa5A-Za-z0-9_./-]{1,24})\s+(-?\d+(?:\.\d+)?)",
    ]
    for pattern in pair_patterns:
        matches = re.findall(pattern, clean)
        parsed = [normalize_label_value(label, value) for label, value in matches]
        points = [item for item in parsed if item]
        if len(points) >= 2:
            return points[:80]

    numbers = [float(x) for x in re.findall(r"-?\d+(?:\.\d+)?", clean)]
    if len(numbers) >= 2:
        return [{"label": f"第{i + 1}项", "value": round(value, 4)} for i, value in enumerate(numbers[:80])]
    return []


def parse_delimited_chart_data(text):
    """读取 CSV / TXT / TSV 文本，默认取前两列作为“名称”和“数值”。"""
    sample = text[:2048]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",\t;，；")
    except csv.Error:
        dialect = csv.excel
    rows = list(csv.reader(io.StringIO(text), dialect))
    rows = [[cell.strip() for cell in row] for row in rows if any(cell.strip() for cell in row)]
    if not rows:
        return []

    start_index = 0
    if len(rows) > 1 and not any(re.fullmatch(r"-?\d+(?:\.\d+)?", cell.replace(",", "")) for cell in rows[0]):
        start_index = 1

    points = []
    for idx, row in enumerate(rows[start_index:start_index + 80], start=start_index):
        if len(row) >= 2:
            item = normalize_label_value(row[0] or f"第{idx + 1}项", row[1])
            if item:
                points.append(item)
        elif len(row) == 1:
            item = normalize_label_value(f"第{idx + 1}项", row[0])
            if item:
                points.append(item)
    return points


def parse_chart_file(file_storage):
    """解析上传文件。CSV/TXT 直接按文本读，Excel 用 openpyxl 读取活动工作表。"""
    if not file_storage or not file_storage.filename:
        raise ValueError("请先选择 CSV、TXT 或 Excel 数据文件。")
    filename = file_storage.filename
    ext = Path(filename).suffix.lower()
    raw = file_storage.read()
    if len(raw) > 2 * 1024 * 1024:
        raise ValueError("文件过大，请上传 2MB 以内的数据文件。")

    if ext in [".csv", ".txt", ".tsv"]:
        for encoding in ["utf-8-sig", "utf-8", "gbk"]:
            try:
                return parse_delimited_chart_data(raw.decode(encoding))
            except UnicodeDecodeError:
                continue
        raise ValueError("文件编码无法识别，请保存为 UTF-8 或 GBK。")

    if ext in [".xlsx", ".xls"]:
        try:
            import openpyxl
        except ImportError as exc:
            raise ValueError("后端暂未安装 openpyxl，无法读取 Excel。请先安装依赖或上传 CSV 文件。") from exc
        workbook = openpyxl.load_workbook(io.BytesIO(raw), read_only=True, data_only=True)
        sheet = workbook.active
        rows = []
        for row in sheet.iter_rows(max_row=81, values_only=True):
            rows.append(["" if cell is None else str(cell).strip() for cell in row])
        text = "\n".join(",".join(row[:2]) for row in rows)
        return parse_delimited_chart_data(text)

    raise ValueError("暂只支持 CSV、TXT、TSV、XLSX、XLS 文件。")


def infer_demo_chart_title(task, chart_type):
    """从指令里猜一个演示标题，没有则用默认。"""
    t = task.strip()
    for kw in ["销售", "营收", "利润", "用户", "访问", "流量", "订单", "产量", "库存", "温度", "湿度", "降水"]:
        if kw in t:
            suffix = "趋势" if chart_type == "line" else "对比"
            return f"{kw}{suffix}（示例）"
    return "数据趋势折线图（示例）" if chart_type == "line" else "数据对比柱状图（示例）"


def generate_demo_chart_points(task):
    """未提供具体数字时，生成一组可展示的模拟数据。"""
    chart_type = detect_chart_type(task)
    seed = abs(hash(task.strip())) % (2**32)
    rng = random.Random(seed)
    if chart_type == "line":
        labels = [f"{i + 1}月" for i in range(8)]
        base = rng.randint(35, 95)
        step = rng.randint(6, 22)
        points = []
        for i in range(8):
            noise = rng.randint(-10, 14)
            v = base + i * step + noise
            points.append({"label": labels[i], "value": round(max(1.0, float(v)), 2)})
        return points
    categories = ["华北", "华东", "华南", "西南", "西北", "东北", "华中", "线上"]
    rng.shuffle(categories)
    n = rng.randint(6, 8)
    cats = categories[:n]
    return [{"label": c, "value": round(rng.uniform(18, 220), 2)} for c in cats]


def resolve_chart_points_from_task(task):
    """优先从指令文本解析数值；不足 2 组时用模拟数据。"""
    points = parse_chart_data_from_text(task)
    if len(points) >= 2:
        return points, "文本数据"
    return (
        generate_demo_chart_points(task),
        "模拟示例数据（指令中无具体数值，已自动生成演示数据集）",
    )


def build_chart_payload(task, points, source="文本数据"):
    """组装统一响应：图表类型、标题、数据点和摘要统计都放进 chartData。"""
    if len(points) < 2:
        raise ValueError("至少需要 2 组数据，例如：生成折线图 一月:120 二月:180 三月:150。")
    chart_type = detect_chart_type(task)
    title_match = re.search(r"(?:标题|名称)[:：]\s*([^\n，,。]+)", task)
    default_title = "数据趋势折线图" if chart_type == "line" else "数据对比柱状图"
    if title_match:
        title = title_match.group(1).strip()
    elif source.startswith("模拟"):
        title = infer_demo_chart_title(task, chart_type)
    else:
        title = default_title
    total = sum(item["value"] for item in points)
    max_item = max(points, key=lambda item: item["value"])
    min_item = min(points, key=lambda item: item["value"])
    return {
        "type": "chart",
        "chartData": {
            "chartType": chart_type,
            "title": title,
            "source": source,
            "points": points,
            "summary": {
                "count": len(points),
                "total": round(total, 2),
                "maxLabel": max_item["label"],
                "maxValue": max_item["value"],
                "minLabel": min_item["label"],
                "minValue": min_item["value"],
            },
        },
        "msg": (
            f"未在指令中解析到具体数值，已自动生成示例数据并绘制{'折线图' if chart_type == 'line' else '柱状图'}，共 {len(points)} 组。"
            if source.startswith("模拟")
            else f"已根据{source}生成{'折线图' if chart_type == 'line' else '柱状图'}，共识别 {len(points)} 组数据。"
        ),
        **current_mode_payload({"mode": "chart", "modeLabel": "数据可视化"}),
    }


# -------------------------- 7. 指令解析核心 --------------------------
def is_goodbye_intent(task):
    """识别全局结束语，用于让前端回到初始待机界面。"""
    t = task.strip().lower().replace(" ", "")
    return any(x in t for x in [
        "再见小文", "小文再见", "拜拜小文", "小文拜拜", "退出小文",
        "结束小文", "休息吧小文", "小文休息吧", "bye小文", "byebye小文",
    ])


def with_intent_workflow(result, intent_result, *items):
    """在 workflow 首部插入意图识别步骤。"""
    return with_workflow(result, ("识别意图", intent_workflow_label(intent_result)), *items)


def parse_command(task, chat_history=None, client_location=None, user_id=None, client_preferences=None):
    """统一指令路由入口：告别/世界状态 → LLM 意图分类 + 规则兜底 + 缓存 → 业务分支。

    client_location：前端可选 { lat, lng }（WGS84），用于当地天气与附近美食等。
    user_id：数据库用户 ID，用于注入个人偏好到 AI 对话的 system prompt 中。
    client_preferences：前端可选偏好字典（与 DB 偏好合并注入）。
    """
    task = task.strip()

    if is_goodbye_intent(task):
        get_dialogue_manager().reset()
        session.WORLD_STATE = None
        return {
            "type": "goodbye",
            "msg": "再见，我会在这里等你。需要我的时候，随时叫我小文。",
            "resetUI": True,
            **current_mode_payload(),
        }

    if session.WORLD_STATE is not None:
        if is_world_exit_intent(task):
            session.WORLD_STATE = None
            session.CHAT_HISTORY = []
            return {"type": "chat", "msg": "已退出模拟世界，回到小文普通助手模式。你可以继续聊天、查天气、播放音乐或生成图片。", **current_mode_payload()}
        return {"type": "chat", "msg": apply_world_action(task), **current_mode_payload()}

    lang_follow = bool(chat_history) and is_music_language_followup(task, chat_history)
    follow_query = resolve_music_followup_search_query(task, chat_history) if lang_follow else None
    dm = get_dialogue_manager()
    intent_ctx = {
        "has_history": bool(dm.resolve_history(chat_history)),
        "has_location": isinstance(client_location, dict),
        "music_followup": bool(follow_query),
    }
    intent_result = classify_intent(task, intent_ctx)
    intent = intent_result.intent
    session.LAST_INTENT = intent

    if intent == INTENT_APP_LIST:
        return with_intent_workflow(
            {"type": "app", "msg": supported_app_message(), **current_mode_payload()},
            intent_result,
            ("接收指令", task),
            ("返回结果", "展示白名单应用列表"),
        )

    if intent == INTENT_KNOWLEDGE:
        answer, refs = ai_answer_with_knowledge(task)
        sources = "、".join(f"{r['source']}#{r['index']}" for r in refs)
        return with_intent_workflow(
            {"type": "chat", "msg": answer, "knowledgeSources": sources, **current_mode_payload({"mode": "knowledge", "modeLabel": "知识库问答"})},
            intent_result,
            ("接收问题", task),
            ("检索知识库", sources or "项目 README / 汇总文档"),
            ("生成回答", "基于检索片段组织答案"),
        )

    if intent == INTENT_IMAGE_LOOKUP:
        query = extract_image_search_query(task, chat_history)
        if not query:
            return with_intent_workflow(
                {
                    "type": "chat",
                    "msg": (
                        "我还没对上你想看哪道菜或哪个东西。你可以：\n"
                        "· 直接说「白洋淀鱼头汤 图片」\n"
                        "· 或先让小文推荐美食，再说「帮我搜一下图片我想看看」（我会用上一条回复里的名字）"
                    ),
                    **current_mode_payload({"mode": "web", "modeLabel": "图片搜索"}),
                },
                intent_result,
                ("接收指令", task),
                ("解析搜索词", "未从对话中识别具体名称"),
                ("返回提示", "引导用户补充关键词"),
            )
        encoded = urllib.parse.quote(query)
        image_search_url = f"https://image.baidu.com/search/index?tn=baiduimage&word={encoded}"
        return with_intent_workflow(
            {
                "type": "web",
                "msg": f"已为你准备「{query}」的图片搜索，点击下方链接在浏览器里浏览实物图（结果来自搜索引擎）。",
                "previewUrl": image_search_url,
                **current_mode_payload({"mode": "web", "modeLabel": "图片搜索"}),
            },
            intent_result,
            ("接收指令", task),
            ("提取关键词", query),
            ("生成链接", "百度图片搜索"),
            ("返回结果", "前端展示可点击链接"),
        )

    if intent == INTENT_IMAGE_UNDERSTANDING:
        answer, image_url = ai_understand_image(task)
        return with_intent_workflow(
            {"type": "chat", "msg": answer, "imageUnderstandingUrl": image_url, **current_mode_payload({"mode": "vision", "modeLabel": "图片理解"})},
            intent_result,
            ("接收图片", image_url or "未提供图片链接"),
            ("调用视觉模型", "识别图片内容并生成描述"),
            ("返回结果", "展示图片理解结论"),
        )

    if intent == INTENT_CHART:
        try:
            points, data_source = resolve_chart_points_from_task(task)
            chart_payload = build_chart_payload(task, points, data_source)
            parse_detail = "自动生成演示数据" if data_source.startswith("模拟") else "从文本中提取标签和值"
            ct = (chart_payload.get("chartData") or {}).get("chartType") or detect_chart_type(task)
            chart_cn = "折线图" if ct == "line" else "柱状图"
            return with_intent_workflow(
                chart_payload,
                intent_result,
                ("接收图表指令", task),
                ("解析数据", parse_detail),
                ("选择图表", f"依指令关键字匹配为「{chart_cn}」"),
                ("生成图表", "前端 SVG 可视化渲染"),
            )
        except ValueError as e:
            return with_intent_workflow(
                {"type": "chat", "msg": str(e), **current_mode_payload({"mode": "chart", "modeLabel": "数据可视化"})},
                intent_result,
                ("接收图表指令", task),
                ("解析数据", "未识别到足够的标签和值"),
                ("返回提示", "引导用户输入数据或上传文件"),
            )

    if intent == INTENT_WEATHER and "天气" in task and not task_should_skip_weather_branch(task):
        city, city_from_ctx, loc_adcode, loc_geo = resolve_weather_city(task, chat_history, client_location)
        data = get_weather_info(city, adcode=loc_adcode, location_detail=loc_geo)
        if loc_adcode:
            data["locationSource"] = "browser_gps"
        adv_block = weather_outdoor_advice(data)
        data["outdoorTips"] = [
            ln.lstrip("·").strip() for ln in adv_block.split("\n") if ln.strip().startswith("·")
        ]
        msg = build_weather_reply(task, city, data)
        if (
            not loc_adcode
            and city == "北京"
            and not city_from_ctx
            and not extract_city_candidate(task)
            and not infer_city_from_single_task(task)
        ):
            msg += (
                "\n\n💡 未确认你所在城市：未收到浏览器定位，且你这句里也没有写明城市。"
                "可以说「保定天气」或在浏览器为本站点开启「位置」权限后再问「今天天气」。"
            )
        if loc_adcode:
            city_step = f"{city}（根据你授权的浏览器定位）"
        elif city_from_ctx:
            city_step = f"{city}（沿用上文目的地）"
        else:
            city_step = city
        wf = [
            ("接收指令", task),
            ("提取城市", city_step),
            ("调用天气服务", "高德地图天气接口（含逆地理/实况）"),
            ("生成出行提示", "结合气温、风力、湿度与天气现象"),
        ]
        if is_weather_travel_intent(task):
            wf.append(("旅游日程建议", "对话模型润色或模板行程"))
        wf.append(("展示结果", "实况摘要与建议"))
        return with_intent_workflow({"type": "weather", "msg": msg, "extraData": data, **current_mode_payload()}, intent_result, *wf)

    if intent == INTENT_MUSIC_NAV:
        nav = parse_music_navigation(task)
        if nav:
            tip = "已切换到下一首（使用你播放器里的播放记录）。" if nav == "next" else "已切换到上一首（使用你播放器里的播放记录）。"
            return with_intent_workflow(
                {
                    "type": "music_control",
                    "musicAction": nav,
                    "msg": tip,
                    **current_mode_payload({"mode": "music", "modeLabel": "音乐播放中"}),
                },
                intent_result,
                ("接收指令", task),
                ("切歌", "下一首" if nav == "next" else "上一首"),
                ("前端执行", "由本地播放列表环形切换，无需重新搜索外链"),
            )

    if intent == INTENT_MUSIC or follow_query:
        eff_task = task if is_music_intent(task) else "放点歌"
        music_url, song_name, music_provider, qishui_url, qishui_embed_url = search_music_url(
            eff_task, chat_history, explicit_query=follow_query
        )
        is_qishui = music_provider == "qishui"
        return with_intent_workflow(
            {
                "type": "music",
                "msg": f"正在为你播放：{song_name}" if not is_qishui else f"正在为你打开汽水音乐：{song_name}",
                "previewUrl": music_url,
                "songName": song_name,
                "musicProvider": music_provider,
                "qishuiUrl": qishui_url,
                "qishuiEmbedUrl": qishui_embed_url,
                **current_mode_payload({"mode": "music", "modeLabel": "音乐播放中" if not is_qishui else "汽水音乐播放"}),
            },
            intent_result,
            ("接收指令", task),
            ("提取歌曲", song_name),
            ("搜索可播放音频", "优先返回浏览器 audio 可直接播放的试听源" if not is_qishui else "用户指定汽水音乐时打开官方入口"),
            ("进入播放", "前端播放器立即加载音频并自动播放" if not is_qishui else "官方页面负责登录和播放"),
        )

    if intent == INTENT_LOCAL_FOOD:
        loc = client_location if isinstance(client_location, dict) else None
        lng = (loc or {}).get("lng") or (loc or {}).get("longitude")
        lat = (loc or {}).get("lat") or (loc or {}).get("latitude")
        if loc is not None and lng is not None and lat is not None:
            try:
                lng_f, lat_f = float(lng), float(lat)
                if (-180 <= lng_f <= 180) and (-90 <= lat_f <= 90):
                    body = compose_nearby_food_reply(task, lng_f, lat_f)
                    return with_intent_workflow(
                        {
                            "type": "chat",
                            "msg": body,
                            **current_mode_payload({"mode": "local", "modeLabel": "附近推荐"}),
                        },
                        intent_result,
                        ("接收指令", task),
                        ("定位与逆地理", "浏览器经纬度 → 高德 GCJ02 / regeo"),
                        ("周边搜索", "餐饮服务类 POI"),
                        ("生成推荐", "按距离列出店名与地址"),
                    )
            except (TypeError, ValueError):
                pass
        return with_intent_workflow(
            {
                "type": "chat",
                "msg": (
                    "想按「附近」给你吃的建议，需要知道你大概在哪：请在浏览器里允许本站点使用**位置**权限后再问一次；"
                    "或直接说你在哪个城市/区县/商圈（例如「我在海淀五道口附近饿了」），我也能按地名参谋。"
                ),
                **current_mode_payload({"mode": "local", "modeLabel": "附近推荐"}),
            },
            intent_result,
            ("接收指令", task),
            ("缺少定位", "未收到经纬度或坐标无效"),
            ("返回提示", "引导开启定位或补充地名"),
        )

    if intent == INTENT_WORLD_CREATE:
        return with_intent_workflow(
            {"type": "chat", "msg": apply_world_action(task), **current_mode_payload()},
            intent_result,
            ("接收指令", task),
            ("创建模拟世界", "生成世界种子、出生点和初始状态"),
            ("锁定模式", "进入文字模拟世界"),
        )

    if intent == INTENT_IMAGE_GENERATE:
        prompt = extract_image_prompt(task)
        task_id = dashscope_submit_image(prompt) if DASHSCOPE_API_KEY else None
        if task_id:
            return with_intent_workflow(
                {"type": "image_pending", "msg": f"正在生成：{prompt}", "taskId": task_id, "prompt": prompt, **current_mode_payload({"mode": "image", "modeLabel": "图片生成中"})},
                intent_result,
                ("接收绘图指令", task),
                ("提取提示词", prompt),
                ("提交文生图任务", "DashScope 异步任务"),
                ("前端轮询", "等待图片生成完成"),
            )
        image_url = generate_image(prompt)
        return with_intent_workflow(
            {"type": "image", "msg": f"正在为你生成：{prompt}", "imageUrl": image_url, "prompt": prompt, **current_mode_payload({"mode": "image", "modeLabel": "图片已生成"})},
            intent_result,
            ("接收绘图指令", task),
            ("提取提示词", prompt),
            ("生成图片", "同步生成或兜底接口"),
            ("展示结果", "前端图片预览"),
        )

    if intent == INTENT_APP_LAUNCH and wants_douyin_web_open(task) and any(
        task.startswith(prefix) for prefix in ["打开", "启动", "运行", "开启", "帮我打开", "帮我启动", "请打开"]
    ):
        return with_intent_workflow(
            {"type": "web", "msg": "已为你准备抖音网页（见下方链接；若允许弹窗会自动打开新标签页）。", "previewUrl": "https://www.douyin.com", **current_mode_payload()},
            intent_result,
            ("接收指令", task),
            ("识别网页", "抖音（网页版）"),
            ("返回链接", "https://www.douyin.com"),
        )

    if intent == INTENT_APP_LAUNCH and any(
        task.startswith(prefix) for prefix in ["打开", "启动", "运行", "开启", "帮我打开", "帮我启动", "请打开"]
    ):
        success, msg = launch_local_app(task)
        if success:
            return with_intent_workflow(
                {"type": "app", "msg": msg, **current_mode_payload()},
                intent_result,
                ("接收指令", task),
                ("匹配白名单", "只允许启动安全应用"),
                ("执行启动", msg),
            )
        if "网页" not in task and "网站" not in task and "百度" not in task:
            return with_intent_workflow(
                {"type": "chat", "msg": msg, **current_mode_payload()},
                intent_result,
                ("接收指令", task),
                ("匹配白名单", "未找到支持的本机应用"),
                ("返回提示", msg),
            )

    if intent == INTENT_WEB_OPEN and "打开" in task:
        site = task.replace("打开", "").strip()
        if "百度" in site:
            return with_intent_workflow(
                {"type": "web", "msg": "已为你准备百度网页（见下方链接；若允许弹窗会自动打开新标签页）。", "previewUrl": "https://www.baidu.com", **current_mode_payload()},
                intent_result,
                ("接收指令", task),
                ("识别网页", "百度"),
                ("返回链接", "https://www.baidu.com"),
            )
        if "抖音" in site and wants_douyin_web_open(task):
            return with_intent_workflow(
                {"type": "web", "msg": "已为你准备抖音网页（见下方链接；若允许弹窗会自动打开新标签页）。", "previewUrl": "https://www.douyin.com", **current_mode_payload()},
                intent_result,
                ("接收指令", task),
                ("识别网页", "抖音（网页版）"),
                ("返回链接", "https://www.douyin.com"),
            )
        search_url = f"https://www.baidu.com/s?wd={urllib.parse.quote(site)}"
        return with_intent_workflow(
            {"type": "web", "msg": f"正在搜索：{site}", "previewUrl": search_url, **current_mode_payload()},
            intent_result,
            ("接收指令", task),
            ("生成搜索词", site),
            ("返回搜索链接", search_url),
        )

    loc_hint = format_location_hint_for_llm(client_location if isinstance(client_location, dict) else None)
    ctx_wf = dm.context_label()
    if loc_hint:
        ctx_wf += "；已注入大致位置（逆地理地址，供回答贴近本地）"
    return with_intent_workflow(
        {
            "type": "chat",
            "msg": ai_chat(
                task,
                chat_history,
                location_hint=loc_hint,
                user_id=user_id,
                user_preferences=client_preferences,
            ),
            **current_mode_payload(),
        },
        intent_result,
        ("接收问题", task),
        ("整理上下文", ctx_wf),
        ("调用对话模型", primary_chat_model_label()),
        ("返回回答", "展示在小文回复卡片"),
    )

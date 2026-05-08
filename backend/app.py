"""Flask 后端「小文」：统一指令入口（如 `/api/send-task`），路由天气、音乐、对话、文生图、图表等。

约定：
- 对话类请求的 system prompt 会附带「当前真实时间」与农历事实（见 ``current_datetime_context_for_llm``），减轻模型编造日期；
- 农历依赖可选库 zhdate；传给 ZhDate 前须使用与时区一致的 naive 本地墙钟时间（避免 naive/aware 混减）。
"""
from flask import Flask, request, jsonify
# 解决跨域，允许网页调用接口
from flask_cors import CORS
# 调用第三方 API（天气、音乐、AI）
import requests
# re：文字提取
import re
# urllib.parse：URL 解析
import urllib.parse
# logging：日志记录
import logging
# os：操作系统相关操作
import os
# subprocess：子进程管理,打开电脑软件（记事本、微信）
import subprocess
import random
import time
import base64
import csv
import io
from datetime import datetime
from pathlib import Path

try:
    from zoneinfo import ZoneInfo
except ImportError:
    ZoneInfo = None  # pragma: no cover

try:
    from zhdate import ZhDate
except ImportError:
    ZhDate = None  # pragma: no cover

# 读取私密配置（AI 密钥不能写在代码里一旦上传到 GitHub，任何人都能盗用你的密钥扣费,.env 是私密配置文件，只存在你本地）
from dotenv import load_dotenv, dotenv_values

_ENV_DIR = Path(__file__).resolve().parent
_ENV_FILE = _ENV_DIR / ".env"
# utf-8-sig 避免记事本保存的 BOM；显式再写入 os.environ，避免未保存/缓存导致读不到
# 读取我的阿里云百炼 AI 密钥,读取模型名称、图片尺寸等,密钥不写死在代码里，更安全
load_dotenv(_ENV_FILE, encoding="utf-8-sig")
for _k, _v in dotenv_values(_ENV_FILE, encoding="utf-8-sig").items():
    if _v is not None and str(_v).strip() != "":
        os.environ[_k] = str(_v).strip()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
# 初始化Flask应用，解决跨域问题
app = Flask(__name__)
CORS(app)

# 核心配置区域：高德 Key 请写在 backend/.env 的 AMAP_KEY（勿提交 Git）
AMAP_KEY = os.environ.get("AMAP_KEY", "").strip()
REQUEST_TIMEOUT = 10
CHAT_TIMEOUT = int(os.environ.get("CHAT_TIMEOUT", "60"))
# 闲聊/倒计时类回答使用的本地时区（IANA），默认中国东部
LOCAL_TIMEZONE = os.environ.get("LOCAL_TIMEZONE", "Asia/Shanghai").strip()
DASHSCOPE_API_KEY = os.environ.get("DASHSCOPE_API_KEY", "").strip()
DASHSCOPE_CHAT_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
DASHSCOPE_CHAT_MODEL = os.environ.get("DASHSCOPE_CHAT_MODEL", "qwen-turbo").strip()
DASHSCOPE_IMAGE_MODEL = os.environ.get("DASHSCOPE_IMAGE_MODEL", "wanx2.1-t2i-turbo").strip()
DASHSCOPE_VL_MODEL = os.environ.get("DASHSCOPE_VL_MODEL", "qwen-vl-plus").strip()
MAX_UPLOAD_IMAGE_BYTES = int(os.environ.get("MAX_UPLOAD_IMAGE_BYTES", str(8 * 1024 * 1024)))
IMAGE_SIZE = os.environ.get("IMAGE_SIZE", "768*1024").strip()
IMAGE_TASK_TIMEOUT = int(os.environ.get("IMAGE_TASK_TIMEOUT", "120"))
DASHSCOPE_TASK_POLL_INTERVAL = float(os.environ.get("DASHSCOPE_TASK_POLL_INTERVAL", "1"))
# DeepSeek：OpenAI 兼容 /v1/chat/completions，可用于对话、划词翻译、知识库；文生图与视觉仍依赖百炼
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "").strip()
DEEPSEEK_CHAT_URL = os.environ.get("DEEPSEEK_CHAT_URL", "https://api.deepseek.com/v1/chat/completions").strip()
DEEPSEEK_CHAT_MODEL = os.environ.get("DEEPSEEK_CHAT_MODEL", "deepseek-chat").strip()

NETEASE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://music.163.com/",
}

WORLD_STATE = None
CHAT_HISTORY = []
KNOWLEDGE_SNIPPETS = []
MAX_KNOWLEDGE_SNIPPETS = 80
MAX_CHAT_HISTORY_MESSAGES = 12
MAX_CHAT_MESSAGE_CHARS = 1200
WORLD_THEMES = {
    "修仙": {
        "cores": ["灵气潮汐", "天道残缺", "万宗争鸣", "妖魔复苏", "古仙遗迹", "灵根觉醒"],
        "birthplaces": ["青岚山脚的破旧药庐", "云河镇外的竹林", "玄霜谷边缘", "落霞宗杂役院", "黑石矿洞入口", "无名古庙"],
        "resources": ["下品灵石", "凝气草", "灵泉水", "妖兽骨", "破损符箓", "赤阳果", "寒铁矿", "旧丹方"],
        "scenes": ["雾气缭绕的山涧", "传来兽吼的密林", "灵光闪动的废墟", "小镇夜市", "宗门试炼路", "被阵法封住的洞府"],
        "events": ["遇到受伤散修", "发现一处浅层灵脉", "被低阶妖兽盯上", "听见宗门招收弟子的消息", "捡到一枚残缺玉简", "遭遇突来的灵雨"],
    },
    "末日": {
        "cores": ["资源枯竭", "感染扩散", "机械失控", "极寒降临", "废土重建", "异种入侵"],
        "birthplaces": ["废弃超市仓库", "地下车站", "城市边缘避难所", "荒废学校", "裂开的高架桥下", "旧医院楼顶"],
        "resources": ["压缩饼干", "净水片", "旧电池", "急救绷带", "铁管", "防寒布", "罐头", "打火机"],
        "scenes": ["满是灰尘的街区", "警报残响的避难所", "停电的商场", "被藤蔓吞没的楼群", "浓雾里的停车场", "断裂的天桥"],
        "events": ["远处传来求救声", "发现被撬开的物资箱", "一群感染者正在游荡", "夜色提前降临", "避难所广播断断续续响起", "暴雨即将到来"],
    },
    "奇幻": {
        "cores": ["魔法复苏", "诸神沉眠", "龙族回归", "王国分裂", "地下城涌现", "星陨预言"],
        "birthplaces": ["边境酒馆", "银月森林", "风车村", "古堡废墙旁", "冒险者公会门口", "幽蓝湖畔"],
        "resources": ["银币", "治疗药水", "魔晶碎片", "旧短剑", "羊皮地图", "火绒草", "精灵面包", "铁质护符"],
        "scenes": ["铺满萤火的森林", "阴冷的古堡大厅", "喧闹的冒险者集市", "巨龙掠过的山谷", "被诅咒的墓园", "星光照耀的湖面"],
        "events": ["吟游诗人说出预言", "哥布林留下脚印", "商队请求护送", "湖面浮出古老符文", "远方出现龙影", "迷路的精灵向你求助"],
    },
}
WORLD_ACTIONS = ["探索", "采集", "修炼", "休息", "战斗", "交易", "向北", "向南", "向东", "向西", "生存", "查看状态"]

# 只允许打开白名单中的应用，避免任意命令执行风险。
# 如需新增应用，只在这里补充名称和启动命令即可。
APP_LAUNCHERS = {
    "记事本": "notepad",
    "笔记本": "notepad",
    "计算器": "calc",
    "画图": "mspaint",
    "截图": "SnippingTool",
    "命令行": "cmd",
    "终端": "wt",
    "文件管理器": "explorer",
    "资源管理器": "explorer",
    "浏览器": "start msedge",
    "edge": "start msedge",
    "谷歌": "start chrome",
    "chrome": "start chrome",
    "微信": "start wechat",
    "qq": "start qq",
    "网易云": "start cloudmusic",
    "抖音": "shortcut:抖音",
    "douyin": "shortcut:抖音",
    "vscode": "code",
    "代码": "code",
}

MSG_LLM_NOT_CONFIGURED = (
    "对话服务未就绪：请在 backend 目录的 .env 中至少配置其一，保存后重启后端：\n"
    "· DASHSCOPE_API_KEY — 阿里云百炼（推荐：对话、文生图、图片理解、翻译）\n"
    "· DEEPSEEK_API_KEY — DeepSeek（对话、翻译、知识库；生图/看图仍需要百炼）\n"
    "若已配置仍失败，请检查密钥是否有效、网络是否可访问对应 API。"
)
MSG_TRANSLATE_NOT_CONFIGURED = (
    "翻译未就绪：请在 backend/.env 中配置 DASHSCOPE_API_KEY 或 DEEPSEEK_API_KEY 后重启后端。"
)
MSG_VISION_NEED_DASHSCOPE = (
    "图片理解需要阿里云百炼：请在 backend/.env 配置 DASHSCOPE_API_KEY。"
    "DeepSeek 不提供看图接口。"
)


def primary_chat_model_label():
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
    return any(kw in task for kw in ["播放", "听", "音乐", "歌"])


# -------------------------- 1. 天气查询模块 --------------------------
# 提取城市名称,正则表达式匹配城市名称
def extract_city(task):
    patterns = [
        r'(.*?)天气',
        r'(.*?)的天气',
        r'我要(.*?)天气'
    ]
    for pattern in patterns:
        match = re.search(pattern, task)
        if match:
            city = match.group(1).strip()
            if len(city) >= 2 and city not in ["今天", "明天"]:
                return city
    return "北京"

# 获取天气信息
# 先获取城市编码，再获取天气信息,在返回前端需要的格式天气信息
def get_weather_info(city="北京"):
    placeholder = {
        "city": city,
        "weather": "晴",
        "temperature": "25°C",
        "wind": "微风",
        "humidity": "40%",
    }
    if not AMAP_KEY:
        logger.warning("未配置 AMAP_KEY，天气接口不可用，返回占位数据。请在 backend/.env 设置高德 Web 服务 Key。")
        return placeholder
    try:
        geo_url = f"https://restapi.amap.com/v3/geocode/geo?key={AMAP_KEY}&address={city}"
        geo_resp = requests.get(geo_url, timeout=REQUEST_TIMEOUT)
        geo_data = geo_resp.json()
        
        if geo_data['status'] != '1' or not geo_data.get('geocodes'):
            raise Exception(f"City '{city}' not found")
            
        adcode = geo_data['geocodes'][0]['adcode']
        
        weather_url = f"https://restapi.amap.com/v3/weather/weatherInfo?key={AMAP_KEY}&city={adcode}"
        weather_resp = requests.get(weather_url, timeout=REQUEST_TIMEOUT)
        weather_data = weather_resp.json()
        
        if weather_data['status'] == '1' and weather_data.get('lives'):
            live = weather_data['lives'][0]
            return {
                "city": live['province'] + live['city'],
                "weather": live['weather'],
                "temperature": live['temperature'] + "°C",
                "wind": f"{live['winddirection']}风 {live['windpower']}级",
                "humidity": live['humidity'] + "%"
            }
    except Exception as e:
        logger.error(f"Weather API Error: {e}")

    return placeholder

# -------------------------- 2. 音乐搜索模块 --------------------------

def extract_music_query(task):
    """从自然语言里抽出用于模糊搜索的歌名/关键词。"""
    t = task.strip()
    m = re.search(r"《([^》]+)》", t)
    if m:
        return m.group(1).strip()
    m = re.search(r"「([^」]+)」", t)
    if m:
        return m.group(1).strip()

    t = re.sub(r"^(用|使用)?(汽水音乐|汽水|网易云音乐|网易云|QQ音乐|酷狗音乐|酷我音乐)(来|给我)?", "", t).strip()
    t = re.sub(r"^(用|使用)", "", t).strip()

    prefixes = (
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


def search_music_url(task):
    """多级降级：先搜 iTunes 试听,再搜网易云,再搜免费接口,最后兜底默认音乐。"""
    song_query = extract_music_query(task)
    wants_qishui = "汽水" in task or "music.douyin.com/qishui" in task
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
    global KNOWLEDGE_SNIPPETS
    if KNOWLEDGE_SNIPPETS:
        return KNOWLEDGE_SNIPPETS

    candidates = [
        _ENV_DIR.parent / "xiao-wen-ai" / "README.md",
        _ENV_DIR.parent / "AI与前端项目汇总.md",
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
    KNOWLEDGE_SNIPPETS = snippets[:MAX_KNOWLEDGE_SNIPPETS]
    return KNOWLEDGE_SNIPPETS


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
    text = openai_compat_chat(DASHSCOPE_CHAT_URL, DASHSCOPE_API_KEY, DASHSCOPE_CHAT_MODEL, messages)
    if text:
        return text, refs
    text = openai_compat_chat(DEEPSEEK_CHAT_URL, DEEPSEEK_API_KEY, DEEPSEEK_CHAT_MODEL, messages)
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


def analyze_uploaded_image(file_storage, question=""):
    if not file_storage:
        return "没有收到图片文件。", []
    mime = file_storage.mimetype or ""
    if not mime.startswith("image/"):
        return "请上传 PNG、JPG、JPEG、WebP 等图片文件。", []
    raw = file_storage.read()
    if not raw:
        return "图片文件为空，请重新上传。", []
    if len(raw) > MAX_UPLOAD_IMAGE_BYTES:
        return f"图片太大，请上传小于 {MAX_UPLOAD_IMAGE_BYTES // 1024 // 1024}MB 的图片。", []
    encoded = base64.b64encode(raw).decode("ascii")
    data_url = f"data:{mime};base64,{encoded}"
    prompt = (question or "").strip() or "请用中文分析这张图片：描述主体、场景、细节、可能用途，并给出一句适合配图的文案。"
    answer = call_vision_model({"type": "image_url", "image_url": {"url": data_url}}, prompt)
    flow = workflow_steps(
        ("接收图片", f"{file_storage.filename or '本地图片'} · {mime}"),
        ("转为 Base64", "浏览器上传/拖拽/粘贴的本地图片已转为可识别数据"),
        ("调用视觉模型", DASHSCOPE_VL_MODEL),
        ("返回分析", "展示图片内容理解与文案建议"),
    )
    return answer, flow


def normalize_chat_history(history):
    """清洗前端传入的对话历史，只保留模型需要的 user / assistant 文本。"""
    if not isinstance(history, list):
        return []

    normalized = []
    for item in history[-MAX_CHAT_HISTORY_MESSAGES:]:
        if not isinstance(item, dict):
            continue
        role = item.get("role")
        content = str(item.get("content") or "").strip()
        if role not in {"user", "assistant"} or not content:
            continue
        normalized.append({"role": role, "content": content[:MAX_CHAT_MESSAGE_CHARS]})
    return normalized


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
    global CHAT_HISTORY
    user_text = str(user_text or "").strip()
    assistant_text = str(assistant_text or "").strip()
    if not user_text or not assistant_text:
        return
    CHAT_HISTORY.extend([
        {"role": "user", "content": user_text[:MAX_CHAT_MESSAGE_CHARS]},
        {"role": "assistant", "content": assistant_text[:MAX_CHAT_MESSAGE_CHARS]},
    ])
    CHAT_HISTORY = CHAT_HISTORY[-MAX_CHAT_HISTORY_MESSAGES:]


def ai_chat(query, history=None):
    system_prompt = (
        "你是智能语音助手「小文」。用自然、口语化的中文回答，适合朗读；"
        "回答尽量控制在几句以内，除非用户明确要求长文（如详细讲故事）。"
        "用户可能会问各地美食、讲笑话、讲故事、闲聊等，请友好作答。\n\n"
        + current_datetime_context_for_llm()
    )
    messages = [
        {"role": "system", "content": system_prompt},
        *normalize_chat_history(history),
        {"role": "user", "content": query},
    ]

    text = openai_compat_chat(DASHSCOPE_CHAT_URL, DASHSCOPE_API_KEY, DASHSCOPE_CHAT_MODEL, messages)
    if text:
        return text
    text = openai_compat_chat(DEEPSEEK_CHAT_URL, DEEPSEEK_API_KEY, DEEPSEEK_CHAT_MODEL, messages)
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
    out = openai_compat_chat(
        DASHSCOPE_CHAT_URL, DASHSCOPE_API_KEY, DASHSCOPE_CHAT_MODEL, messages, temperature=0.2
    )
    if out:
        return out
    out = openai_compat_chat(
        DEEPSEEK_CHAT_URL, DEEPSEEK_API_KEY, DEEPSEEK_CHAT_MODEL, messages, temperature=0.2
    )
    if out:
        return out
    if not DASHSCOPE_API_KEY and not DEEPSEEK_API_KEY:
        return MSG_TRANSLATE_NOT_CONFIGURED
    return "翻译失败：模型服务暂时不可用。"


@app.route('/api/translate-selection', methods=['POST'])
def translate_selection():
    try:
        data = request.json or {}
        text = (data.get('text') or '').strip()
        target_lang = (data.get('targetLang') or 'en').strip().lower()
        if target_lang not in {'zh', 'en'}:
            target_lang = 'en'
        if not text:
            return jsonify({"code": 400, "translation": "请选择要翻译的文字。"})
        if len(text) > 2000:
            text = text[:2000]
        return jsonify({"code": 200, "translation": translate_selected_text(text, target_lang)})
    except Exception as e:
        logger.error("translate_selection error: %s", e)
        return jsonify({"code": 500, "translation": f"翻译失败: {str(e)}"})


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
    return (
        "我目前可以帮你打开这些电脑应用：\n"
        f"{ '、'.join(app_names) }。\n"
        "你可以这样说：打开记事本、启动计算器、打开文件管理器、打开 VSCode。"
    )


def is_app_list_query(task):
    """判断用户是否在询问可打开哪些应用。"""
    t = task.strip().lower()
    return (
        any(x in t for x in ["可以打开什么", "能打开什么", "支持打开什么", "可以启动什么", "能启动什么"])
        and any(x in t for x in ["应用", "软件", "程序", "app"])
    )


def find_windows_shortcut(keyword):
    """在当前用户桌面、公共桌面和开始菜单中查找应用快捷方式。"""
    search_dirs = [
        Path.home() / "Desktop",
        Path(os.environ.get("PUBLIC", "C:/Users/Public")) / "Desktop",
        Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs",
        Path(os.environ.get("PROGRAMDATA", "C:/ProgramData")) / "Microsoft" / "Windows" / "Start Menu" / "Programs",
    ]
    keyword_lower = keyword.lower()
    for directory in search_dirs:
        if not directory.exists():
            continue
        for shortcut in directory.rglob("*.lnk"):
            if keyword_lower in shortcut.stem.lower():
                return shortcut
    return None


def launch_shortcut(keyword):
    """打开桌面或开始菜单中的快捷方式。"""
    shortcut = find_windows_shortcut(keyword)
    if not shortcut:
        return False
    os.startfile(str(shortcut))
    return True


def launch_local_app(task):
    """打开本机白名单应用。返回 (是否成功, 提示信息)。"""
    app_name = extract_app_name(task)
    if not app_name:
        return False, "请告诉我要打开哪个应用，例如：打开记事本、打开计算器。"

    matched_name = None
    command = None
    for name, cmd in APP_LAUNCHERS.items():
        if name.lower() in app_name or app_name in name.lower():
            matched_name = name
            command = cmd
            break

    if not command:
        supported = "、".join(sorted(APP_LAUNCHERS.keys()))
        return False, f"暂时不支持打开「{app_name}」。当前支持：{supported}。"

    try:
        if command.startswith("shortcut:"):
            keyword = command.split(":", 1)[1]
            if launch_shortcut(keyword):
                return True, f"已为你打开：{matched_name}"
            return False, f"没有在桌面或开始菜单找到「{keyword}」快捷方式，请确认快捷方式名称包含“{keyword}”。"

        # Windows 内置 start 需要 shell=True；白名单固定命令，避免执行用户输入。
        subprocess.Popen(command, shell=True)
        return True, f"已为你打开：{matched_name}"
    except Exception as e:
        logger.error("Launch app failed: %s", e)
        return False, f"打开「{matched_name}」失败，可能是应用未安装或不在系统 PATH 中。"


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
    """优先用前端传来的 history，否则用服务端内存里的上一轮对话。"""
    norm = normalize_chat_history(chat_history)
    if norm:
        return norm
    return list(CHAT_HISTORY)


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
    if WORLD_STATE is None:
        payload = {"mode": "normal", "modeLabel": "普通助手"}
    else:
        payload = {
            "mode": "world",
            "modeLabel": f"{WORLD_STATE['theme']}世界中",
            "worldState": public_world_state(WORLD_STATE),
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


def world_status_text(state):
    return (
        f"【状态】第 {state['day']} 天 · {state['time']}｜生命 {state['hp']}｜精力 {state['energy']}｜饥饿 {state['hunger']}\n"
        f"【世界】{state['theme']}｜种子 {state['seed']}｜核心：{state['core']}\n"
        f"【身份】{state['realm']}｜安全 {state['safety']}｜机缘 {state['luck']}｜敌意 {state['hostility']}\n"
        f"【位置】{state['location']}\n"
        f"【背包】{ '、'.join(state['inventory']) if state['inventory'] else '空' }"
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


def render_world_intro(state):
    suggestions = "、".join(world_suggestions(state))
    return (
        f"已为你生成一个【{state['theme']}】文字模拟世界。\n\n"
        f"【世界种子】{state['seed']}\n"
        f"【世界核心】{state['core']}\n"
        f"【出生地点】{state['location']}\n"
        f"【当前场景】{state['scene']}\n"
        f"【初始资源】{ '、'.join(state['inventory']) }\n\n"
        f"你已经出生在这里。模拟世界已锁定，后续对话都会发生在这个世界里。只有输入“退出模拟”才会回到普通助手。\n\n"
        f"{world_status_text(state)}\n\n"
        f"【行动建议】{suggestions}"
    )


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
    t = task.strip()
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
    if any(x in t for x in ["战斗", "攻击", "迎战", "打", "猎杀"]):
        return "fight"
    if any(x in t for x in ["交易", "卖", "买", "去宗门", "宗门", "小镇", "集市"]):
        return "trade"
    if any(x in t for x in ["生存", "过一天", "一天"]):
        return "survive_day"
    if any(x in t for x in ["继续", "附近", "向北", "向南", "向东", "向西", "走", "前进", "探索", "冒险", "看看周围"]):
        return "explore"
    return "observe"


def apply_world_action(task):
    global WORLD_STATE
    if WORLD_STATE is None or any(x in task for x in ["生成", "创建", "新开", "重新", "开一个", "来一个"]):
        WORLD_STATE = create_world(task)
        return render_world_intro(WORLD_STATE)

    state = WORLD_STATE
    data = WORLD_THEMES[state["theme"]]
    event = random.choice(data["events"])
    found = random.choice(data["resources"])
    scene = random.choice(data["scenes"])
    action = classify_world_action(task)
    changes = []

    if action == "status":
        return f"{world_status_text(state)}\n\n【行动建议】{ '、'.join(world_suggestions(state)) }"

    if action == "eat":
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
        WORLD_STATE = None
        return "\n".join(changes + [ending])

    return (
        f"【世界事件】{event}\n"
        f"{chr(10).join(changes)}\n\n"
        f"{world_status_text(state)}\n\n"
        f"【行动建议】{ '、'.join(world_suggestions(state)) }"
    )


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
        "图表", "折线图", "线形图", "线型图", "柱状图", "条形图", "柱形图", "趋势图",
        "可视化", "数据分析", "统计图", "数据图", "画图", "作图", "生成图",
    ]
    if any(word in t for word in chart_words):
        return True
    # 「生成/模拟…数据」且同时要图（如：帮我生成一份数据和图表）
    has_viz = any(
        x in t
        for x in ["图表", "柱状", "折线", "条形", "可视化", "趋势", "统计图", "图"]
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
    if any(x in task for x in ["折线", "线形", "线型", "趋势", "line"]):
        return "line"
    if any(x in task for x in ["条形", "柱状", "柱形", "bar"]):
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


def parse_command(task, chat_history=None):
    """统一指令路由入口。

    处理顺序很重要：全局告别优先级最高，其次是模拟世界锁定，
    然后才进入天气、音乐、模拟世界创建、图片、应用和普通聊天等分支。
    每个分支会附带 mode 信息，前端据此显示模式栏或执行 resetUI。
    """
    global WORLD_STATE, CHAT_HISTORY
    task = task.strip()

    if is_goodbye_intent(task):
        WORLD_STATE = None
        CHAT_HISTORY = []
        return {
            "type": "goodbye",
            "msg": "再见，我会在这里等你。需要我的时候，随时叫我小文。",
            "resetUI": True,
            **current_mode_payload(),
        }

    if WORLD_STATE is not None:
        if is_world_exit_intent(task):
            WORLD_STATE = None
            CHAT_HISTORY = []
            return {"type": "chat", "msg": "已退出模拟世界，回到小文普通助手模式。你可以继续聊天、查天气、播放音乐或生成图片。", **current_mode_payload()}
        return {"type": "chat", "msg": apply_world_action(task), **current_mode_payload()}

    if is_app_list_query(task):
        return with_workflow(
            {"type": "app", "msg": supported_app_message(), **current_mode_payload()},
            ("接收指令", task),
            ("识别意图", "用户询问可启动的本机应用"),
            ("返回结果", "展示白名单应用列表"),
        )

    if is_knowledge_intent(task):
        answer, refs = ai_answer_with_knowledge(task)
        sources = "、".join(f"{r['source']}#{r['index']}" for r in refs)
        return with_workflow(
            {"type": "chat", "msg": answer, "knowledgeSources": sources, **current_mode_payload({"mode": "knowledge", "modeLabel": "知识库问答"})},
            ("接收问题", task),
            ("检索知识库", sources or "项目 README / 汇总文档"),
            ("生成回答", "基于检索片段组织答案"),
        )

    if is_image_lookup_intent(task):
        query = extract_image_search_query(task, chat_history)
        if not query:
            return with_workflow(
                {
                    "type": "chat",
                    "msg": (
                        "我还没对上你想看哪道菜或哪个东西。你可以：\n"
                        "· 直接说「白洋淀鱼头汤 图片」\n"
                        "· 或先让小文推荐美食，再说「帮我搜一下图片我想看看」（我会用上一条回复里的名字）"
                    ),
                    **current_mode_payload({"mode": "web", "modeLabel": "图片搜索"}),
                },
                ("接收指令", task),
                ("解析搜索词", "未从对话中识别具体名称"),
                ("返回提示", "引导用户补充关键词"),
            )
        encoded = urllib.parse.quote(query)
        image_search_url = f"https://image.baidu.com/search/index?tn=baiduimage&word={encoded}"
        return with_workflow(
            {
                "type": "web",
                "msg": f"已为你准备「{query}」的图片搜索，点击下方链接在浏览器里浏览实物图（结果来自搜索引擎）。",
                "previewUrl": image_search_url,
                **current_mode_payload({"mode": "web", "modeLabel": "图片搜索"}),
            },
            ("接收指令", task),
            ("提取关键词", query),
            ("生成链接", "百度图片搜索"),
            ("返回结果", "前端展示可点击链接"),
        )

    if is_image_understanding_intent(task):
        answer, image_url = ai_understand_image(task)
        return with_workflow(
            {"type": "chat", "msg": answer, "imageUnderstandingUrl": image_url, **current_mode_payload({"mode": "vision", "modeLabel": "图片理解"})},
            ("接收图片", image_url or "未提供图片链接"),
            ("调用视觉模型", "识别图片内容并生成描述"),
            ("返回结果", "展示图片理解结论"),
        )

    if is_chart_intent(task):
        # 数据可视化入口：用户输入“生成折线图/柱状图 + 数据”时，在后端先解析数据，
        # 再返回 chartData 给前端 ChartPanel；无具体数字时可自动生成模拟数据。
        try:
            points, data_source = resolve_chart_points_from_task(task)
            chart_payload = build_chart_payload(task, points, data_source)
            parse_detail = "自动生成演示数据" if data_source.startswith("模拟") else "从文本中提取标签和值"
            return with_workflow(
                chart_payload,
                ("接收图表指令", task),
                ("解析数据", parse_detail),
                ("选择图表", "折线图 / 柱状图自动匹配"),
                ("生成图表", "前端 SVG 可视化渲染"),
            )
        except ValueError as e:
            return with_workflow(
                {"type": "chat", "msg": str(e), **current_mode_payload({"mode": "chart", "modeLabel": "数据可视化"})},
                ("接收图表指令", task),
                ("解析数据", "未识别到足够的标签和值"),
                ("返回提示", "引导用户输入数据或上传文件"),
            )

    if "天气" in task:
        city = extract_city(task)
        data = get_weather_info(city)
        msg = f"{data['city']}今天{data['weather']}，气温{data['temperature']}，{data['wind']}，湿度{data['humidity']}"
        return with_workflow(
            {"type": "weather", "msg": msg, "extraData": data, **current_mode_payload()},
            ("接收指令", task),
            ("提取城市", city),
            ("调用天气服务", "高德地图天气接口"),
            ("展示结果", msg),
        )

    if is_music_intent(task):
        music_url, song_name, music_provider, qishui_url, qishui_embed_url = search_music_url(task)
        is_qishui = music_provider == "qishui"
        return with_workflow(
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
            ("接收指令", task),
            ("提取歌曲", song_name),
            ("搜索可播放音频", "优先返回浏览器 audio 可直接播放的试听源" if not is_qishui else "用户指定汽水音乐时打开官方入口"),
            ("进入播放", "前端播放器立即加载音频并自动播放" if not is_qishui else "官方页面负责登录和播放"),
        )

    if is_world_create_intent(task):
        return with_workflow(
            {"type": "chat", "msg": apply_world_action(task), **current_mode_payload()},
            ("接收指令", task),
            ("创建模拟世界", "生成世界种子、出生点和初始状态"),
            ("锁定模式", "进入文字模拟世界"),
        )

    if is_image_intent(task):
        prompt = extract_image_prompt(task)
        task_id = dashscope_submit_image(prompt) if DASHSCOPE_API_KEY else None
        if task_id:
            return with_workflow(
                {"type": "image_pending", "msg": f"正在生成：{prompt}", "taskId": task_id, "prompt": prompt, **current_mode_payload({"mode": "image", "modeLabel": "图片生成中"})},
                ("接收绘图指令", task),
                ("提取提示词", prompt),
                ("提交文生图任务", "DashScope 异步任务"),
                ("前端轮询", "等待图片生成完成"),
            )
        image_url = generate_image(prompt)
        return with_workflow(
            {"type": "image", "msg": f"正在为你生成：{prompt}", "imageUrl": image_url, "prompt": prompt, **current_mode_payload({"mode": "image", "modeLabel": "图片已生成"})},
            ("接收绘图指令", task),
            ("提取提示词", prompt),
            ("生成图片", "同步生成或兜底接口"),
            ("展示结果", "前端图片预览"),
        )

    if any(task.startswith(prefix) for prefix in ["打开", "启动", "运行", "开启", "帮我打开", "帮我启动", "请打开"]):
        success, msg = launch_local_app(task)
        if success:
            return with_workflow(
                {"type": "app", "msg": msg, **current_mode_payload()},
                ("接收指令", task),
                ("匹配白名单", "只允许启动安全应用"),
                ("执行启动", msg),
            )
        if "网页" not in task and "网站" not in task and "百度" not in task and "抖音" not in task:
            return with_workflow(
                {"type": "chat", "msg": msg, **current_mode_payload()},
                ("接收指令", task),
                ("匹配白名单", "未找到支持的本机应用"),
                ("返回提示", msg),
            )

    if "打开" in task:
        site = task.replace("打开", "").strip()
        if "百度" in site:
            return with_workflow(
                {"type": "web", "msg": "正在打开百度", "previewUrl": "https://www.baidu.com", **current_mode_payload()},
                ("接收指令", task),
                ("识别网页", "百度"),
                ("返回链接", "https://www.baidu.com"),
            )
        if "抖音" in site:
            return with_workflow(
                {"type": "web", "msg": "正在打开抖音", "previewUrl": "https://www.douyin.com", **current_mode_payload()},
                ("接收指令", task),
                ("识别网页", "抖音"),
                ("返回链接", "https://www.douyin.com"),
            )
        search_url = f"https://www.baidu.com/s?wd={urllib.parse.quote(site)}"
        return with_workflow(
            {"type": "web", "msg": f"正在搜索：{site}", "previewUrl": search_url, **current_mode_payload()},
            ("接收指令", task),
            ("生成搜索词", site),
            ("返回搜索链接", search_url),
        )

    return with_workflow(
        {"type": "chat", "msg": ai_chat(task, normalize_chat_history(chat_history) or CHAT_HISTORY), **current_mode_payload()},
        ("接收问题", task),
        ("整理上下文", "携带最近多轮对话"),
        ("调用对话模型", primary_chat_model_label()),
        ("返回回答", "展示在小文回复卡片"),
    )

@app.route('/api/image-status/<task_id>', methods=['GET'])
def image_status(task_id):
    """前端轮询：查询图片生成进度。
    返回 { status: 'pending'|'succeeded'|'failed', imageUrl? }
    """
    try:
        status, url = dashscope_poll_image(task_id)
        resp = {"status": status}
        if url:
            resp["imageUrl"] = url
        return jsonify(resp)
    except Exception as e:
        logger.error("image_status error: %s", e)
        return jsonify({"status": "failed"})


# -------------------------- 核心接口 --------------------------
@app.route('/api/analyze-image', methods=['POST'])
def analyze_image_upload():
    try:
        file_storage = request.files.get('image')
        question = request.form.get('question', '')
        answer, flow = analyze_uploaded_image(file_storage, question)
        return jsonify({
            "code": 200,
            "reply": answer,
            "type": "chat",
            "mode": "vision",
            "modeLabel": "图片理解",
            "workflow": flow,
        })
    except Exception as e:
        logger.error("analyze_image_upload error: %s", e)
        return jsonify({"code": 500, "reply": f"图片分析失败: {str(e)}", "type": "chat"})


@app.route('/api/generate-chart', methods=['POST'])
def generate_chart_upload():
    """文件生成图表接口。

    前端通过 FormData 上传文件和 task：
    - file：CSV / TXT / TSV / Excel 数据文件；
    - task：用户当前输入，用于判断折线图还是柱状图。
    后端解析完成后返回 chartData，由前端 SVG 组件负责绘制。
    """
    try:
        task = request.form.get('task', '生成柱状图')
        file_storage = request.files.get('file')
        if file_storage and file_storage.filename:
            points = parse_chart_file(file_storage)
            source = file_storage.filename
            if len(points) < 2:
                points, source = (
                    generate_demo_chart_points(task),
                    "模拟示例数据（文件中未解析出至少两组有效数据，已自动生成）",
                )
        else:
            points, source = resolve_chart_points_from_task(task)
        payload = build_chart_payload(task, points, source)
        payload = with_workflow(
            payload,
            ("接收数据", source),
            ("解析数据", "读取前两列作为名称和值"),
            ("统计摘要", "计算总数、最大值、最小值"),
            ("生成图表", "前端 SVG 可视化渲染"),
        )
        return jsonify({
            "code": 200,
            "reply": payload["msg"],
            "type": "chart",
            "chartData": payload["chartData"],
            "mode": payload.get("mode", "chart"),
            "modeLabel": payload.get("modeLabel", "数据可视化"),
            "workflow": payload.get("workflow", []),
        })
    except Exception as e:
        logger.error("generate_chart_upload error: %s", e)
        return jsonify({"code": 400, "reply": f"图表生成失败: {str(e)}", "type": "chat"})


# -------------------------- 核心接口 --------------------------
@app.route('/api/send-task', methods=['POST'])
def send_task():
    try:
        data = request.json
        task = data.get('task', '')
        incoming_history = normalize_chat_history(data.get('history'))
        if not task:
            return jsonify({"code": 400, "reply": "指令不能为空"})
            
        logger.info(f"Received task: {task}")
        res = parse_command(task, incoming_history)
        if res.get("type") == "chat" and not res.get("resetUI"):
            remember_chat_turn(task, res.get("msg", ""))
        
        response = {
            "code": 200,
            "reply": res["msg"],
            "type": res["type"]
        }
        
        if "previewUrl" in res: response["previewUrl"] = res["previewUrl"]
        if "musicProvider" in res: response["musicProvider"] = res["musicProvider"]
        if "qishuiUrl" in res: response["qishuiUrl"] = res["qishuiUrl"]
        if "qishuiEmbedUrl" in res: response["qishuiEmbedUrl"] = res["qishuiEmbedUrl"]
        if "songName" in res: response["songName"] = res["songName"]
        if "imageUrl" in res: response["imageUrl"] = res["imageUrl"]
        if "taskId" in res: response["taskId"] = res["taskId"]
        if "prompt" in res: response["prompt"] = res["prompt"]
        if "extraData" in res: response["extraData"] = res["extraData"]
        if "mode" in res: response["mode"] = res["mode"]
        if "modeLabel" in res: response["modeLabel"] = res["modeLabel"]
        if "worldState" in res: response["worldState"] = res["worldState"]
        if "quickActions" in res: response["quickActions"] = res["quickActions"]
        if "resetUI" in res: response["resetUI"] = res["resetUI"]
        if "workflow" in res: response["workflow"] = res["workflow"]
        if "knowledgeSources" in res: response["knowledgeSources"] = res["knowledgeSources"]
        if "chartData" in res: response["chartData"] = res["chartData"]
        if "imageUnderstandingUrl" in res: response["imageUnderstandingUrl"] = res["imageUnderstandingUrl"]
            
        return jsonify(response)
    except Exception as e:
        logger.error(f"Server Error: {e}")
        return jsonify({"code": 500, "reply": f"服务器内部错误: {str(e)}"})

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5001, debug=True)
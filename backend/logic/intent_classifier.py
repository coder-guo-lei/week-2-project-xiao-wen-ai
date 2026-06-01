"""意图分类：LLM 主判 + 规则兜底 + 进程内 TTL 缓存。"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any

from config import (
    DASHSCOPE_API_KEY,
    DEEPSEEK_API_KEY,
    INTENT_CACHE_MAX,
    INTENT_CACHE_TTL,
    INTENT_LLM_ENABLED,
    INTENT_RULE_CONFIDENCE,
)

logger = logging.getLogger(__name__)

# 与 parse_command 分支一一对应（world 内动作由 session 状态单独处理）
INTENT_GOODBYE = "goodbye"
INTENT_APP_LIST = "app_list"
INTENT_KNOWLEDGE = "knowledge"
INTENT_IMAGE_LOOKUP = "image_lookup"
INTENT_IMAGE_UNDERSTANDING = "image_understanding"
INTENT_CHART = "chart"
INTENT_WEATHER = "weather"
INTENT_MUSIC_NAV = "music_nav"
INTENT_MUSIC = "music"
INTENT_LOCAL_FOOD = "local_food"
INTENT_WORLD_CREATE = "world_create"
INTENT_IMAGE_GENERATE = "image_generate"
INTENT_APP_LAUNCH = "app_launch"
INTENT_WEB_OPEN = "web_open"
INTENT_CHAT = "chat"

_ALL_INTENTS = (
    INTENT_GOODBYE,
    INTENT_APP_LIST,
    INTENT_KNOWLEDGE,
    INTENT_IMAGE_LOOKUP,
    INTENT_IMAGE_UNDERSTANDING,
    INTENT_CHART,
    INTENT_WEATHER,
    INTENT_MUSIC_NAV,
    INTENT_MUSIC,
    INTENT_LOCAL_FOOD,
    INTENT_WORLD_CREATE,
    INTENT_IMAGE_GENERATE,
    INTENT_APP_LAUNCH,
    INTENT_WEB_OPEN,
    INTENT_CHAT,
)

_LLM_SYSTEM = """你是智能语音助手「小文」的意图分类器。根据用户一句话，从下列标签中选唯一最匹配 intent。
只输出一行 JSON，不要 markdown，不要解释。格式：{"intent":"标签","confidence":0.0到1.0}

标签说明：
- goodbye：告别小文、退出助手（含「再见小文」「拜拜小文」）
- app_list：询问能打开哪些应用/软件（不是具体打开某个）
- knowledge：查项目文档/README/知识库
- image_lookup：在网上搜实物图、看长什么样（非 AI 生图）
- image_understanding：分析/识别用户给出的图片链接
- chart：生成折线图/柱状图/数据可视化
- weather：查天气、气温、出行是否与天气相关
- music_nav：仅切歌（下一首/上一首/换一首），不含具体歌名
- music：播放/听/点歌/来一首（含具体歌名）
- local_food：饿了、附近吃什么、美食推荐
- world_create：创建修仙/末日/奇幻等文字模拟世界
- image_generate：AI 画一张图/文生图/生成图片
- app_launch：打开/启动本机应用（微信、记事本、VSCode 等）
- web_open：打开网页或百度搜索（含打开百度/抖音网页）
- chat：闲聊、问答、讲笑话故事、其它未覆盖需求

注意：「听个故事/讲笑话」→ chat；「听首歌/播放稻香」→ music；「今天北京天气」→ weather；「画一只猫」→ image_generate。"""


@dataclass(frozen=True)
class IntentResult:
    intent: str
    confidence: float
    source: str  # cache | rule | llm | rule_fallback
    detail: str = ""


class _IntentCache:
    """LRU + TTL 进程内缓存。"""

    def __init__(self, max_size: int, ttl_sec: int):
        self._max = max(16, max_size)
        self._ttl = max(60, ttl_sec)
        self._data: OrderedDict[str, tuple[float, IntentResult]] = OrderedDict()

    def _make_key(self, task: str, ctx: dict[str, Any]) -> str:
        norm = re.sub(r"\s+", "", (task or "").strip().lower())
        flags = f"h={1 if ctx.get('has_history') else 0}|loc={1 if ctx.get('has_location') else 0}"
        raw = f"{norm}|{flags}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def get(self, task: str, ctx: dict[str, Any]) -> IntentResult | None:
        key = self._make_key(task, ctx)
        hit = self._data.get(key)
        if not hit:
            return None
        ts, result = hit
        if time.time() - ts > self._ttl:
            self._data.pop(key, None)
            return None
        self._data.move_to_end(key)
        return IntentResult(result.intent, result.confidence, "cache", result.detail)

    def set(self, task: str, ctx: dict[str, Any], result: IntentResult) -> None:
        key = self._make_key(task, ctx)
        self._data[key] = (time.time(), result)
        self._data.move_to_end(key)
        while len(self._data) > self._max:
            self._data.popitem(last=False)


_CACHE = _IntentCache(INTENT_CACHE_MAX, INTENT_CACHE_TTL)


def _normalize_intent(raw: str) -> str:
    v = (raw or "").strip().lower()
    aliases = {
        "image_gen": INTENT_IMAGE_GENERATE,
        "text2img": INTENT_IMAGE_GENERATE,
        "image_search": INTENT_IMAGE_LOOKUP,
        "vision": INTENT_IMAGE_UNDERSTANDING,
        "food": INTENT_LOCAL_FOOD,
        "nearby_food": INTENT_LOCAL_FOOD,
        "world": INTENT_WORLD_CREATE,
        "app": INTENT_APP_LAUNCH,
        "web": INTENT_WEB_OPEN,
        "general": INTENT_CHAT,
        "conversation": INTENT_CHAT,
    }
    if v in aliases:
        return aliases[v]
    return v if v in _ALL_INTENTS else INTENT_CHAT


def rule_classify_intent(task: str, context: dict[str, Any] | None = None) -> IntentResult:
    """规则兜底：沿用原有 is_* / 正则逻辑，按 parse_command 优先级返回首个命中。"""
    from logic import task_parser as tp

    ctx = context or {}
    t = (task or "").strip()

    if tp.is_goodbye_intent(t):
        return IntentResult(INTENT_GOODBYE, 1.0, "rule", "告别语强匹配")

    if tp.is_app_list_query(t):
        return IntentResult(INTENT_APP_LIST, 0.95, "rule", "应用清单问询")

    if tp.is_knowledge_intent(t):
        return IntentResult(INTENT_KNOWLEDGE, 0.95, "rule", "知识库关键词")

    if tp.is_image_lookup_intent(t):
        return IntentResult(INTENT_IMAGE_LOOKUP, 0.9, "rule", "网页搜图")

    if tp.is_image_understanding_intent(t):
        return IntentResult(INTENT_IMAGE_UNDERSTANDING, 0.92, "rule", "图片理解")

    if tp.is_chart_intent(t):
        return IntentResult(INTENT_CHART, 0.9, "rule", "图表/可视化")

    if "天气" in t and not tp.task_should_skip_weather_branch(t):
        return IntentResult(INTENT_WEATHER, 0.88, "rule", "天气关键词")

    nav = tp.parse_music_navigation(t)
    if nav:
        return IntentResult(INTENT_MUSIC_NAV, 0.95, "rule", f"切歌:{nav}")

    if tp.is_music_intent(t):
        return IntentResult(INTENT_MUSIC, 0.85, "rule", "音乐播放")

    if ctx.get("music_followup"):
        return IntentResult(INTENT_MUSIC, 0.82, "rule", "音乐语种跟唱")

    if tp.is_local_life_food_intent(t):
        return IntentResult(INTENT_LOCAL_FOOD, 0.85, "rule", "附近美食")

    if tp.is_world_create_intent(t):
        return IntentResult(INTENT_WORLD_CREATE, 0.88, "rule", "创建模拟世界")

    if tp.is_image_intent(t):
        return IntentResult(INTENT_IMAGE_GENERATE, 0.85, "rule", "文生图")

    open_prefixes = ("打开", "启动", "运行", "开启", "帮我打开", "帮我启动", "请打开")
    if any(t.startswith(p) for p in open_prefixes):
        if tp.wants_douyin_web_open(t):
            return IntentResult(INTENT_WEB_OPEN, 0.9, "rule", "抖音网页")
        return IntentResult(INTENT_APP_LAUNCH, 0.8, "rule", "打开/启动前缀")

    if "打开" in t:
        return IntentResult(INTENT_WEB_OPEN, 0.75, "rule", "打开+搜索/网页")

    return IntentResult(INTENT_CHAT, 0.5, "rule", "默认对话")


def _llm_classify_intent(task: str, context: dict[str, Any] | None = None) -> IntentResult | None:
    if not INTENT_LLM_ENABLED or not (DASHSCOPE_API_KEY or DEEPSEEK_API_KEY):
        return None
    from logic.task_parser import openai_compat_chat_fallback

    ctx = context or {}
    hints = []
    if ctx.get("has_history"):
        hints.append("用户有多轮对话上下文")
    if ctx.get("has_location"):
        hints.append("前端已传浏览器定位")
    user = f"用户说：{task.strip()[:500]}"
    if hints:
        user += "\n上下文：" + "；".join(hints)

    raw = openai_compat_chat_fallback(
        [
            {"role": "system", "content": _LLM_SYSTEM},
            {"role": "user", "content": user},
        ],
        temperature=0.0,
    )
    if not raw:
        return None

    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{[^{}]+\}", text)
        if not m:
            logger.warning("intent LLM 返回非 JSON: %s", raw[:120])
            return None
        try:
            data = json.loads(m.group(0))
        except json.JSONDecodeError:
            return None

    intent = _normalize_intent(str(data.get("intent", "")))
    try:
        conf = float(data.get("confidence", 0.75))
    except (TypeError, ValueError):
        conf = 0.75
    conf = max(0.0, min(1.0, conf))
    return IntentResult(intent, conf, "llm", "LLM 意图分类")


def classify_intent(task: str, context: dict[str, Any] | None = None) -> IntentResult:
    """主入口：缓存 → 规则高置信短路 → LLM → 规则兜底。"""
    ctx = dict(context or {})
    t = (task or "").strip()
    if not t:
        return IntentResult(INTENT_CHAT, 1.0, "rule", "空输入")

    cached = _CACHE.get(t, ctx)
    if cached:
        return cached

    rule_hit = rule_classify_intent(t, ctx)

    # 高置信规则直接采用，避免多余 LLM 调用
    if rule_hit.confidence >= INTENT_RULE_CONFIDENCE:
        _CACHE.set(t, ctx, rule_hit)
        logger.debug("intent rule-fast %s (%.2f) %s", rule_hit.intent, rule_hit.confidence, t[:40])
        return rule_hit

    llm_hit = _llm_classify_intent(t, ctx)
    if llm_hit and llm_hit.confidence >= 0.55:
        # LLM 判 chat 但规则有中等置信专项意图时，规则优先（避免误落闲聊）
        if llm_hit.intent == INTENT_CHAT and rule_hit.intent != INTENT_CHAT and rule_hit.confidence >= 0.75:
            result = IntentResult(rule_hit.intent, rule_hit.confidence, "rule_fallback", rule_hit.detail)
        else:
            result = llm_hit
    else:
        result = IntentResult(rule_hit.intent, rule_hit.confidence, "rule_fallback", rule_hit.detail)

    _CACHE.set(t, ctx, result)
    logger.info(
        "intent %s (%.2f, %s) task=%s",
        result.intent,
        result.confidence,
        result.source,
        t[:60],
    )
    return result


def intent_workflow_label(result: IntentResult) -> str:
    """供 workflow 展示的人类可读意图摘要。"""
    names = {
        INTENT_GOODBYE: "告别",
        INTENT_APP_LIST: "应用清单",
        INTENT_KNOWLEDGE: "知识库问答",
        INTENT_IMAGE_LOOKUP: "网页搜图",
        INTENT_IMAGE_UNDERSTANDING: "图片理解",
        INTENT_CHART: "数据图表",
        INTENT_WEATHER: "天气查询",
        INTENT_MUSIC_NAV: "音乐切歌",
        INTENT_MUSIC: "音乐播放",
        INTENT_LOCAL_FOOD: "附近美食",
        INTENT_WORLD_CREATE: "创建模拟世界",
        INTENT_IMAGE_GENERATE: "AI 文生图",
        INTENT_APP_LAUNCH: "启动本机应用",
        INTENT_WEB_OPEN: "打开网页/搜索",
        INTENT_CHAT: "通用对话",
    }
    label = names.get(result.intent, result.intent)
    src = {"cache": "缓存", "rule": "规则", "llm": "LLM", "rule_fallback": "规则兜底"}.get(result.source, result.source)
    return f"{label}（{src}·{result.confidence:.0%}）"

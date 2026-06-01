"""轻量全网检索：百度结果页摘要解析（无需额外 API Key）。"""
import logging
import re
import urllib.parse

import requests

from config import REQUEST_TIMEOUT

logger = logging.getLogger(__name__)

_WEB_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def _strip_html(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text or "")).strip()


def search_web_snippets(query: str, limit: int = 5) -> list[dict]:
    """
    从百度搜索结果页提取标题与摘要。
    返回 [{"title", "snippet", "url"}, ...]
    """
    q = (query or "").strip()
    if not q:
        return []

    results: list[dict] = []
    try:
        resp = requests.get(
            "https://www.baidu.com/s",
            params={"wd": q, "rn": max(limit, 5), "ie": "utf-8"},
            headers={
                "User-Agent": _WEB_UA,
                "Accept-Language": "zh-CN,zh;q=0.9",
            },
            timeout=REQUEST_TIMEOUT,
        )
        resp.encoding = "utf-8"
        html = resp.text

        # 标题：<!--s-text-->…</span>；摘要：class 含 c-abstract
        title_pat = re.compile(r"<!--s-text-->(.*?)</span>", re.S)
        abstract_pat = re.compile(
            r'class="[^"]*c-abstract[^"]*"[^>]*>.*?<!--s-text-->(.*?)</span>',
            re.S,
        )
        titles = [_strip_html(t) for t in title_pat.findall(html)]
        abstracts = [_strip_html(a) for a in abstract_pat.findall(html)]

        for i in range(min(limit, max(len(titles), len(abstracts)))):
            title = titles[i] if i < len(titles) else ""
            snippet = abstracts[i] if i < len(abstracts) else ""
            if not title and not snippet:
                continue
            results.append({
                "title": title,
                "snippet": snippet,
                "url": "",
            })

    except Exception as e:
        logger.warning("web search failed: %s", e)

    if not results:
        search_url = f"https://www.baidu.com/s?wd={urllib.parse.quote(q)}"
        results.append({
            "title": "百度搜索",
            "snippet": f"未能自动解析网页摘要，可点击链接在浏览器中查看「{q}」的搜索结果。",
            "url": search_url,
        })
    return results[:limit]

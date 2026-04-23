import json
from typing import Dict, Any, List, Optional

import httpx
from bs4 import BeautifulSoup
from readability import Document

from playwright.async_api import async_playwright, Browser, Page
import atexit

DEFAULT_TIMEOUT = 10.0


async def _tidy_text(text: str) -> str:
    """清理文本，去除多余空白和换行符"""
    if not text:
        return ""
    return " ".join(text.strip().split())

async def search_tavily(
    query: str,
    api_key: str,
    max_results: int = 7,
    search_depth: str = "basic",
    topic: str = "general",
    days: int = 3,
    time_range: str = "",
    start_date: str = "",
    end_date: str = "",
) -> str:
    """
    使用 Tavily API 进行网络搜索。

    Args:
        query: 搜索查询
        api_key: Tavily API 密钥
        max_results: 最大结果数（5-20，默认 7）
        search_depth: 搜索深度，"basic" 或 "advanced"
        topic: 主题，"general" 或 "news"
        days: 新闻搜索时回溯的天数（仅当 topic="news" 时生效）
        time_range: 时间范围，"day", "week", "month", "year"
        start_date: 起始日期 YYYY-MM-DD
        end_date: 结束日期 YYYY-MM-DD

    Returns:
        JSON 字符串，包含 results 列表，每个结果包含 title, url, snippet, index
    """
    url = "https://api.tavily.com/search"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload: Dict[str, Any] = {
        "query": query,
        "max_results": max_results,
        "include_favicon": True,
        "search_depth": search_depth if search_depth in ("basic", "advanced") else "basic",
        "topic": topic if topic in ("general", "news") else "general",
    }

    if topic == "news":
        payload["days"] = days
    if time_range in ("day", "week", "month", "year"):
        payload["time_range"] = time_range
    if start_date:
        payload["start_date"] = start_date
    if end_date:
        payload["end_date"] = end_date

    async with httpx.AsyncClient() as client:
        resp = await client.post(url, json=payload, headers=headers, timeout=30.0)
        if resp.status_code != 200:
            raise Exception(f"Tavily API error: {resp.text} (status {resp.status_code})")
        data = resp.json()

    results = []
    for item in data.get("results", []):
        results.append({
            "title": item.get("title", ""),
            "url": item.get("url", ""),
            "snippet": item.get("content", ""),
            "favicon": item.get("favicon", ""),
        })

    if not results:
        return "Error: Tavily search returned no results."

    ref_uuid = str(hash(query))[-4:]
    for idx, res in enumerate(results, 1):
        res["index"] = f"{ref_uuid}.{idx}"

    return json.dumps({"results": results}, ensure_ascii=False)

# ---------- Playwright 浏览器单例管理 ----------
_browser: Optional[Browser] = None

async def _get_browser() -> Browser:
    """获取全局复用的浏览器实例（懒加载）"""
    global _browser
    if _browser is None or not _browser.is_connected():
        playwright = await async_playwright().start()
        _browser = await playwright.chromium.launch(
            headless=True,
            args=['--disable-blink-features=AutomationControlled', '--no-sandbox', '--disable-dev-shm-usage']
        )
    return _browser


async def _close_browser():
    """清理浏览器资源（脚本退出时调用）"""
    global _browser
    if _browser:
        await _browser.close()
        _browser = None

atexit.register(lambda: __import__('asyncio').run(_close_browser()))

async def fetch_url(url: str, max_length: int = 2000) -> str:
    """
    使用 Playwright 抓取网页完整渲染内容，并提取可读文本。

    Args:
        url: 要抓取的网页地址
        max_length: 返回文本的最大长度（默认 2000）

    Returns:
        清理后的纯文本内容
    """
    browser = await _get_browser()
    page: Page = await browser.new_page()
    try:
        # 设置合理视口，模拟真实浏览器
        await page.set_viewport_size({"width": 1280, "height": 800})
        # 访问页面，等待网络基本空闲
        await page.goto(url, wait_until="networkidle", timeout=15000)
        # 额外等待一秒，确保懒加载内容触发
        await page.wait_for_timeout(1000)
        
        html = await page.content()
    except Exception as e:
        return f"Error: 网页抓取失败 - {e}"
    finally:
        await page.close()

    # 使用 readability 提取正文
    doc = Document(html)
    summary_html = doc.summary(html_partial=True)
    soup = BeautifulSoup(summary_html, "html.parser")
    text = await _tidy_text(soup.get_text())

    if len(text) > max_length:
        text = text[:max_length] + "..."
    return text

async def search_tavily_list(
    query: str,
    api_key: str,
    max_results: int = 7,
    **kwargs
) -> List[Dict[str, str]]:
    """返回 Tavily 搜索结果的列表形式（不包含 JSON 序列化）"""
    result_json = await search_tavily(query, api_key, max_results, **kwargs)
    if result_json.startswith("Error:"):
        return []
    return json.loads(result_json)["results"]
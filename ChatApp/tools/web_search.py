import json
from typing import Dict, Any, List, Optional

import httpx

DEFAULT_TIMEOUT = 10.0
TAVILY_BASE_URL = "https://api.tavily.com"


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
    include_answer: bool = False,
    include_raw_content: bool = False,
    chunks_per_source: int = 3,
    include_domains: Optional[List[str]] = None,
    exclude_domains: Optional[List[str]] = None,
    country: str = "",
) -> str:
    url = f"{TAVILY_BASE_URL}/search"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    valid_depths = ("basic", "advanced", "fast", "ultra-fast")
    valid_topics = ("general", "news", "finance")

    payload: Dict[str, Any] = {
        "query": query,
        "max_results": max_results,
        "include_favicon": True,
        "search_depth": search_depth if search_depth in valid_depths else "basic",
        "topic": topic if topic in valid_topics else "general",
    }

    if search_depth == "advanced":
        payload["chunks_per_source"] = max(1, min(3, chunks_per_source))

    if topic == "news" and days:
        payload["days"] = days
    if time_range in ("day", "week", "month", "year", "d", "w", "m", "y"):
        payload["time_range"] = time_range
    if start_date:
        payload["start_date"] = start_date
    if end_date:
        payload["end_date"] = end_date
    if include_answer:
        payload["include_answer"] = "basic"
    if include_raw_content:
        payload["include_raw_content"] = "markdown"
    if include_domains:
        payload["include_domains"] = include_domains
    if exclude_domains:
        payload["exclude_domains"] = exclude_domains
    if country and topic == "general":
        payload["country"] = country

    async with httpx.AsyncClient() as client:
        resp = await client.post(url, json=payload, headers=headers, timeout=60.0)
        if resp.status_code != 200:
            raise Exception(f"Tavily API error: {resp.text} (status {resp.status_code})")
        data = resp.json()

    results = []
    for item in data.get("results", []):
        result = {
            "title": item.get("title", ""),
            "url": item.get("url", ""),
            "snippet": item.get("content", ""),
            "favicon": item.get("favicon", ""),
            "score": item.get("score", 0),
        }
        if include_raw_content and item.get("raw_content"):
            result["raw_content"] = item.get("raw_content", "")
        results.append(result)

    output: Dict[str, Any] = {"results": results}

    answer = data.get("answer")
    if answer:
        output["answer"] = answer

    if not results and not answer:
        return "Error: Tavily search returned no results."

    ref_uuid = str(hash(query))[-4:]
    for idx, result in enumerate(results, 1):
        result["index"] = f"{ref_uuid}.{idx}"

    return json.dumps(output, ensure_ascii=False)


async def tavily_extract(
    urls: List[str],
    api_key: str,
    extract_depth: str = "basic",
    format: str = "markdown",
    query: str = "",
    chunks_per_source: int = 3,
    timeout: Optional[float] = None,
) -> str:
    url = f"{TAVILY_BASE_URL}/extract"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    valid_depths = ("basic", "advanced")
    valid_formats = ("markdown", "text")

    payload: Dict[str, Any] = {
        "urls": urls,
        "extract_depth": extract_depth if extract_depth in valid_depths else "basic",
        "format": format if format in valid_formats else "markdown",
        "include_favicon": True,
    }

    if query:
        payload["query"] = query
        payload["chunks_per_source"] = max(1, min(5, chunks_per_source))
    if timeout is not None:
        payload["timeout"] = max(1.0, min(60.0, float(timeout)))

    async with httpx.AsyncClient() as client:
        resp = await client.post(url, json=payload, headers=headers, timeout=90.0)
        if resp.status_code != 200:
            raise Exception(f"Tavily Extract API error: {resp.text} (status {resp.status_code})")
        data = resp.json()

    extracted = []
    for item in data.get("results", []):
        extracted.append({
            "url": item.get("url", ""),
            "content": item.get("raw_content", ""),
            "favicon": item.get("favicon", ""),
        })

    failed = data.get("failed_results", [])

    output: Dict[str, Any] = {"results": extracted}
    if failed:
        output["failed_results"] = failed
    if not extracted and not failed:
        return "Error: Tavily Extract returned no results."

    return json.dumps(output, ensure_ascii=False)


async def tavily_crawl(
    url: str,
    api_key: str,
    instructions: str = "",
    max_depth: int = 1,
    max_breadth: int = 20,
    limit: int = 50,
    extract_depth: str = "basic",
    format: str = "markdown",
    include_images: bool = False,
    timeout: Optional[float] = None,
) -> str:
    endpoint = f"{TAVILY_BASE_URL}/crawl"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    valid_depths = ("basic", "advanced")
    valid_formats = ("markdown", "text")

    payload: Dict[str, Any] = {
        "url": url,
        "max_depth": max(1, min(5, max_depth)),
        "max_breadth": max(1, min(500, max_breadth)),
        "limit": max(1, limit),
        "extract_depth": extract_depth if extract_depth in valid_depths else "basic",
        "format": format if format in valid_formats else "markdown",
        "include_favicon": True,
    }

    if instructions:
        payload["instructions"] = instructions
    if include_images:
        payload["include_images"] = True
    if timeout is not None:
        payload["timeout"] = max(10.0, min(150.0, float(timeout)))

    async with httpx.AsyncClient() as client:
        resp = await client.post(endpoint, json=payload, headers=headers, timeout=180.0)
        if resp.status_code != 200:
            raise Exception(f"Tavily Crawl API error: {resp.text} (status {resp.status_code})")
        data = resp.json()

    results = []
    for item in data.get("results", []):
        results.append({
            "url": item.get("url", ""),
            "content": item.get("raw_content", ""),
            "favicon": item.get("favicon", ""),
        })

    if not results:
        return "Error: Tavily Crawl returned no results."

    return json.dumps({
        "base_url": data.get("base_url", url),
        "results": results,
    }, ensure_ascii=False)


async def tavily_map(
    url: str,
    api_key: str,
    instructions: str = "",
    max_depth: int = 1,
    max_breadth: int = 20,
    limit: int = 50,
    timeout: Optional[float] = None,
) -> str:
    endpoint = f"{TAVILY_BASE_URL}/map"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload: Dict[str, Any] = {
        "url": url,
        "max_depth": max(1, min(5, max_depth)),
        "max_breadth": max(1, min(500, max_breadth)),
        "limit": max(1, limit),
    }

    if instructions:
        payload["instructions"] = instructions
    if timeout is not None:
        payload["timeout"] = max(10.0, min(150.0, float(timeout)))

    async with httpx.AsyncClient() as client:
        resp = await client.post(endpoint, json=payload, headers=headers, timeout=180.0)
        if resp.status_code != 200:
            raise Exception(f"Tavily Map API error: {resp.text} (status {resp.status_code})")
        data = resp.json()

    urls = data.get("results", [])
    if not urls:
        return "Error: Tavily Map returned no URLs."

    return json.dumps({
        "base_url": data.get("base_url", url),
        "urls": urls,
        "total": len(urls),
    }, ensure_ascii=False)


async def search_tavily_list(
    query: str,
    api_key: str,
    max_results: int = 7,
    **kwargs
) -> List[Dict[str, str]]:
    result_json = await search_tavily(query, api_key, max_results, **kwargs)
    if result_json.startswith("Error:"):
        return []
    return json.loads(result_json)["results"]

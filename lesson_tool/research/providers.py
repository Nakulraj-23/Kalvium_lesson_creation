"""Research providers. Each provider is independent: if one fails (rate limit, network,
missing package) the others still return results and the failure is reported, not fatal.

Websites  : DuckDuckGo search (ddgs, no key) + full-page text extraction (trafilatura)
            + Wikipedia API + Gemini Google-Search grounding (optional)
Books     : Google Books API (no key needed) with Open Library as fallback
YouTube   : YouTube Data API v3 if YOUTUBE_API_KEY is set, otherwise yt-dlp search (no key)
"""
from __future__ import annotations

import re
from typing import Optional

import requests

from .reliability import domain_of, tier_for

UA = {"User-Agent": "LessonCreationTool/1.0 (educational research prototype)"}


# ---------------------------------------------------------------- helpers
def relevant_excerpt(text: str, keywords: list[str], max_chars: int = 2500) -> str:
    """Keep the paragraphs that mention the most keywords, in original order."""
    if not text:
        return ""
    paras = [p.strip() for p in re.split(r"\n\s*\n|\n", text) if len(p.strip()) > 40]
    kws = [k.lower() for k in keywords if k]
    scored = []
    for i, p in enumerate(paras):
        low = p.lower()
        scored.append((sum(low.count(k) for k in kws), i, p))
    best = sorted(scored, key=lambda x: (-x[0], x[1]))
    chosen, total = [], 0
    for score, i, p in best:
        if total + len(p) > max_chars:
            continue
        chosen.append((i, p))
        total += len(p)
        if total > max_chars * 0.9:
            break
    return "\n\n".join(p for _, p in sorted(chosen))


def keywords_from(*texts: str) -> list[str]:
    stop = {"the", "and", "for", "with", "between", "explain", "describe", "distinguish", "understand",
            "learn", "how", "what", "into", "from", "their", "this", "that", "of", "to", "in", "a", "an"}
    words = re.findall(r"[A-Za-z0-9]{3,}", " ".join(texts))
    seen, out = set(), []
    for w in words:
        lw = w.lower()
        if lw not in stop and lw not in seen:
            seen.add(lw)
            out.append(lw)
    return out[:20]


def fetch_html(url: str, timeout: int = 15) -> str:
    """Download only (safe to run in threads)."""
    try:
        r = requests.get(url, headers=UA, timeout=timeout)
        r.raise_for_status()
        if "html" not in r.headers.get("content-type", "html"):
            return ""
        return r.text
    except Exception:
        return ""


def extract_text(html_text: str) -> str:
    """Parse with trafilatura/lxml - call from the main thread only (lxml in worker threads
    can crash some macOS Python builds)."""
    if not html_text:
        return ""
    try:
        import trafilatura

        return trafilatura.extract(html_text, include_comments=False, include_tables=True) or ""
    except Exception:
        return ""


def fetch_page_text(url: str, timeout: int = 15) -> str:
    return extract_text(fetch_html(url, timeout))


# ---------------------------------------------------------------- web search
def search_web(query: str, max_results: int = 6) -> list[dict]:
    try:
        from ddgs import DDGS
    except ImportError:  # older package name
        from duckduckgo_search import DDGS  # type: ignore
    with DDGS() as d:
        results = list(d.text(query, max_results=max_results))
    return [{"title": r.get("title", ""), "url": r.get("href", ""), "snippet": r.get("body", "")} for r in results]


def search_wikipedia(query: str, limit: int = 2, timeout: int = 15) -> list[dict]:
    r = requests.get(
        "https://en.wikipedia.org/w/api.php",
        params={"action": "query", "list": "search", "srsearch": query, "srlimit": limit, "format": "json"},
        headers=UA,
        timeout=timeout,
    )
    r.raise_for_status()
    hits = r.json().get("query", {}).get("search", [])
    out = []
    for h in hits:
        title = h["title"]
        r2 = requests.get(
            "https://en.wikipedia.org/w/api.php",
            params={"action": "query", "prop": "extracts", "explaintext": 1, "titles": title, "format": "json"},
            headers=UA,
            timeout=timeout,
        )
        pages = r2.json().get("query", {}).get("pages", {})
        text = next(iter(pages.values()), {}).get("extract", "")
        out.append({"title": f"{title} - Wikipedia", "url": f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}", "text": text})
    return out


def resolve_redirect(url: str, timeout: int = 8) -> str:
    """Gemini grounding returns vertexaisearch redirect URLs; resolve them to the real page."""
    if "grounding-api-redirect" not in url:
        return url
    try:
        r = requests.head(url, allow_redirects=False, timeout=timeout, headers=UA)
        loc = r.headers.get("location")
        if loc:
            return loc
        r = requests.get(url, allow_redirects=True, timeout=timeout, headers=UA, stream=True)
        return r.url
    except Exception:
        return url


# ---------------------------------------------------------------- books
def search_books(query: str, max_results: int = 5, api_key: str = "", timeout: int = 15) -> list[dict]:
    out: list[dict] = []
    try:
        params = {"q": query, "maxResults": max_results, "printType": "books", "langRestrict": "en"}
        if api_key:
            params["key"] = api_key
        r = requests.get("https://www.googleapis.com/books/v1/volumes", params=params, headers=UA, timeout=timeout)
        r.raise_for_status()
        for it in r.json().get("items", []) or []:
            v = it.get("volumeInfo", {})
            out.append(
                {
                    "title": v.get("title", "") + (f": {v['subtitle']}" if v.get("subtitle") else ""),
                    "authors": v.get("authors", []),
                    "year": (v.get("publishedDate") or "")[:4] or None,
                    "url": v.get("infoLink") or v.get("canonicalVolumeLink") or "",
                    "description": v.get("description", "")[:1200],
                    "publisher": v.get("publisher", ""),
                }
            )
    except Exception:
        out = []
    if out:
        return out
    # fallback: Open Library
    r = requests.get("https://openlibrary.org/search.json", params={"q": query, "limit": max_results}, headers=UA, timeout=timeout)
    r.raise_for_status()
    for d in r.json().get("docs", [])[:max_results]:
        out.append(
            {
                "title": d.get("title", ""),
                "authors": d.get("author_name", [])[:3],
                "year": str(d.get("first_publish_year")) if d.get("first_publish_year") else None,
                "url": f"https://openlibrary.org{d.get('key', '')}",
                "description": "; ".join(d.get("subject", [])[:8]),
                "publisher": (d.get("publisher") or [""])[0],
            }
        )
    return out


# ---------------------------------------------------------------- youtube
def _iso8601_duration(s: str) -> Optional[int]:
    m = re.fullmatch(r"P(?:\d+D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", s or "")
    if not m:
        return None
    h, mi, se = (int(x) if x else 0 for x in m.groups())
    return h * 3600 + mi * 60 + se


def search_youtube(query: str, max_results: int = 6, api_key: str = "", timeout: int = 15) -> list[dict]:
    if api_key:
        r = requests.get(
            "https://www.googleapis.com/youtube/v3/search",
            params={"part": "snippet", "q": query, "type": "video", "maxResults": max_results, "key": api_key,
                    "relevanceLanguage": "en", "safeSearch": "strict"},
            timeout=timeout,
        )
        r.raise_for_status()
        items = r.json().get("items", [])
        ids = [i["id"]["videoId"] for i in items]
        details = {}
        if ids:
            r2 = requests.get(
                "https://www.googleapis.com/youtube/v3/videos",
                params={"part": "contentDetails,statistics", "id": ",".join(ids), "key": api_key},
                timeout=timeout,
            )
            details = {v["id"]: v for v in r2.json().get("items", [])}
        out = []
        for i in items:
            vid = i["id"]["videoId"]
            d = details.get(vid, {})
            out.append(
                {
                    "id": vid,
                    "title": i["snippet"]["title"],
                    "channel": i["snippet"]["channelTitle"],
                    "description": i["snippet"].get("description", ""),
                    "duration_sec": _iso8601_duration(d.get("contentDetails", {}).get("duration", "")),
                    "views": int(d.get("statistics", {}).get("viewCount", 0) or 0),
                    "url": f"https://www.youtube.com/watch?v={vid}",
                }
            )
        return out

    import yt_dlp

    opts = {"quiet": True, "skip_download": True, "extract_flat": "in_playlist", "no_warnings": True}
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(f"ytsearch{max_results}:{query}", download=False)
    out = []
    for e in (info or {}).get("entries", []) or []:
        if not e or not e.get("id"):
            continue
        out.append(
            {
                "id": e["id"],
                "title": e.get("title", ""),
                "channel": e.get("channel") or e.get("uploader") or "",
                "description": (e.get("description") or "")[:400],
                "duration_sec": int(e["duration"]) if e.get("duration") else None,
                "views": int(e.get("view_count") or 0),
                "url": f"https://www.youtube.com/watch?v={e['id']}",
            }
        )
    return out


def youtube_oembed_ok(url: str, timeout: int = 8) -> bool:
    """Cheap existence/embeddability check for a video link."""
    try:
        r = requests.get("https://www.youtube.com/oembed", params={"url": url, "format": "json"}, timeout=timeout)
        return r.status_code == 200
    except Exception:
        return True  # network issue: don't drop the video on our own failure


__all__ = [
    "domain_of", "tier_for", "relevant_excerpt", "keywords_from", "fetch_page_text", "fetch_html", "extract_text", "search_web",
    "search_wikipedia", "resolve_redirect", "search_books", "search_youtube", "youtube_oembed_ok",
]

"""Research orchestration: plan queries -> run providers -> build a numbered source bundle."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from types import ModuleType
from typing import Callable, Optional

from ..config import Settings
from ..llm import BaseLLM, LLMError
from ..models import ResearchBundle, Source
from ..generator import clean_title
from ..prompts import GROUNDED_RESEARCH, RESEARCH_PLAN, render
from . import providers as real_providers
from .reliability import TIER_RANK, domain_of, tier_for


class ResearchError(RuntimeError):
    pass


Progress = Optional[Callable[[str], None]]


def _plan(llm: BaseLLM, title: str, objective: str, audience: str) -> tuple[dict, Optional[str]]:
    try:
        plan = llm.generate_json(
            render(RESEARCH_PLAN, title=title, objective=objective, audience=audience or "beginner / undergraduate"),
            task="research_plan",
            temperature=0.2,
        )
        if not isinstance(plan, dict) or not plan.get("web_queries"):
            raise ValueError("plan missing web_queries")
        return plan, None
    except Exception as e:  # deterministic fallback keeps research going
        return (
            {
                "web_queries": [title, f"{title} {objective}"[:120], f"{title} explained"],
                "youtube_queries": [f"{title} explained", f"{title} tutorial"],
                "book_queries": [title],
                "key_subtopics": [],
            },
            f"Query planning by AI failed, used default queries ({e}).",
        )


def run_research(
    title: str,
    objective: str,
    audience: str,
    llm: BaseLLM,
    settings: Settings,
    providers: ModuleType = real_providers,
    progress: Progress = None,
) -> tuple[ResearchBundle, list[str]]:
    say = progress or (lambda _m: None)
    warnings: list[str] = []
    errors: dict[str, str] = {}

    say("Planning search queries...")
    plan, w = _plan(llm, title, objective, audience)
    if w:
        warnings.append(w)
    kw = providers.keywords_from(title, objective, " ".join(plan.get("key_subtopics", [])))

    # ---------------- websites (DuckDuckGo + page extraction)
    say("Searching the web...")
    hits: dict[str, dict] = {}
    for q in plan.get("web_queries", [])[:4]:
        try:
            for h in providers.search_web(q, max_results=6):
                if h.get("url") and h["url"] not in hits:
                    h["query"] = q
                    hits[h["url"]] = h
        except Exception as e:
            errors["web_search"] = f"{type(e).__name__}: {e}"[:300]
    ranked = sorted(hits.values(), key=lambda h: TIER_RANK[tier_for(h["url"])])
    ranked = [h for h in ranked if tier_for(h["url"]) != "D"][: settings.max_web_sources]

    say(f"Reading {len(ranked)} web pages...")

    if hasattr(providers, "fetch_html"):
        # download in parallel, parse sequentially in the main thread
        with ThreadPoolExecutor(max_workers=4) as ex:
            pages = list(ex.map(lambda h: providers.fetch_html(h["url"], timeout=settings.http_timeout), ranked))
        texts = [providers.extract_text(html_) for html_ in pages]
    else:
        texts = [providers.fetch_page_text(h["url"], timeout=settings.http_timeout) for h in ranked]
    for h, text in zip(ranked, texts):
        h["excerpt"] = providers.relevant_excerpt(text, kw) if text else h.get("snippet", "")
        h["full_text_ok"] = bool(text)
    web_sources = [
        Source(id="", kind="web", title=clean_title(h["title"]) or domain_of(h["url"]), url=h["url"], domain=domain_of(h["url"]),
               excerpt=h["excerpt"], tier=tier_for(h["url"]), query=h.get("query", ""))
        for h in ranked
        if h.get("excerpt")
    ]
    unread = sum(1 for h in ranked if not h.get("full_text_ok"))
    if unread:
        warnings.append(f"{unread} web page(s) could not be fully read; their search snippet was used instead.")

    # ---------------- Wikipedia
    say("Checking Wikipedia...")
    wiki_sources = []
    try:
        for p in providers.search_wikipedia(title, limit=2, timeout=settings.http_timeout):
            ex_ = providers.relevant_excerpt(p["text"], kw)
            if ex_ and p["url"] not in hits:
                wiki_sources.append(Source(id="", kind="wikipedia", title=p["title"], url=p["url"], domain="wikipedia.org",
                                           excerpt=ex_, tier="B", query=title))
    except Exception as e:
        errors["wikipedia"] = f"{type(e).__name__}: {e}"[:300]

    # ---------------- Gemini Google-Search grounding
    grounded_sources = []
    if settings.use_grounded_search:
        say("Running Google-Search-grounded research (Gemini)...")
        try:
            g = llm.generate_grounded(render(GROUNDED_RESEARCH, title=title, objective=objective), task="grounded_research")
            per_chunk: dict[int, list[str]] = {}
            for sp in g.supports:
                for idx in sp["source_idx"]:
                    per_chunk.setdefault(idx, []).append(sp["text"])
            for idx, src in enumerate(g.sources):
                segs = per_chunk.get(idx)
                if not segs:
                    continue
                url = providers.resolve_redirect(src["url"])
                grounded_sources.append(
                    Source(id="", kind="grounded", title=clean_title(src.get("title") or "") or domain_of(url), url=url, domain=domain_of(url),
                           excerpt="\n".join(dict.fromkeys(segs))[:2500], tier=tier_for(url), query="google-search-grounding")
                )
        except Exception as e:
            errors["grounded_search"] = f"{type(e).__name__}: {e}"[:300]

    # merge + dedupe by url
    seen, text_sources = set(), []
    for s in sorted([*web_sources, *wiki_sources, *grounded_sources], key=lambda s: TIER_RANK[s.tier]):
        if s.url in seen:
            continue
        seen.add(s.url)
        text_sources.append(s)
    for i, s in enumerate(text_sources, 1):
        s.id = f"S{i}"

    # ---------------- books
    say("Searching books...")
    books, seen_b = [], set()
    for q in plan.get("book_queries", [title])[:2]:
        try:
            for b in providers.search_books(q, max_results=5, api_key=settings.google_books_api_key, timeout=settings.http_timeout):
                key = b["title"].lower()
                if key in seen_b or not b["title"]:
                    continue
                seen_b.add(key)
                books.append(Source(id="", kind="book", title=b["title"], url=b.get("url", ""), domain=domain_of(b.get("url", "")),
                                    excerpt=b.get("description", ""), tier="B", authors=b.get("authors", []), year=b.get("year"), query=q))
        except Exception as e:
            errors["books"] = f"{type(e).__name__}: {e}"[:300]
    for i, b in enumerate(books[:8], 1):
        b.id = f"B{i}"
    books = books[:8]

    # ---------------- YouTube
    say("Searching YouTube...")
    videos, seen_v = [], set()
    for q in plan.get("youtube_queries", [title])[:2]:
        try:
            for v in providers.search_youtube(q, max_results=6, api_key=settings.youtube_api_key, timeout=settings.http_timeout):
                if v["id"] in seen_v:
                    continue
                if v.get("duration_sec") and v["duration_sec"] > 25 * 60:
                    continue  # too long to be a useful supplement to a 45-minute lesson
                seen_v.add(v["id"])
                videos.append(Source(id="", kind="video", title=v["title"], url=v["url"], domain="youtube.com",
                                     excerpt=v.get("description", ""), tier="C", channel=v.get("channel"),
                                     duration_sec=v.get("duration_sec"), query=q))
        except Exception as e:
            errors["youtube"] = f"{type(e).__name__}: {e}"[:300]
    for i, v in enumerate(videos[:10], 1):
        v.id = f"V{i}"
    videos = videos[:10]

    for prov, err in errors.items():
        warnings.append(f"Research provider '{prov}' failed: {err}")

    if not text_sources:
        raise ResearchError(
            "No usable text sources were found (all web/Wikipedia/grounded providers failed or returned nothing). "
            "Check your internet connection and press Retry. Details: " + "; ".join(f"{k}: {v}" for k, v in errors.items())
        )
    if len(text_sources) < 3:
        warnings.append(f"Only {len(text_sources)} text source(s) found - QC1 will have less evidence to verify against.")
    if not videos:
        warnings.append("No YouTube videos found; the lesson will have no video resources.")

    bundle = ResearchBundle(
        queries={k: plan.get(k, []) for k in ("web_queries", "youtube_queries", "book_queries")},
        key_subtopics=plan.get("key_subtopics", []),
        sources=text_sources,
        books=books,
        videos=videos,
        provider_errors=errors,
    )
    say(f"Research done: {len(text_sources)} text sources, {len(books)} books, {len(videos)} videos.")
    return bundle, warnings

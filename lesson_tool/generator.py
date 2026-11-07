"""Lesson generation from a research bundle, plus helpers that format lessons for prompts."""
from __future__ import annotations

import re

from .llm import BaseLLM, LLMError
from .models import Lesson, ResearchBundle, Section, SubObjective, VideoPick
from .prompts import GENERATE_LESSON, GENERATE_SYSTEM, render

READING_WPM = 180
CITE_RE = re.compile(r"\[(S\d+)\]")
URL_RE = re.compile(r"https?://[^\s)\]>\"']+")


_ODD_CITE = re.compile(r"[【\[\(（]\s*(S\d+(?:\s*[,;†]\s*S\d+)*)\s*[】\]\)）]")


def normalize_citations(md: str) -> str:
    """Models sometimes write 【S1】, (S1), [S1, S2] or [S1†L3]; normalise to [S1][S2]."""
    def rep(m):
        ids = re.findall(r"S\d+", m.group(1))
        return "".join(f"[{i}]" for i in ids)

    md = re.sub(r"【\s*(S\d+)[^】]*】", lambda m: f"[{m.group(1)}]", md)
    return _ODD_CITE.sub(rep, md)


def clean_title(t: str, max_len: int = 110) -> str:
    """Search engines sometimes glue several result titles together; keep the first one."""
    t = re.split(r"\s*(?:\.\.\.|…|\s\|\s)\s*", (t or "").strip())[0].strip(" -–|")
    return t if len(t) <= max_len else t[: max_len - 1].rsplit(" ", 1)[0] + "…"


def rebalance_minutes(lesson, target: int) -> None:
    """Make section minutes sum to `target` by adjusting the largest flexible sections first."""
    diff = target - lesson.total_minutes()
    order = sorted([s for s in lesson.sections if s.type in ("concept", "example", "activity")] or lesson.sections,
                   key=lambda s: -s.minutes)
    i = 0
    while diff != 0 and order and i < 200:
        s = order[i % len(order)]
        step = 1 if diff > 0 else -1
        if s.minutes + step >= 2:
            s.minutes += step
            diff -= step
        i += 1


def to_minutes(val, default: int) -> int:
    """Accept 5, 5.0, "5", "5 min" from the model; fall back to default."""
    m = re.search(r"\d+(?:\.\d+)?", str(val)) if val is not None else None
    return max(1, round(float(m.group()))) if m else default


# ------------------------------------------------------------------ formatting for prompts
def format_sources(bundle: ResearchBundle, max_chars: int = 1800, max_sources: int = 12) -> str:
    parts = []
    for s in bundle.sources[:max_sources]:
        parts.append(f"[{s.id}] {s.title} ({s.domain}, reliability tier {s.tier})\n{s.excerpt[:max_chars]}")
    return "\n\n".join(parts) or "(none)"


def format_books(bundle: ResearchBundle) -> str:
    return "\n".join(
        f"[{b.id}] {b.title} - {', '.join(b.authors) or 'unknown author'} ({b.year or 'n.d.'}): {b.excerpt[:300]}" for b in bundle.books
    ) or "(none)"


def format_videos(bundle: ResearchBundle) -> str:
    def dur(s):
        return f"{s // 60}:{s % 60:02d}" if s else "?"

    return "\n".join(f"[{v.id}] \"{v.title}\" - channel: {v.channel}, duration {dur(v.duration_sec)}" for v in bundle.videos) or "(none)"


def format_lesson(lesson: Lesson) -> str:
    out = ["SUB-OBJECTIVES: " + "; ".join(f"{o.id}: {o.text}" for o in lesson.sub_objectives)]
    for s in lesson.sections:
        out.append(f"\n=== [{s.id}] {s.type.upper()}: {s.title} ({s.minutes} min; objectives {', '.join(s.objectives)}) ===\n{s.content_md}")
    return "\n".join(out)


# ------------------------------------------------------------------ metrics (deterministic)
def word_count(md: str) -> int:
    return len(re.findall(r"\w+", md))


def lesson_metrics(lesson: Lesson) -> dict:
    sections = []
    for s in lesson.sections:
        wc = word_count(s.content_md)
        sections.append(
            {
                "id": s.id,
                "type": s.type,
                "minutes": s.minutes,
                "words": wc,
                "reading_minutes": round(wc / READING_WPM, 1),
                "citations": len(CITE_RE.findall(s.content_md)),
            }
        )
    return {
        "total_minutes": lesson.total_minutes(),
        "target_minutes": lesson.duration_minutes,
        "total_words": sum(x["words"] for x in sections),
        "total_reading_minutes": round(sum(x["reading_minutes"] for x in sections), 1),
        "section_types": [s.type for s in lesson.sections],
        "has_activity": any(s.type == "activity" for s in lesson.sections),
        "has_knowledge_check": any(s.type == "knowledge_check" for s in lesson.sections),
        "sections": sections,
        "videos": len(lesson.videos),
    }


# ------------------------------------------------------------------ generation
def _parse_lesson(data: dict, title: str, objective: str, audience: str, minutes: int, bundle: ResearchBundle) -> Lesson:
    if not isinstance(data, dict) or not data.get("sections"):
        raise LLMError("The model returned a lesson with no sections. Press Retry.")
    sections = []
    for i, raw in enumerate(data["sections"], 1):
        t = raw.get("type", "concept")
        if t not in {"hook", "concept", "example", "activity", "knowledge_check", "summary"}:
            t = "concept"
        sections.append(
            Section(
                id=str(raw.get("id") or f"s{i}"),
                type=t,
                title=str(raw.get("title") or f"Section {i}"),
                minutes=to_minutes(raw.get("minutes"), 1),
                content_md=normalize_citations(str(raw.get("content_md") or "")),
                objectives=[str(o) for o in raw.get("objectives", [])],
            )
        )
    # make ids unique even if the model repeats one
    seen = set()
    for i, s in enumerate(sections, 1):
        if s.id in seen:
            s.id = f"s{i}x"
        seen.add(s.id)

    valid_v = {v.id for v in bundle.videos}
    valid_b = {b.id for b in bundle.books}
    videos = [VideoPick(source_id=v["source_id"], why=v.get("why", ""), watch_when=v.get("watch_when", ""))
              for v in data.get("videos", []) if isinstance(v, dict) and v.get("source_id") in valid_v]
    further = [b for b in data.get("further_reading", []) if b in valid_b]
    subs = [SubObjective(id=str(o.get("id")), text=str(o.get("text"))) for o in data.get("sub_objectives", []) if isinstance(o, dict)]
    return Lesson(title=title, objective=objective, audience=audience, duration_minutes=minutes,
                  sub_objectives=subs, sections=sections, videos=videos, further_reading=further)


def generate_lesson(title: str, objective: str, audience: str, bundle: ResearchBundle, llm: BaseLLM, minutes: int = 45) -> Lesson:
    prompt = render(
        GENERATE_LESSON,
        title=title,
        objective=objective,
        audience=audience or "beginner / undergraduate, no prior knowledge assumed",
        minutes=minutes,
        subtopics=", ".join(bundle.key_subtopics) or "(derive from sources)",
        sources=format_sources(bundle, llm.excerpt_chars, llm.max_sources),
        books=format_books(bundle),
        videos=format_videos(bundle),
    )
    data = llm.generate_json(prompt, task="generate_lesson", system=GENERATE_SYSTEM, temperature=0.5)
    return _parse_lesson(data, title, objective, audience, minutes, bundle)

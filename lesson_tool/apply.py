"""Apply selected QC recommendations: the model proposes revised sections, the instructor sees a diff
and accepts or rejects. Nothing is saved until the instructor accepts."""
from __future__ import annotations

import difflib
import json

from .generator import format_sources, normalize_citations, rebalance_minutes, to_minutes
from .llm import BaseLLM, LLMError
from .models import Lesson, QCIssue, ResearchBundle, Section
from .prompts import APPLY_FIXES, APPLY_SYSTEM, render


def propose_revision(lesson: Lesson, issues: list[QCIssue], bundle: ResearchBundle, llm: BaseLLM) -> tuple[Lesson, list[dict], list[str]]:
    if not issues:
        raise ValueError("Select at least one issue to apply.")
    issues = issues[:6]
    sections_json = json.dumps([s.model_dump() for s in lesson.sections], indent=1)
    issues_txt = "\n".join(
        f"- {i.id} [{i.severity}] ({i.category}) section={i.section_id or 'whole lesson'}: {i.description}"
        + (f" | Evidence: {i.evidence}" if i.evidence else "") + (f" | Suggested fix: {i.suggestion}" if i.suggestion else "")
        for i in issues
    )
    data = llm.generate_json(
        render(APPLY_FIXES, title=lesson.title, objective=lesson.objective, minutes=lesson.duration_minutes,
               sections=sections_json, issues=issues_txt, sources=format_sources(bundle, max_chars=min(900, llm.excerpt_chars // 2), max_sources=llm.max_sources)),
        task="apply_fixes", system=APPLY_SYSTEM, temperature=0.3,
    )
    if not isinstance(data, dict):
        raise LLMError("Model returned an unexpected format for the revision. Press Retry.")

    new = lesson.model_copy(deep=True)
    by_id = {s.id: i for i, s in enumerate(new.sections)}
    changed: list[str] = []
    for raw in data.get("sections", []) or []:
        if not isinstance(raw, dict) or not raw.get("content_md"):
            continue
        sid = str(raw.get("id") or f"s{len(new.sections) + 1}")
        base = new.sections[by_id[sid]] if sid in by_id else None
        t = raw.get("type") or (base.type if base else "concept")
        if t not in {"hook", "concept", "example", "activity", "knowledge_check", "summary"}:
            t = base.type if base else "concept"
        sec = Section(
            id=sid, type=t,
            title=str(raw.get("title") or (base.title if base else "New section")),
            minutes=to_minutes(raw.get("minutes"), base.minutes if base else 3),
            content_md=normalize_citations(str(raw["content_md"])),
            objectives=[str(o) for o in (raw.get("objectives") or (base.objectives if base else []))],
        )
        if base is not None:
            new.sections[by_id[sid]] = sec
        else:
            # insert new section before the knowledge check / summary
            pos = next((i for i, s in enumerate(new.sections) if s.type in ("knowledge_check", "summary")), len(new.sections))
            new.sections.insert(pos, sec)
            by_id = {s.id: i for i, s in enumerate(new.sections)}
        changed.append(sid)
    for sid, mins in (data.get("minutes_changes") or {}).items():
        if sid in by_id:
            try:
                new.sections[by_id[sid]].minutes = to_minutes(mins, new.sections[by_id[sid]].minutes)
                if sid not in changed:
                    changed.append(sid)
            except (TypeError, ValueError):
                pass
    if new.total_minutes() != new.duration_minutes:
        rebalance_minutes(new, new.duration_minutes)  # revisions must keep the 45-minute budget
    if not changed:
        raise LLMError("The model did not propose any changes. Try selecting fewer/more specific issues, or Retry.")
    log = [c for c in data.get("change_log", []) or [] if isinstance(c, dict)]
    return new, log, changed


def section_diff(old: Lesson, new: Lesson) -> list[tuple[str, str]]:
    """Unified diff per changed section: [(section_label, diff_text)]."""
    old_by = {s.id: s for s in old.sections}
    out = []
    for s in new.sections:
        o = old_by.get(s.id)
        a = (f"# {o.title} ({o.minutes} min)\n" + o.content_md) if o else ""
        b = f"# {s.title} ({s.minutes} min)\n" + s.content_md
        if a != b:
            d = "\n".join(difflib.unified_diff(a.splitlines(), b.splitlines(), "before", "after", lineterm="", n=1))
            out.append((f"{s.id} - {s.title}" + ("" if o else " (NEW)"), d))
    return out

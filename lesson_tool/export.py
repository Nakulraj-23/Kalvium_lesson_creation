"""Render a lesson + references + QC reports to Markdown / HTML / DOCX and bundle as ZIP."""
from __future__ import annotations

import html
import io
import json
import re
import zipfile

from .generator import CITE_RE, clean_title, normalize_citations
from .models import Lesson, LessonProject, QCReport, ResearchBundle


ORIGIN = {"rule": "rule check", "llm": "AI audit", "web": "independent web verification"}


def _dur(sec) -> str:
    return f"{sec // 60}:{sec % 60:02d}" if sec else "n/a"


def citation_map(lesson: Lesson, bundle: ResearchBundle) -> dict[str, int]:
    """S-ids -> reference numbers in order of first appearance (only ids that exist)."""
    valid = {s.id for s in bundle.sources}
    order: dict[str, int] = {}
    for s in lesson.sections:
        for c in CITE_RE.findall(normalize_citations(s.content_md)):
            if c in valid and c not in order:
                order[c] = len(order) + 1
    return order


def _replace_cites(md: str, cmap: dict[str, int]) -> str:
    md = normalize_citations(md)
    return CITE_RE.sub(lambda m: f"[{cmap[m.group(1)]}]" if m.group(1) in cmap else "[citation needed]", md)


def references_md(lesson: Lesson, bundle: ResearchBundle) -> str:
    cmap = citation_map(lesson, bundle)
    by = bundle.by_id()
    lines = ["## References", ""]
    for sid, n in sorted(cmap.items(), key=lambda x: x[1]):
        s = by[sid]
        lines.append(f"{n}. {clean_title(s.title)}. *{s.domain}*. {s.url}")
    if lesson.further_reading:
        lines += ["", "### Books (further reading)", ""]
        for bid in lesson.further_reading:
            b = by.get(bid)
            if b:
                lines.append(f"- {b.title} - {', '.join(b.authors) or 'Unknown author'} ({b.year or 'n.d.'}). {b.url}")
    if lesson.videos:
        lines += ["", "### Videos", ""]
        for v in lesson.videos:
            s = by.get(v.source_id)
            if s:
                lines.append(f"- {s.title} - {s.channel} ({_dur(s.duration_sec)}). {s.url}")
    return "\n".join(lines) + "\n"


def lesson_md(lesson: Lesson, bundle: ResearchBundle, include_refs: bool = True) -> str:
    cmap = citation_map(lesson, bundle)
    by = bundle.by_id()
    out = [f"# {lesson.title}", "", f"**Learning objective:** {lesson.objective}  ",
           f"**Duration:** {lesson.total_minutes()} minutes (self-study or instructor-led)"
           + (f"  \n**Audience:** {lesson.audience}" if lesson.audience else ""), ""]
    if lesson.sub_objectives:
        out += ["### By the end of this lesson you will be able to:", ""]
        out += [f"- **{o.id}** {o.text}" for o in lesson.sub_objectives] + [""]
    out += ["### Lesson plan", "", "| # | Section | Type | Minutes | Objectives |", "|---|---|---|---|---|"]
    for i, s in enumerate(lesson.sections, 1):
        out.append(f"| {i} | {s.title} | {s.type.replace('_', ' ')} | {s.minutes} | {', '.join(s.objectives)} |")
    out += [f"| | **Total** | | **{lesson.total_minutes()}** | |", ""]
    for i, s in enumerate(lesson.sections, 1):
        out += [f"## {i}. {s.title} ({s.minutes} min)", "", _replace_cites(s.content_md, cmap).strip(), ""]
    if lesson.videos:
        out += ["## Supplementary videos (optional, not counted in the 45 minutes)", ""]
        for v in lesson.videos:
            s = by.get(v.source_id)
            if s:
                out.append(f"- **[{s.title}]({s.url})** - {s.channel}, {_dur(s.duration_sec)}. {v.why}"
                           + (f" *Watch: {v.watch_when}.*" if v.watch_when else ""))
        out.append("")
    if include_refs:
        out.append(references_md(lesson, bundle))
    return "\n".join(out)


def qc_report_md(r: QCReport, bundle: ResearchBundle | None = None) -> str:
    title = "QC Layer 1 - Research & Factual Accuracy" if r.layer == "qc_factual" else "QC Layer 2 - Instructional Quality"
    out = [f"# {title} - Audit Report", "", f"- **Score:** {r.score}/100", f"- **Lesson version audited:** v{r.lesson_version}",
           f"- **Reviewer model:** {r.model}", f"- **Date:** {r.created_at}", "", "## Summary", "", r.summary or "-", ""]
    if r.rubric:
        out += ["## Rubric (1-5)", "", "| Criterion | Score |", "|---|---|"]
        out += [f"| {k.replace('_', ' ')} | {v} |" for k, v in r.rubric.items()] + [""]
    if r.objective_coverage:
        out += ["## Objective coverage", "", "| Component | Taught | Practised | Assessed | Coverage |", "|---|---|---|---|---|"]
        for c in r.objective_coverage:
            j = lambda x: ", ".join(c.get(x) or []) or "-"
            out.append(f"| {c.get('component', '')} | {j('taught_in')} | {j('practised_in')} | {j('assessed_in')} | {c.get('coverage', '')} |")
        out.append("")
    out += [f"## Issues ({len(r.issues)})", ""]
    if not r.issues:
        out.append("No issues found.")
    for i in r.issues:
        out += [f"### {i.id} - [{i.severity.upper()}] {i.category} ({'section ' + i.section_id if i.section_id else 'whole lesson'}; found by {ORIGIN[i.origin]})",
                "", f"**Problem:** {i.description}  "]
        if i.evidence:
            out.append(f"**Evidence:** {i.evidence}  ")
        if i.suggestion:
            out.append(f"**Suggested improvement:** {i.suggestion}")
        out.append("")
    if r.claims:
        out += ["## Claim verification", "", "| # | Claim | Section | Cited | Verdict | Notes |", "|---|---|---|---|---|---|"]
        for n, c in enumerate(r.claims, 1):
            esc = lambda t: (t or "").replace("|", "\\|").replace("\n", " ")
            out.append(f"| {n} | {esc(c.claim)} | {c.section_id or ''} | {', '.join(c.cited)} | {c.verdict} | {esc(c.note)} |")
        out.append("")
    if r.sources:
        by = bundle.by_id() if bundle else {}
        out += ["## Source assessment", "", "| Source | Tier | Relevance | Note |", "|---|---|---|---|"]
        for s in r.sources:
            src = by.get(s.source_id)
            name = f"{s.source_id} {src.title} ({src.domain})" if src else s.source_id
            out.append(f"| {name} | {s.tier} | {s.relevance} | {(s.note or '').replace('|', '/')} |")
        out += ["", "_Tier key: A = standards/official docs/.gov/.edu, B = reputable reference, C = general web/blog, D = user-generated._", ""]
    return "\n".join(out)


# ------------------------------------------------------------------ HTML
def _md_to_html(md_text: str) -> str:
    import markdown

    return markdown.markdown(md_text, extensions=["tables", "fenced_code", "sane_lists"])


def lesson_html(lesson: Lesson, bundle: ResearchBundle) -> str:
    body = _md_to_html(lesson_md(lesson, bundle))
    by = bundle.by_id()
    embeds = ""
    for v in lesson.videos:
        s = by.get(v.source_id)
        if s and "watch?v=" in s.url:
            vid = s.url.split("watch?v=")[1].split("&")[0]
            embeds += (f'<figure><iframe width="560" height="315" src="https://www.youtube-nocookie.com/embed/{vid}" '
                       f'title="{html.escape(s.title)}" frameborder="0" allowfullscreen></iframe>'
                       f"<figcaption>{html.escape(s.title)} - {html.escape(s.channel or '')}</figcaption></figure>")
    if embeds:
        body = body.replace("<h2>References</h2>", f"<h2>Watch</h2>{embeds}<h2>References</h2>", 1)
    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><title>{html.escape(lesson.title)}</title>
<style>body{{font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;max-width:860px;margin:2rem auto;padding:0 1rem;line-height:1.6;color:#1d1d1f}}
table{{border-collapse:collapse;width:100%;margin:1rem 0}}td,th{{border:1px solid #ccc;padding:.4rem .6rem;text-align:left}}th{{background:#f3f3f3}}
pre{{background:#f6f8fa;padding:1rem;overflow:auto;border-radius:6px}}code{{font-family:ui-monospace,Consolas,monospace}}
h1{{border-bottom:3px solid #333}}h2{{margin-top:2.2rem;border-bottom:1px solid #ddd}}figure{{margin:1rem 0}}
@media print{{iframe{{display:none}}}}</style></head><body>{body}</body></html>"""


# ------------------------------------------------------------------ DOCX
def _add_runs(par, text: str):
    # **bold**, `code`, *italic*
    for tok in re.split(r"(\*\*[^*]+\*\*|`[^`]+`|\*[^*]+\*)", text):
        if not tok:
            continue
        if tok.startswith("**") and tok.endswith("**"):
            par.add_run(tok[2:-2]).bold = True
        elif tok.startswith("`") and tok.endswith("`"):
            r = par.add_run(tok[1:-1])
            r.font.name = "Consolas"
        elif tok.startswith("*") and tok.endswith("*") and len(tok) > 2:
            par.add_run(tok[1:-1]).italic = True
        else:
            par.add_run(re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1 (\2)", tok))


def lesson_docx(lesson: Lesson, bundle: ResearchBundle) -> bytes:
    from docx import Document
    from docx.shared import Pt

    doc = Document()
    lines = lesson_md(lesson, bundle).splitlines()
    i, in_code, code_buf = 0, False, []
    while i < len(lines):
        line = lines[i]
        if line.strip().startswith("```"):
            if in_code:
                p = doc.add_paragraph()
                r = p.add_run("\n".join(code_buf))
                r.font.name = "Consolas"
                r.font.size = Pt(9)
                code_buf = []
            in_code = not in_code
            i += 1
            continue
        if in_code:
            code_buf.append(line)
            i += 1
            continue
        if line.strip().startswith("|"):
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
                    rows.append(cells)
                i += 1
            if rows:
                ncol = max(len(r) for r in rows)
                t = doc.add_table(rows=len(rows), cols=ncol)
                t.style = "Table Grid"
                for ri, r in enumerate(rows):
                    for ci, c in enumerate(r):
                        t.cell(ri, ci).text = c.replace("**", "")
            continue
        m = re.match(r"^(#{1,6})\s+(.*)", line)
        if m:
            doc.add_heading(m.group(2).replace("**", ""), level=min(len(m.group(1)), 4))
        elif re.match(r"^\s*[-*]\s+", line):
            _add_runs(doc.add_paragraph(style="List Bullet"), re.sub(r"^\s*[-*]\s+", "", line))
        elif re.match(r"^\s*\d+[.)]\s+", line):
            _add_runs(doc.add_paragraph(style="List Number"), re.sub(r"^\s*\d+[.)]\s+", "", line))
        elif line.strip():
            _add_runs(doc.add_paragraph(), line.strip().rstrip("\\").rstrip())
        i += 1
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


# ------------------------------------------------------------------ bundle
def export_zip(project: LessonProject) -> bytes:
    lesson, bundle = project.lesson, project.research
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("lesson.md", lesson_md(lesson, bundle))
        z.writestr("lesson.html", lesson_html(lesson, bundle))
        z.writestr("lesson.docx", lesson_docx(lesson, bundle))
        z.writestr("references.md", references_md(lesson, bundle))
        for key, name in (("qc_factual", "qc1_factual_report"), ("qc_instructional", "qc2_instructional_report")):
            r = project.qc_reports.get(key)
            if r:
                z.writestr(f"{name}.md", qc_report_md(r, bundle))
                z.writestr(f"{name}.json", r.model_dump_json(indent=2))
        z.writestr("research_sources.json", bundle.model_dump_json(indent=2))
        z.writestr("project.json", project.model_dump_json(indent=2))
    return buf.getvalue()

"""AI Lesson Creation Tool - Streamlit UI.

Run:  streamlit run app.py
"""
from __future__ import annotations

import streamlit as st

from lesson_tool.apply import propose_revision, section_diff
from lesson_tool.config import get_settings
from lesson_tool.export import export_zip, lesson_docx, lesson_html, lesson_md, qc_report_md, references_md
from lesson_tool.generator import lesson_metrics
from lesson_tool.llm import make_llm
from lesson_tool.models import Lesson, Section, SubObjective
from lesson_tool.pipeline import STEP_LABEL, STEP_ORDER, Pipeline, validate_inputs
from lesson_tool.storage import Store

SAMPLES = {
    "HTTP Requests and Responses": (
        "HTTP Requests and Responses",
        "Explain GET and POST methods and distinguish between 2xx, 4xx, and 5xx response status categories.",
        "Beginner web-development students",
    ),
    "SQL Joins": (
        "SQL Joins: Combining Data from Multiple Tables",
        "Differentiate INNER JOIN, LEFT JOIN and FULL OUTER JOIN and choose the correct join to answer a given query.",
        "Undergraduate students who know basic SELECT queries",
    ),
}
ICON = {"pending": "⚪", "running": "🔄", "done": "✅", "failed": "❌"}

st.set_page_config(page_title="AI Lesson Creation Tool", page_icon="📘", layout="wide")
settings = get_settings()
store = Store(settings.data_dir)
pipeline = Pipeline(store, settings)
ss = st.session_state
ss.setdefault("project_id", None)
ss.setdefault("pending", None)  # pending QC revision awaiting accept/reject
ss.setdefault("flash", None)


def flash(kind: str, msg: str):
    ss.flash = (kind, msg)


def load_project():
    if not ss.project_id:
        return None
    try:
        return store.load(ss.project_id)
    except Exception as e:
        st.error(f"Could not load project {ss.project_id}: {e}")
        ss.project_id = None
        return None


def run_with_status(label: str, fn):
    with st.status(label, expanded=True) as status:
        ok = fn(status.write)
        status.update(label=label + (" - done" if ok else " - failed"), state="complete" if ok else "error")
    return ok


# ====================================================================== sidebar
with st.sidebar:
    st.title("📘 Lesson Creator")
    if settings.llm_backend == "fake":
        st.warning("TEST MODE: fake LLM (LESSON_TOOL_LLM=fake). Output is placeholder text.")
    elif settings.provider == "groq" and settings.groq_api_key:
        st.success("AI: **Groq** (writing + QC, QC starts on a different model)"
                   + ("\n\nGoogle-Search grounding: Gemini" if settings.gemini_api_key else ""))
    elif settings.gemini_api_key:
        st.success(f"AI: **Gemini**\n\nGeneration: `{settings.gen_model}`\n\nQC: `{settings.qc_model}`")
    else:
        st.error("No AI key found. Copy `.env.example` to `.env`, add GROQ_API_KEY (or GEMINI_API_KEY), then restart.")
    st.caption(f"Grounded Google Search: {'on' if settings.use_grounded_search else 'off'} · "
               f"YouTube: {'Data API' if settings.youtube_api_key else 'yt-dlp search'}")
    if st.button("➕ New lesson", width="stretch"):
        ss.project_id, ss.pending = None, None
        st.rerun()
    projects = store.list_projects()
    if projects:
        labels = {p["id"]: f"{p['title']}  ·  {p['updated_at'][:16].replace('T', ' ')}" for p in projects}
        ids = list(labels)
        idx = ids.index(ss.project_id) if ss.project_id in ids else None
        choice = st.selectbox("Saved lessons", ids, index=idx, format_func=lambda i: labels[i], placeholder="Open a saved lesson")
        if choice and choice != ss.project_id:
            ss.project_id, ss.pending = choice, None
            st.rerun()

project = load_project()

if ss.flash:
    kind, msg = ss.flash
    getattr(st, kind)(msg)
    ss.flash = None

# ====================================================================== create
if project is None:
    st.header("Create a new lesson")
    st.write("Enter a lesson title and learning objective. The tool researches websites, books and YouTube, writes a "
             "45-minute lesson with citations, then runs two independent QC audits.")
    c1, c2 = st.columns(2)
    for col, name in zip((c1, c2), SAMPLES):
        if col.button(f"Load sample: {name}", width="stretch"):
            ss.in_title, ss.in_obj, ss.in_aud = SAMPLES[name]
            st.rerun()
    with st.form("create"):
        title = st.text_input("Lesson Title *", key="in_title")
        objective = st.text_area("Learning Objective *", key="in_obj", height=90)
        audience = st.text_input("Audience (optional)", key="in_aud", placeholder="e.g. first-year CS students")
        go = st.form_submit_button("🚀 Research & generate lesson", type="primary")
    if go:
        errs = validate_inputs(title, objective)
        if errs:
            for e in errs:
                st.error(e)
        else:
            p = store.new_project(title, objective, audience)
            ss.project_id = p.id
            run_with_status("Building lesson", lambda say: pipeline.run_all(p, progress=say))
            st.rerun()
    st.stop()

# ====================================================================== project header + step status
st.header(project.title)
st.caption(f"Objective: {project.objective}" + (f"  ·  Audience: {project.audience}" if project.audience else "")
           + f"  ·  Lesson version v{project.lesson_version}")

cols = st.columns(4)
for col, step in zip(cols, STEP_ORDER):
    s = project.steps[step]
    with col:
        st.markdown(f"**{ICON[s.state]} {STEP_LABEL[step]}**")
        if s.state == "failed":
            st.error(s.error or "failed", icon="⚠️")
            if st.button("🔁 Retry", key=f"retry_{step}"):
                ok = run_with_status(f"Retrying {STEP_LABEL[step]}", lambda say: pipeline.run_step(project, step, say))
                if ok:
                    nxt = [x for x in STEP_ORDER[STEP_ORDER.index(step) + 1:] if project.steps[x].state != "done"]
                    if nxt:
                        run_with_status("Continuing remaining steps", lambda say: pipeline.run_all(project, say, start_at=nxt[0]))
                st.rerun()
        elif s.state == "running":
            st.caption("Interrupted while running - press Retry.")
            if st.button("🔁 Retry", key=f"retry_{step}"):
                run_with_status(f"Retrying {STEP_LABEL[step]}", lambda say: pipeline.run_step(project, step, say))
                st.rerun()
        for w in s.warnings:
            st.caption(f"⚠️ {w}")

tabs = st.tabs(["🔎 Research", "✏️ Edit", "🧪 QC 1 · Facts", "🎓 QC 2 · Instruction", "👁️ Preview", "📦 Export", "🕘 History"])

# ====================================================================== research
with tabs[0]:
    r = project.research
    if not r:
        st.info("No research yet.")
    else:
        st.write(f"**{len(r.sources)}** text sources · **{len(r.books)}** books · **{len(r.videos)}** videos · {r.created_at[:16]}")
        with st.expander("Search queries used"):
            st.json(r.queries)
            if r.key_subtopics:
                st.write("Key subtopics:", ", ".join(r.key_subtopics))
        if r.provider_errors:
            st.warning("Some providers failed: " + "; ".join(f"{k}: {v}" for k, v in r.provider_errors.items()))
        st.subheader("Websites")
        st.dataframe([{"id": s.id, "tier": s.tier, "kind": s.kind, "title": s.title, "url": s.url} for s in r.sources],
                     width="stretch", hide_index=True,
                     column_config={"url": st.column_config.LinkColumn("url")})
        st.caption("Tier A = standards/official docs/.gov/.edu · B = reputable reference · C = general web · D = user-generated (excluded)")
        for s in r.sources:
            with st.expander(f"{s.id} · {s.title}"):
                st.write(s.url)
                st.text(s.excerpt[:3000])
        st.subheader("Books")
        st.dataframe([{"id": b.id, "title": b.title, "authors": ", ".join(b.authors), "year": b.year, "url": b.url} for b in r.books],
                     width="stretch", hide_index=True, column_config={"url": st.column_config.LinkColumn("url")})
        st.subheader("YouTube candidates")
        st.dataframe([{"id": v.id, "title": v.title, "channel": v.channel,
                       "duration": f"{v.duration_sec // 60}:{v.duration_sec % 60:02d}" if v.duration_sec else "?", "url": v.url}
                      for v in r.videos], width="stretch", hide_index=True,
                     column_config={"url": st.column_config.LinkColumn("url")})
    if st.button("🔄 Re-run research", help="Fetches fresh sources. Your current lesson and its versions are kept."):
        run_with_status("Researching", lambda say: pipeline.run_step(project, "research", say))
        st.rerun()

lesson: Lesson | None = project.lesson

# ====================================================================== edit
with tabs[1]:
    if not lesson:
        st.info("Lesson not generated yet.")
        if project.research and st.button("✨ Generate lesson"):
            run_with_status("Generating", lambda say: pipeline.run_all(project, say, start_at="generate"))
            st.rerun()
    else:
        m = lesson_metrics(lesson)
        a, b, c = st.columns(3)
        a.metric("Planned minutes", f"{m['total_minutes']} / {lesson.duration_minutes}")
        b.metric("Words", m["total_words"])
        c.metric("Est. reading time", f"{m['total_reading_minutes']} min")
        st.caption("Edit any section below, then press **Save changes** - every save creates a new version (see History).")
        v = project.lesson_version
        with st.form(f"edit_{v}"):
            subs_txt = st.text_area("Sub-objectives (one per line, `O1: text`)",
                                    "\n".join(f"{o.id}: {o.text}" for o in lesson.sub_objectives), height=100)
            obj_ids = [o.id for o in lesson.sub_objectives]
            edited = []
            for i, s in enumerate(lesson.sections):
                with st.expander(f"{i + 1}. {s.title}  ·  {s.type}  ·  {s.minutes} min", expanded=False):
                    c1, c2, c3 = st.columns([3, 1, 1])
                    t = c1.text_input("Title", s.title, key=f"t_{v}_{s.id}")
                    mins = c2.number_input("Minutes", 1, 45, s.minutes, key=f"m_{v}_{s.id}")
                    types = ["hook", "concept", "example", "activity", "knowledge_check", "summary"]
                    ty = c3.selectbox("Type", types, types.index(s.type), key=f"ty_{v}_{s.id}")
                    objs = st.multiselect("Serves objectives", obj_ids, [o for o in s.objectives if o in obj_ids], key=f"o_{v}_{s.id}")
                    body = st.text_area("Content (markdown, cite sources as [S1])", s.content_md, height=320, key=f"c_{v}_{s.id}")
                    delete = st.checkbox("Delete this section", key=f"d_{v}_{s.id}")
                    if not delete:
                        edited.append(Section(id=s.id, type=ty, title=t, minutes=int(mins), content_md=body, objectives=objs))
            vid_ids = [x.source_id for x in lesson.videos]
            keep_videos = st.multiselect("Supplementary videos to keep", vid_ids, vid_ids, key=f"vids_{v}")
            note = st.text_input("Change note (optional)", key=f"note_{v}")
            saved = st.form_submit_button("💾 Save changes", type="primary")
        if saved:
            subs = []
            for line in subs_txt.splitlines():
                if ":" in line:
                    oid, txt = line.split(":", 1)
                    subs.append(SubObjective(id=oid.strip(), text=txt.strip()))
            if not edited:
                st.error("A lesson needs at least one section - nothing saved.")
            elif any(not s.content_md.strip() for s in edited):
                st.error("A section has empty content. Fill it or tick 'Delete this section'. Nothing saved.")
            else:
                new = lesson.model_copy(deep=True)
                new.sub_objectives, new.sections = subs, edited
                new.videos = [x for x in lesson.videos if x.source_id in keep_videos]
                if new.model_dump() == lesson.model_dump():
                    flash("info", "No changes to save.")
                else:
                    ver = store.commit_lesson(project, new, "Instructor edit" + (f": {note}" if note else ""))
                    flash("success", f"Saved as version v{ver}.")
                st.rerun()
        c1, c2 = st.columns(2)
        if c1.button("➕ Add empty section"):
            new = lesson.model_copy(deep=True)
            nid = f"s{max([int(x.id[1:]) for x in new.sections if x.id[1:].isdigit()] + [0]) + 1}"
            pos = next((i for i, x in enumerate(new.sections) if x.type in ("knowledge_check", "summary")), len(new.sections))
            new.sections.insert(pos, Section(id=nid, type="concept", title="New section", minutes=3, content_md="Write content here."))
            store.commit_lesson(project, new, f"Instructor added section {nid}")
            st.rerun()
        if c2.button("♻️ Regenerate whole lesson", help="Creates a new AI version; all previous versions stay in History."):
            run_with_status("Regenerating", lambda say: pipeline.run_step(project, "generate", say))
            st.rerun()


# ====================================================================== QC tabs
def render_qc(layer: str, tab):
    with tab:
        if not lesson:
            st.info("Generate the lesson first.")
            return
        rep = project.qc_reports.get(layer)
        label = STEP_LABEL[layer]
        if st.button(("🔁 Re-run " if rep else "▶️ Run ") + label, key=f"run_{layer}"):
            run_with_status(label, lambda say: pipeline.run_step(project, layer, say))
            st.rerun()
        if not rep:
            st.info("No report yet.")
            return
        if rep.lesson_version != project.lesson_version:
            st.warning(f"This report audited v{rep.lesson_version}; the lesson is now v{project.lesson_version}. Re-run to audit the latest version.")
        a, b, c = st.columns(3)
        a.metric("Score", f"{rep.score}/100")
        b.metric("Issues", len(rep.issues), help="high / medium / low: "
                 + " / ".join(str(sum(1 for i in rep.issues if i.severity == s)) for s in ("high", "medium", "low")))
        c.metric("Reviewer model", rep.model)
        st.write(rep.summary)
        if rep.rubric:
            st.subheader("Rubric")
            st.dataframe([{"criterion": k.replace("_", " "), "score (1-5)": v} for k, v in rep.rubric.items()], hide_index=True)
        if rep.objective_coverage:
            st.subheader("Objective coverage")
            st.dataframe([{"component": x.get("component"), "taught": ", ".join(x.get("taught_in") or []),
                           "practised": ", ".join(x.get("practised_in") or []), "assessed": ", ".join(x.get("assessed_in") or []),
                           "coverage": x.get("coverage")} for x in rep.objective_coverage], hide_index=True, width="stretch")
        if rep.claims:
            st.subheader(f"Claim verification ({len(rep.claims)} claims)")
            st.dataframe([{"verdict": x.verdict, "claim": x.claim, "section": x.section_id, "cited": ", ".join(x.cited), "note": x.note}
                          for x in rep.claims], hide_index=True, width="stretch")
        if rep.sources:
            st.subheader("Source assessment")
            by = project.research.by_id() if project.research else {}
            st.dataframe([{"source": f"{x.source_id} {by[x.source_id].title if x.source_id in by else ''}", "tier": x.tier,
                           "relevance": x.relevance, "note": x.note} for x in rep.sources], hide_index=True, width="stretch")

        st.subheader("Issues & recommendations")
        selected = []
        for i in rep.issues:
            applied = f"{layer}|{rep.created_at}|{i.id}" in project.applied_issue_ids
            box = st.checkbox(
                f"**{i.id}** · {i.severity.upper()} · {i.category} · {('section ' + i.section_id) if i.section_id else 'whole lesson'}"
                + (" · ✔ applied before" if applied else "") + {"rule": " · rule check", "llm": " · AI audit", "web": " · web verification"}[i.origin],
                value=(i.severity in ("high", "medium") and not applied and i.category != "process"),
                key=f"sel_{layer}_{rep.created_at}_{i.id}",
            )
            st.markdown(f"> {i.description}" + (f"\n>\n> *Evidence:* {i.evidence}" if i.evidence else "")
                        + (f"\n>\n> **Suggested fix:** {i.suggestion}" if i.suggestion else ""))
            if box:
                selected.append(i)

        pend = ss.pending if ss.pending and ss.pending.get("layer") == layer else None
        if not pend:
            if st.button(f"🛠️ Apply {len(selected)} selected recommendation(s)", key=f"apply_{layer}", disabled=not selected, type="primary"):
                try:
                    with st.spinner("Drafting revision..."):
                        new, log, changed = propose_revision(lesson, selected, project.research, make_llm(settings, "gen"))
                    ss.pending = {"layer": layer, "lesson": new.model_dump(), "log": log, "changed": changed,
                                  "issues": [i.id for i in selected], "base_version": project.lesson_version,
                                  "keys": [f"{layer}|{rep.created_at}|{i.id}" for i in selected]}
                    st.rerun()
                except Exception as e:
                    st.error(f"Could not draft the revision: {e}. Your lesson is unchanged - press the button again to retry.")
        else:
            new = Lesson.model_validate(pend["lesson"])
            st.info(f"Proposed revision for issues {', '.join(pend['issues'])} - review the changes, then accept or reject.")
            if pend["base_version"] != project.lesson_version:
                st.warning("The lesson changed since this revision was drafted; accepting will overwrite those changes in a new version.")
            for entry in pend["log"]:
                st.write(f"- **{entry.get('issue_id', '')}**: {entry.get('change', '')}")
            st.caption(f"New total time: {new.total_minutes()} min")
            for lbl, d in section_diff(lesson, new):
                with st.expander(f"Diff · {lbl}", expanded=True):
                    st.code(d or "(minutes only)", language="diff")
            c1, c2 = st.columns(2)
            if c1.button("✅ Accept revision", key=f"acc_{layer}", type="primary"):
                ver = store.commit_lesson(project, new, f"Applied {'QC1' if layer == 'qc_factual' else 'QC2'} recommendations {', '.join(pend['issues'])}")
                project.applied_issue_ids = sorted(set(project.applied_issue_ids) | set(pend["keys"]))
                store.save(project)
                ss.pending = None
                flash("success", f"Revision saved as v{ver}. Re-run the QC layers to audit the new version.")
                st.rerun()
            if c2.button("✖️ Reject", key=f"rej_{layer}"):
                ss.pending = None
                st.rerun()
        st.download_button("⬇️ Download this report (Markdown)", qc_report_md(rep, project.research),
                           file_name=f"{layer}_report.md", key=f"dl_{layer}")


render_qc("qc_factual", tabs[2])
render_qc("qc_instructional", tabs[3])

# ====================================================================== preview
with tabs[4]:
    if not lesson:
        st.info("Nothing to preview yet.")
    else:
        md = lesson_md(lesson, project.research, include_refs=False)
        st.markdown(md)
        by = project.research.by_id()
        vids = [by[v.source_id] for v in lesson.videos if v.source_id in by]
        if vids:
            st.subheader("Watch")
            cols = st.columns(min(3, len(vids)))
            for col, v in zip(cols, vids):
                with col:
                    st.video(v.url)
                    st.caption(f"{v.title} · {v.channel}")
        st.markdown(references_md(lesson, project.research))

# ====================================================================== export
with tabs[5]:
    if not lesson:
        st.info("Nothing to export yet.")
    else:
        for layer in ("qc_factual", "qc_instructional"):
            rep = project.qc_reports.get(layer)
            if not rep:
                st.warning(f"{STEP_LABEL[layer]} has not been run - its report will be missing from the export.")
            elif rep.lesson_version != project.lesson_version:
                st.warning(f"{STEP_LABEL[layer]} report is for v{rep.lesson_version}, lesson is v{project.lesson_version}.")
        slug = project.id
        try:
            z = export_zip(project)
            zip_path = store.export_dir(project.id) / f"{slug}-v{project.lesson_version}.zip"
            st.download_button("📦 Download everything (ZIP: lesson MD/HTML/DOCX, references, both QC reports, sources)",
                               z, file_name=zip_path.name, mime="application/zip", type="primary",
                               on_click=lambda: zip_path.write_bytes(z))
            c1, c2, c3, c4 = st.columns(4)
            c1.download_button("Lesson (.md)", lesson_md(lesson, project.research), file_name=f"{slug}.md")
            c2.download_button("Lesson (.html)", lesson_html(lesson, project.research), file_name=f"{slug}.html", mime="text/html")
            c3.download_button("Lesson (.docx)", lesson_docx(lesson, project.research), file_name=f"{slug}.docx",
                               mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
            c4.download_button("References (.md)", references_md(lesson, project.research), file_name=f"{slug}-references.md")
            st.caption(f"A copy of the ZIP is also saved in `{store.export_dir(project.id)}`.")
        except Exception as e:
            st.error(f"Export failed: {e}")

# ====================================================================== history
with tabs[6]:
    if not project.versions:
        st.info("No versions yet.")
    else:
        st.dataframe([{"version": f"v{x.version}", "note": x.note, "saved": x.created_at} for x in reversed(project.versions)],
                     hide_index=True, width="stretch")
        pick = st.selectbox("View version", [x.version for x in reversed(project.versions)], format_func=lambda n: f"v{n}")
        old = store.load_version(project.id, pick)
        if old:
            if pick != project.lesson_version and st.button(f"↩️ Restore v{pick} as a new version"):
                ver = store.commit_lesson(project, old, f"Restored from v{pick}")
                flash("success", f"Restored v{pick} as v{ver}.")
                st.rerun()
            with st.expander("Show content", expanded=False):
                st.markdown(lesson_md(old, project.research, include_refs=False))

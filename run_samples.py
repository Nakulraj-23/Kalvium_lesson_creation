"""Headless end-to-end run: generates both test lessons, runs both QC layers, applies the
high/medium QC recommendations, re-runs QC, and exports everything into samples/.
Usage:  python run_samples.py        (log goes to run_log.txt)"""
import io, json, sys, time, zipfile
from pathlib import Path

from lesson_tool.apply import propose_revision
from lesson_tool.config import get_settings
from lesson_tool.export import export_zip
from lesson_tool.llm import make_llm
from lesson_tool.pipeline import Pipeline
from lesson_tool.storage import Store

LESSONS = [
    ("http-requests-and-responses", "HTTP Requests and Responses",
     "Explain GET and POST methods and distinguish between 2xx, 4xx, and 5xx response status categories.",
     "Beginner web-development students"),
    ("sql-joins", "SQL Joins: Combining Data from Multiple Tables",
     "Differentiate INNER JOIN, LEFT JOIN and FULL OUTER JOIN and choose the correct join to answer a given query.",
     "Undergraduate students who know basic SELECT queries"),
]

s = get_settings()
store = Store(s.data_dir)
pipe = Pipeline(store, s)
summary = {}
for slug, title, obj, aud in LESSONS:
    print(f"\n===== {title} =====", flush=True)
    existing = [x for x in store.list_projects() if x["title"] == title]
    p = store.load(existing[0]["id"]) if existing else store.new_project(title, obj, aud)
    if p.lesson is None and any("default queries" in w or "grounded_search" in w for w in p.steps["research"].warnings):
        p.steps["research"].state = "pending"  # first research ran with a broken model - redo it properly
    todo = [k for k in ("research", "generate", "qc_factual", "qc_instructional") if p.steps[k].state != "done"]
    ok = pipe.run_all(p, progress=lambda m: print("  ", m, flush=True), start_at=todo[0]) if todo else True
    for k, st in p.steps.items():
        print(f"  step {k}: {st.state} {st.error or ''}", flush=True)
        for w in st.warnings:
            print(f"     warning: {w}", flush=True)
    if not ok:
        summary[slug] = "FAILED"
        continue
    before = {k: r.score for k, r in p.qc_reports.items()}
    issues = [i for r in p.qc_reports.values() for i in r.issues if i.severity in ("high", "medium") and i.category != "process"][:6]
    if issues:
        print(f"  applying {len(issues)} QC recommendations...", flush=True)
        try:
            new, log, changed = propose_revision(p.lesson, issues, p.research, make_llm(s, "gen"))
            store.commit_lesson(p, new, "Applied QC recommendations " + ", ".join(i.id for i in issues))
            for e in log:
                print("     -", e.get("issue_id"), e.get("change"), flush=True)
            time.sleep(5)
            pipe.run_step(p, "qc_factual"); pipe.run_step(p, "qc_instructional")
        except Exception as e:
            print("  apply failed:", e, flush=True)
    after = {k: r.score for k, r in p.qc_reports.items()}
    out = Path("samples") / slug
    out.mkdir(parents=True, exist_ok=True)
    zipfile.ZipFile(io.BytesIO(export_zip(p))).extractall(out)
    summary[slug] = {"scores_before": before, "scores_after": after, "version": p.lesson_version, "project_id": p.id}
    print("  exported to", out, summary[slug], flush=True)
    time.sleep(10)
print("\nSUMMARY", json.dumps(summary, indent=2))

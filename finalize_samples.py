"""Final step for the two test lessons (run once after run_samples.py).

1. Applies the INSTRUCTOR EDITS below. These are corrections I made by hand after checking the
   generated lessons against primary sources (docs/FACT_CHECK.md). The QC layers did not catch them,
   and the verification log in FACT_CHECK.md explains each one.
2. Saves the edits as a new lesson version (the history is kept).
3. Re-runs BOTH QC layers on the corrected version, so the reports audit the final lesson.
4. Exports everything to samples/<lesson>/.

Usage:  python finalize_samples.py
"""
import io
import zipfile
from pathlib import Path

from lesson_tool.config import get_settings
from lesson_tool.export import export_zip
from lesson_tool.generator import normalize_citations, rebalance_minutes
from lesson_tool.pipeline import Pipeline
from lesson_tool.storage import Store

NB = " "  # the model put narrow no-break spaces before citations

EDITS = {
    "HTTP Requests and Responses": [
        ("s2", "- `Content-Type` describes the body you are sending (only for POST).",
         "- `Content-Type` describes the media type of a message body. You send it whenever your request has a body "
         "(POST, PUT, PATCH), and servers also send it on responses."),
        ("s4", """### Example 3 – Bad request (4xx)
```bash
curl -i -X POST https://jsonplaceholder.typicode.com/posts \\
     -H "Content-Type: application/json" \\
     -d '{"invalid":"data"}'
```
Possible response:
```
HTTP/1.1 400 Bad Request
```""",
         """### Example 3 – Client error (4xx)
JSONPlaceholder is a *fake* API: it accepts any body and does not validate input, so you can't trigger a 400 there.
Ask for a resource that doesn't exist instead:
```bash
curl -i https://jsonplaceholder.typicode.com/posts/99999
```
Response:
```
HTTP/1.1 404 Not Found
```"""),
        ("s5", "5. **Trigger a server error** (optional – use a mock service that returns 500, e.g., a local mock server configured for this purpose).\n6. Fill the table below:\n",
         "5. **Trigger a server error** (optional): `curl -s -o /dev/null -w \"%{http_code}\\n\" https://httpbin.org/status/500` "
         "(httpbin returns whatever status code you ask for).\n6. Fill the table below:\n\n"),
    ],
    "SQL Joins: Combining Data from Multiple Tables": [
        ("s2", f"The join is evaluated left‑to‑right unless parentheses change the order{NB}[S6].",
         f"When several joins are chained they nest left‑to‑right, and parentheses can change the nesting{NB}[S6]. "
         "For INNER JOINs the nesting doesn't change the result, but for OUTER JOINs it can."),
        ("s5", f"PostgreSQL evaluates joins left‑to‑right, but parentheses can be used to control the logical order{NB}[S6]. "
               f"This can affect performance because the optimizer may choose different join strategies{NB}[S8].",
         f"Joins nest left‑to‑right, and parentheses can change the nesting{NB}[S6]. With INNER JOINs the database's "
         f"query planner is free to reorder them for speed, so you write joins for *correctness* and let the optimizer "
         f"handle performance{NB}[S8]."),
        ("s8", "- Use parentheses to guide join order for performance, especially with three+ tables.\n",
         "- With OUTER JOINs, order and parentheses can change the result. Check which table must keep all its rows.\n"
         "- **Pitfall:** after a LEFT JOIN, a condition on the right table in `WHERE` (e.g. `WHERE e.grade > 50`) discards "
         "the NULL rows and silently turns it into an INNER JOIN. Put that condition in the `ON` clause instead.\n"),
    ],
}


def main():
    s = get_settings()
    store = Store(s.data_dir)
    pipe = Pipeline(store, s)
    slugs = {"HTTP Requests and Responses": "http-requests-and-responses",
             "SQL Joins: Combining Data from Multiple Tables": "sql-joins"}
    for title, edits in EDITS.items():
        found = [x for x in store.list_projects() if x["title"] == title]
        if not found:
            print("project not found - run run_samples.py first:", title)
            continue
        p = store.load(found[0]["id"])
        if any(v.note.startswith("Instructor edit after manual fact-check") for v in p.versions):
            print(f"{title}: edits already applied (v{p.lesson_version})")
        else:
            new = p.lesson.model_copy(deep=True)
            applied = 0
            for sid, old, rep in edits:
                sec = next(x for x in new.sections if x.id == sid)
                if old in sec.content_md:
                    sec.content_md = sec.content_md.replace(old, rep)
                    applied += 1
                else:
                    print(f"  WARNING: text to correct not found in {sid}: {old[:60]!r}")
            for sec in new.sections:
                sec.content_md = normalize_citations(sec.content_md)
            if new.total_minutes() != new.duration_minutes:
                rebalance_minutes(new, new.duration_minutes)
            v = store.commit_lesson(p, new, f"Instructor edit after manual fact-check ({applied} corrections, see docs/FACT_CHECK.md)")
            print(f"{title}: {applied}/{len(edits)} corrections saved as v{v}, total {new.total_minutes()} min")
        print("  re-running QC 1 and QC 2 on the corrected version...")
        pipe.run_step(p, "qc_factual", progress=print)
        pipe.run_step(p, "qc_instructional", progress=print)
        for k in ("qc_factual", "qc_instructional"):
            st = p.steps[k]
            r = p.qc_reports.get(k)
            print(f"  {k}: {st.state} {st.error or ''} score={r.score if r else '-'} (audited v{r.lesson_version if r else '-'})")
        out = Path("samples") / slugs[title]
        out.mkdir(parents=True, exist_ok=True)
        zipfile.ZipFile(io.BytesIO(export_zip(p))).extractall(out)
        print("  exported to", out)
    print("\nFINALIZE DONE")


if __name__ == "__main__":
    main()

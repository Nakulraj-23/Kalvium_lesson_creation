# Sample outputs (real runs)

| Folder | Contents |
|---|---|
| [`http-requests-and-responses/`](http-requests-and-responses/) | Required sample lesson |
| [`sql-joins/`](sql-joins/) | My second test lesson |

Each folder has:
* `lesson.md` / `lesson.html` / `lesson.docx`: the final lesson (45 min, inline numbered citations, videos, references)
* `references.md`: the reference list (cited web sources, books, videos)
* `qc1_factual_report.md` (+ `.json`): QC Layer 1, research & factual accuracy audit
* `qc2_instructional_report.md` (+ `.json`): QC Layer 2, instructional quality audit
* `research_sources.json`: every source the research step found, with reliability tier and the excerpt the model read
* `project.json`: full project state (steps, version history, reports)

How they were produced: `run_samples.py` (research → generate → QC 1 → QC 2 → apply QC recommendations → re-run QC), then a manual fact-check ([docs/FACT_CHECK.md](../docs/FACT_CHECK.md)), then `finalize_samples.py` (instructor corrections saved as a new version → both QC layers re-run → export).

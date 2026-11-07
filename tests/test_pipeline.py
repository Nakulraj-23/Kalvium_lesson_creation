import io
import json
import zipfile

from docx import Document

from lesson_tool.apply import propose_revision, section_diff
from lesson_tool.export import export_zip, lesson_md
from lesson_tool.fake_llm import FakeLLM
from lesson_tool.llm import parse_json
from lesson_tool.pipeline import Pipeline, validate_inputs
from lesson_tool.research.reliability import tier_for

from .conftest import make_providers

T = "HTTP Requests and Responses"
O = "Explain GET and POST methods and distinguish between 2xx, 4xx, and 5xx response status categories."


def full(store, settings, providers, links_ok):
    p = store.new_project(T, O)
    pipe = Pipeline(store, settings, providers=providers, link_checker=links_ok)
    assert pipe.run_all(p)
    return p, pipe


def test_input_validation():
    assert validate_inputs("", "") == ["Lesson Title is required.", "Learning Objective is required."]
    assert any("too short" in e for e in validate_inputs("HT", "learn http"))
    assert validate_inputs(T, O) == []


def test_full_pipeline(store, settings, providers, links_ok):
    p, _ = full(store, settings, providers, links_ok)
    assert all(s.state == "done" for s in p.steps.values())
    r = p.research
    assert [s.domain for s in r.sources][0] == "developer.mozilla.org"  # tier A first
    assert not any("reddit" in s.url for s in r.sources)  # tier D excluded
    assert any(s.kind == "grounded" for s in r.sources) and any(s.kind == "wikipedia" for s in r.sources)
    assert [v.id for v in r.videos] == ["V1"]  # 10-hour video filtered
    assert any("snippet" in w for w in p.steps["research"].warnings)  # blog page unreadable -> snippet used
    # generator drops invented ids
    assert [v.source_id for v in p.lesson.videos] == ["V1"] and p.lesson.further_reading == ["B1"]
    assert p.lesson_version == 1 and p.lesson.total_minutes() == 45

    qc1 = p.qc_reports["qc_factual"]
    descs = " ".join(i.description for i in qc1.issues)
    assert "S99" in descs  # non-existent citation
    assert "invented-site.io" in descs and "example.com" not in descs
    assert any(i.category == "factual_error" and "POST is idempotent" in i.description for i in qc1.issues)
    assert qc1.issues[0].severity == "high"
    assert 0 <= qc1.score <= 100 and qc1.sources

    qc2 = p.qc_reports["qc_instructional"]
    assert not any(i.category == "timing" and i.section_id is None for i in qc2.issues)
    assert any("O2" in i.description and i.category == "assessment" for i in qc2.issues)
    assert qc2.rubric["clarity"] == 4 and qc2.objective_coverage


def test_failure_preserves_work_and_retry(store, settings, providers, links_ok):
    p, pipe = full(store, settings, providers, links_ok)
    before = p.lesson.model_dump()
    FakeLLM.fail_tasks = {"generate_lesson"}
    assert not pipe.run_step(p, "generate")
    reloaded = store.load(p.id)
    assert reloaded.steps["generate"].state == "failed" and "simulated failure" in reloaded.steps["generate"].error
    assert reloaded.lesson.model_dump() == before and reloaded.lesson_version == 1
    assert reloaded.qc_reports["qc_factual"]  # reports kept
    FakeLLM.fail_tasks = set()
    assert pipe.run_step(reloaded, "generate")  # retry
    assert reloaded.lesson_version == 2 and store.load_version(p.id, 1) is not None


def test_research_total_failure_blocks_generation(store, settings, links_ok):
    settings.use_grounded_search = False
    p = store.new_project(T, O)
    pipe = Pipeline(store, settings, providers=make_providers(fail_all_text=True), link_checker=links_ok)
    assert not pipe.run_all(p)
    p = store.load(p.id)
    assert p.steps["research"].state == "failed" and "No usable text sources" in p.steps["research"].error
    assert not pipe.run_step(p, "generate")
    assert "Research must complete" in store.load(p.id).steps["generate"].error


def test_grounded_and_plan_failures_are_non_fatal(store, settings, providers, links_ok):
    FakeLLM.fail_tasks = {"research_plan", "grounded_research", "qc_grounded_verify"}
    p, _ = full(store, settings, providers, links_ok)
    w = " ".join(p.steps["research"].warnings)
    assert "default queries" in w and "grounded_search" in w
    assert any(i.category == "process" for i in p.qc_reports["qc_factual"].issues)


def test_broken_link_flagged(store, settings, providers):
    p = store.new_project(T, O)
    Pipeline(store, settings, providers=providers, link_checker=lambda urls: {u: "mozilla" not in u for u in urls}).run_all(p)
    assert any("broken" in i.description and "mozilla" in i.description for i in p.qc_reports["qc_factual"].issues)


def test_apply_recommendations(store, settings, providers, links_ok):
    p, _ = full(store, settings, providers, links_ok)
    issue = p.qc_reports["qc_instructional"].issues[0]
    new, log, changed = propose_revision(p.lesson, [issue], p.research, FakeLLM())
    assert changed == ["s6"] and log
    diffs = section_diff(p.lesson, new)
    assert diffs and "503" in diffs[0][1]
    v = store.commit_lesson(p, new, "Applied QC2")
    assert v == 2 and "503" in store.load(p.id).lesson.sections[5].content_md
    assert store.load_version(p.id, 1).sections[5].content_md != new.sections[5].content_md


def test_export(store, settings, providers, links_ok):
    p, _ = full(store, settings, providers, links_ok)
    md = lesson_md(p.lesson, p.research)
    assert "[1]" in md and "[citation needed]" in md and "## References" in md and "[S1]" not in md
    z = zipfile.ZipFile(io.BytesIO(export_zip(p)))
    names = set(z.namelist())
    assert {"lesson.md", "lesson.html", "lesson.docx", "references.md", "qc1_factual_report.md",
            "qc2_instructional_report.md", "qc1_factual_report.json", "project.json"} <= names
    assert "Claim verification" in z.read("qc1_factual_report.md").decode()
    assert "Objective coverage" in z.read("qc2_instructional_report.md").decode()
    assert "youtube-nocookie.com/embed/abc123" in z.read("lesson.html").decode()
    doc = Document(io.BytesIO(z.read("lesson.docx")))
    assert any(T in para.text for para in doc.paragraphs) and doc.tables


def test_storage_resilience(store, tmp_path):
    p = store.new_project(T, O)
    (store.root / "broken").mkdir()
    (store.root / "broken" / "project.json").write_text("{not json")
    ids = [x["id"] for x in store.list_projects()]
    assert p.id in ids and "broken" not in ids
    assert not list(store.root.rglob(".tmp-*"))


def test_parse_json_and_tiers():
    assert parse_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert parse_json('Sure! {"a": [1,2]} hope this helps') == {"a": [1, 2]}
    assert tier_for("https://www.rfc-editor.org/rfc/rfc9110") == "A"
    assert tier_for("https://cs.stanford.edu/x") == "A"
    assert tier_for("https://en.wikipedia.org/wiki/HTTP") == "B"
    assert tier_for("https://www.geeksforgeeks.org/x") == "C"
    assert tier_for("https://www.quora.com/x") == "D"


def test_parse_json_handles_markdown_newlines_and_truncation():
    raw = '{"sections": [{"id": "s1", "content_md": "### Title\n- point one [S1]\n```\nGET / HTTP/1.1\n```"}]}'
    assert parse_json(raw)["sections"][0]["content_md"].startswith("### Title\n")
    assert parse_json('Here you go:\n```json\n' + raw + '\n```')["sections"][0]["id"] == "s1"
    assert parse_json('{"sections": [{"id": "s1", "content_md": "cut off mid')["sections"][0]["id"] == "s1"


def test_citation_normalisation_title_cleanup_and_rebalance():
    from lesson_tool.generator import clean_title, normalize_citations, rebalance_minutes
    from lesson_tool.models import Lesson, Section

    assert normalize_citations("x【S1】 y【S5†L3】 z[S2, S3]") == "x[S1] y[S5] z[S2][S3]"
    assert clean_title("RFC 7231 - Semantics ...List of HTTP status codes - Wikipedia") == "RFC 7231 - Semantics"
    les = Lesson(title="t", objective="o", sections=[
        Section(id="s1", type="hook", title="h", minutes=3, content_md="x"),
        Section(id="s2", type="concept", title="c", minutes=20, content_md="x"),
        Section(id="s3", type="activity", title="a", minutes=26, content_md="x")])
    rebalance_minutes(les, 45)
    assert les.total_minutes() == 45 and les.sections[0].minutes == 3

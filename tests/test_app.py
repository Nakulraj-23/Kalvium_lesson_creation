"""UI smoke tests with Streamlit's AppTest (offline, fake LLM)."""
import os

from streamlit.testing.v1 import AppTest

from lesson_tool.pipeline import Pipeline

APP = os.path.join(os.path.dirname(__file__), "..", "app.py")


def test_empty_inputs_show_errors(settings, monkeypatch):
    monkeypatch.setenv("LESSON_TOOL_LLM", "fake")
    monkeypatch.setenv("LESSON_DATA_DIR", str(settings.data_dir))
    at = AppTest.from_file(APP, default_timeout=30).run()
    assert not at.exception
    at.button(key="FormSubmitter:create-🚀 Research & generate lesson").click().run()
    errs = [e.value for e in at.error]
    assert "Lesson Title is required." in errs and "Learning Objective is required." in errs


def test_project_views_render(settings, store, providers, links_ok, monkeypatch):
    monkeypatch.setenv("LESSON_TOOL_LLM", "fake")
    monkeypatch.setenv("LESSON_DATA_DIR", str(settings.data_dir))
    p = store.new_project("HTTP Requests and Responses", "Explain GET and POST methods and distinguish status categories.")
    Pipeline(store, settings, providers=providers, link_checker=links_ok).run_all(p)
    at = AppTest.from_file(APP, default_timeout=30)
    at.session_state["project_id"] = p.id
    at.run()
    assert not at.exception, at.exception
    assert any("Score" == m.label for m in at.metric)
    # save an instructor edit -> new version
    at.text_area(key="c_1_s1").set_value("Edited hook text by instructor.")
    at.button(key="FormSubmitter:edit_1-💾 Save changes").click().run()
    assert not at.exception
    re = store.load(p.id)
    assert re.lesson_version == 2 and re.lesson.sections[0].content_md == "Edited hook text by instructor."
    assert re.versions[-1].note.startswith("Instructor edit")


def test_apply_qc_and_retry_in_ui(settings, store, providers, links_ok, monkeypatch):
    from lesson_tool.fake_llm import FakeLLM

    monkeypatch.setenv("LESSON_TOOL_LLM", "fake")
    monkeypatch.setenv("LESSON_DATA_DIR", str(settings.data_dir))
    p = store.new_project("HTTP Requests and Responses", "Explain GET and POST methods and distinguish status categories.")
    pipe = Pipeline(store, settings, providers=providers, link_checker=links_ok)
    pipe.run_all(p)
    at = AppTest.from_file(APP, default_timeout=30)
    at.session_state["project_id"] = p.id
    at.run()
    at.button(key="apply_qc_instructional").click().run()
    assert not at.exception
    assert at.session_state["pending"]["changed"] == ["s6"]
    at.button(key="acc_qc_instructional").click().run()
    re = store.load(p.id)
    assert re.lesson_version == 2 and "Applied QC2" in re.versions[-1].note
    assert any("audited v1" in w.value for w in at.warning)  # stale-report warning shown

    # simulate a failed QC step, then retry from the UI
    FakeLLM.fail_tasks = {"qc_factual"}
    pipe.run_step(re, "qc_factual")
    at.run()
    assert any("simulated failure" in e.value for e in at.error)
    FakeLLM.fail_tasks = set()
    at.button(key="retry_qc_factual").click().run()
    assert store.load(p.id).steps["qc_factual"].state == "done"

import time

import pytest
from google.genai import errors, types

from lesson_tool.config import Settings
from lesson_tool.llm import GeminiLLM, LLMError


@pytest.fixture(autouse=True)
def reset_state(monkeypatch):
    GeminiLLM._good_model, GeminiLLM._dead_models = None, set()
    monkeypatch.setattr("lesson_tool.llm.time.sleep", lambda _x: None)
    yield
    GeminiLLM._good_model, GeminiLLM._dead_models = None, set()


def ok_resp(text='{"x": 1}'):
    return types.GenerateContentResponse(candidates=[types.Candidate(content=types.Content(role="model", parts=[types.Part(text=text)]))])


def _llm(behaviour):
    s = Settings()
    s.gemini_api_key, s.gen_model = "dummy", "m-primary"
    g = GeminiLLM(s)
    calls = []

    class M:
        def generate_content(self, model, contents, config):
            calls.append(model)
            return behaviour(model, len(calls))

    g.client = type("C", (), {"models": M()})()
    return g, calls


def test_busy_model_falls_back_and_is_remembered():
    def b(model, n):
        if model == "m-primary":
            raise errors.ServerError(503, {"error": {"message": "high demand"}})
        return ok_resp()

    g, calls = _llm(b)
    assert g.generate_json("p", task="t") == {"x": 1}
    assert calls[0] == "m-primary" and calls[1] == "gemini-3.5-flash"
    g2, calls2 = _llm(b)  # new instance reuses the model that worked
    g2.generate_json("p", task="t")
    assert calls2 == ["gemini-3.5-flash"]


def test_404_model_is_skipped_without_ping_pong():
    def b(model, n):
        if model in ("m-primary", "gemini-3.5-flash"):
            raise errors.ClientError(404, {"error": {"message": "no longer available"}})
        return ok_resp()

    g, calls = _llm(b)
    g.generate_json("p", task="t")
    assert calls == ["m-primary", "gemini-3.5-flash", "gemini-3.6-flash"]


def test_hanging_call_times_out_and_moves_on():
    def b(model, n):
        if model == "m-primary":
            __import__("threading").Event().wait(2)  # simulate a hung request
        return ok_resp()

    g, calls = _llm(b)
    t = __import__("time").time()
    resp = g._call("p", types.GenerateContentConfig(), timeout=0.5)
    assert resp.text == '{"x": 1}' and calls[-1] == "gemini-3.5-flash"
    assert __import__("time").time() - t < 2


def test_thinking_rejected_is_dropped():
    def b(model, n):
        if n == 1:
            raise errors.ClientError(400, {"error": {"message": "thinking_level is not supported"}})
        return ok_resp()

    g, calls = _llm(b)
    assert g.generate_json("p", task="t") == {"x": 1} and not g._use_thinking


def test_bad_key_stops_immediately():
    def b(model, n):
        raise errors.ClientError(403, {"error": {"message": "API key not valid"}})

    g, calls = _llm(b)
    with pytest.raises(LLMError, match="rejected the API key"):
        g.generate_json("p", task="t")
    assert len(calls) == 1


def test_everything_down_gives_clear_error():
    def b(model, n):
        raise errors.ServerError(503, {"error": {"message": "overloaded"}})

    g, calls = _llm(b)
    with pytest.raises(LLMError, match="server error"):
        g.generate_json("p", task="t")


def test_missing_key():
    s = Settings()
    s.gemini_api_key = ""
    with pytest.raises(LLMError, match="GEMINI_API_KEY is not set"):
        GeminiLLM(s)

import json

import pytest

from lesson_tool.config import Settings
from lesson_tool.groq_llm import GroqLLM
from lesson_tool.llm import LLMError, make_llm


class R:
    def __init__(self, code, body=None, headers=None, text=None):
        self.status_code, self._b, self.headers = code, body, headers or {}
        self.text = text if text is not None else json.dumps(body or {})

    def json(self):
        return self._b

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(self.status_code)


def ok(content):
    return R(200, {"choices": [{"message": {"content": content}}]})


@pytest.fixture(autouse=True)
def reset(monkeypatch):
    GroqLLM._good, GroqLLM._dead, GroqLLM._available = {}, set(), None
    monkeypatch.setattr("lesson_tool.groq_llm.time.sleep", lambda _x: None)
    yield
    GroqLLM._good, GroqLLM._dead, GroqLLM._available = {}, set(), None


def make(monkeypatch, post, models=("llama-3.3-70b-versatile", "openai/gpt-oss-120b", "whisper-large-v3", "llama-3.1-8b-instant"), purpose="gen"):
    calls = []

    def fake_get(self, url, timeout=None):
        return R(200, {"data": [{"id": m} for m in models]})

    def fake_post(self, url, json=None, timeout=None):
        calls.append(json["model"])
        return post(json, len(calls))

    monkeypatch.setattr("requests.Session.get", fake_get)
    monkeypatch.setattr("requests.Session.post", fake_post)
    s = Settings()
    s.groq_api_key, s.gemini_api_key = "gsk_test", ""
    return GroqLLM(s, purpose=purpose), calls


def test_provider_selection():
    s = Settings()
    s.groq_api_key, s.llm_provider, s.llm_backend = "gsk_x", "", "gemini"
    assert s.provider == "groq"
    s.llm_provider = "gemini"
    assert s.provider == "gemini"


def test_chain_order_skips_audio_and_qc_uses_other_model(monkeypatch):
    g, _ = make(monkeypatch, lambda b, n: ok('{"a":1}'))
    assert g.chain[:2] == ["openai/gpt-oss-120b", "llama-3.3-70b-versatile"] and "whisper-large-v3" not in g.chain
    q, _ = make(monkeypatch, lambda b, n: ok('{"a":1}'), purpose="qc")
    assert q.chain[0] == "llama-3.3-70b-versatile"


def test_json_and_reasoning_settings(monkeypatch):
    seen = {}

    def post(body, n):
        seen.update(body)
        return ok('{"x": 2}')

    g, _ = make(monkeypatch, post)
    assert g.generate_json("p", task="t") == {"x": 2}
    assert seen["response_format"] == {"type": "json_object"} and seen["reasoning_effort"] == "low"


def test_413_moves_to_bigger_model_and_429_waits(monkeypatch):
    def post(body, n):
        if body["model"] == "openai/gpt-oss-120b":
            return R(413, text="Request too large for model on tokens per minute (TPM)")
        if n == 2:
            return R(429, headers={"retry-after": "3"}, text="Rate limit reached ... tokens per minute")
        return ok('{"ok": true}')

    g, calls = make(monkeypatch, post)
    assert g.generate_json("p", task="generate_lesson") == {"ok": True}
    assert calls == ["openai/gpt-oss-120b", "llama-3.3-70b-versatile", "llama-3.3-70b-versatile"]


def test_daily_limit_and_500_skip(monkeypatch):
    def post(body, n):
        if body["model"] == "openai/gpt-oss-120b":
            return R(429, text="Rate limit reached for model on tokens per day (TPD)")
        if body["model"] == "llama-3.3-70b-versatile":
            return R(503, text="over capacity")
        return ok('{"ok": 1}')

    g, calls = make(monkeypatch, post)
    g.generate_json("p", task="t")
    assert calls[-1] == "llama-3.1-8b-instant"


def test_invalid_json_repaired(monkeypatch):
    answers = iter(["not json at all", '{"fixed": true}'])
    g, _ = make(monkeypatch, lambda b, n: ok(next(answers)))
    assert g.generate_json("p", task="t") == {"fixed": True}


def test_bad_key(monkeypatch):
    monkeypatch.setattr("requests.Session.get", lambda self, url, timeout=None: R(401, text="invalid key"))
    s = Settings()
    s.groq_api_key = "gsk_bad"
    with pytest.raises(LLMError, match="rejected the API key"):
        GroqLLM(s)


def test_grounding_without_gemini_key_is_reported(monkeypatch):
    g, _ = make(monkeypatch, lambda b, n: ok("{}"))
    with pytest.raises(LLMError, match="grounding skipped"):
        g.generate_grounded("x", task="grounded_research")

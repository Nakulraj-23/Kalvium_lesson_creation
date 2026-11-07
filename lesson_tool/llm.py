"""Thin wrapper around Google Gemini (google-genai SDK).

Responsibilities:
* JSON-mode generation with validation and one automatic "repair" retry if the model
  returns malformed JSON;
* Google-Search-grounded generation (used for research and for QC1 independent fact checks);
* retry with exponential backoff on rate limits / transient server errors;
* translating SDK errors into readable messages for the UI.
"""
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from typing import Any, Optional

from .config import Settings


class LLMError(RuntimeError):
    """Raised with a human-readable message the UI can show directly."""


@dataclass
class GroundedResult:
    text: str
    sources: list[dict] = field(default_factory=list)  # [{"title":..., "url":...}]
    supports: list[dict] = field(default_factory=list)  # [{"text":..., "source_idx":[..]}]


_JSON_FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.S)


def parse_json(text: str) -> Any:
    """Parse model JSON robustly: markdown fences, leading prose, raw newlines inside strings
    (very common when the model writes markdown into a JSON field) and truncated output."""
    if text is None or not str(text).strip():
        raise ValueError("empty response")
    t = str(text).strip()
    if not t.startswith(("{", "[")):
        # only unwrap a ```json fence when the answer itself is wrapped (lesson content contains code fences too)
        m = re.match(r"^[^{\[]*?```(?:json)?\s*([\[{].*[\]}])\s*```", t, re.S)
        if m:
            t = m.group(1).strip()
    candidates = [t]
    for open_c, close_c in (("{", "}"), ("[", "]")):
        s_, e_ = t.find(open_c), t.rfind(close_c)
        if s_ != -1 and e_ > s_:
            candidates.append(t[s_ : e_ + 1])
    for c in candidates:
        try:
            return json.loads(c, strict=False)  # strict=False allows raw newlines/tabs inside strings
        except json.JSONDecodeError:
            continue
    try:
        import json_repair

        start = min([i for i in (t.find("{"), t.find("[")) if i != -1], default=0)
        val = json_repair.loads(t[start:])
        if val not in ("", None, [], {}):
            return val
    except Exception:
        pass
    raise ValueError(f"could not parse JSON (first chars: {t[:80]!r})")


class BaseLLM:
    model: str = ""
    excerpt_chars: int = 1800  # how much of each source excerpt fits in a prompt for this provider
    max_sources: int = 12

    def generate_json(self, prompt: str, *, task: str, system: str = "", temperature: float = 0.3) -> Any:
        raise NotImplementedError

    def generate_grounded(self, prompt: str, *, task: str) -> GroundedResult:
        raise NotImplementedError


FALLBACK_MODELS = ["gemini-3.5-flash", "gemini-3.6-flash", "gemini-3.7-flash", "gemini-3.8-flash",
                   "gemini-3.5-flash-lite", "gemini-3.1-flash-lite"]


def _log(msg: str) -> None:
    print(f"[llm] {msg}", flush=True)


class GeminiLLM(BaseLLM):
    """Robust Gemini client.

    * hard wall-clock timeout per call (the SDK call runs in a worker thread), so a call can never hang;
    * on timeout / overload (429, 5xx) / model-not-found it immediately moves to the next model in the chain;
    * the first model that answers is remembered (class level) and reused by every later step;
    * low 'thinking' level for speed; if a model rejects that setting it is dropped automatically.
    """

    _good_model: Optional[str] = None  # shared across instances: once a model works, keep using it
    _dead_models: set = set()

    def __init__(self, settings: Settings, model: Optional[str] = None):
        if not settings.gemini_api_key:
            raise LLMError("GEMINI_API_KEY is not set. Add it to your .env file (free key: https://aistudio.google.com/apikey).")
        from google import genai  # imported lazily so tests never need the SDK
        from google.genai import types

        self.client = genai.Client(api_key=settings.gemini_api_key, http_options=types.HttpOptions(timeout=180_000))
        preferred = model or settings.gen_model
        chain = [GeminiLLM._good_model, preferred, *FALLBACK_MODELS]
        self.chain = [m for i, m in enumerate(chain) if m and m not in chain[:i]]
        self.model = self.chain[0]
        self._use_thinking = True
        self.passes = 3
        self.grounded_timeout = 120

    # ---------- low level ----------
    def _one(self, model: str, contents: str, config, timeout: float):
        import concurrent.futures as cf

        ex = cf.ThreadPoolExecutor(max_workers=1)
        fut = ex.submit(self.client.models.generate_content, model=model, contents=contents, config=config)
        try:
            return fut.result(timeout=timeout)
        finally:
            ex.shutdown(wait=False, cancel_futures=True)

    def _call(self, contents: str, config, timeout: float = 120) -> Any:
        import concurrent.futures as cf

        from google.genai import errors

        last: Optional[Exception] = None
        for rnd in range(self.passes):  # passes over the model chain
            for model in self.chain:
                if model in GeminiLLM._dead_models:
                    continue
                cfg = config
                if self._use_thinking:
                    from google.genai import types

                    cfg = config.model_copy(update={"thinking_config": types.ThinkingConfig(thinking_level="LOW")})
                _log(f"calling {model} (pass {rnd + 1}, timeout {int(timeout)}s)...")
                t0 = time.time()
                try:
                    resp = self._one(model, contents, cfg, timeout)
                except cf.TimeoutError as e:
                    last = TimeoutError(f"{model} did not answer within {int(timeout)}s")
                    _log(f"{model} timed out -> trying next model")
                    continue
                except errors.APIError as e:
                    last = e
                    code = getattr(e, "code", None)
                    msg = str(e)
                    if code == 400 and self._use_thinking and "think" in msg.lower():
                        _log("model rejected thinking setting -> retrying without it")
                        self._use_thinking = False
                        return self._call(contents, config, timeout)
                    if code in (401, 403):
                        raise LLMError(self._friendly(e))
                    if code == 404:
                        GeminiLLM._dead_models.add(model)
                        _log(f"{model} not available for this key -> skipping")
                        continue
                    if code in (429, 500, 502, 503, 504):
                        _log(f"{model} busy (HTTP {code}) -> trying next model")
                        continue
                    raise LLMError(self._friendly(e))
                except Exception as e:  # network error etc.
                    last = e
                    _log(f"{model} network error {type(e).__name__}: {str(e)[:150]} -> trying next model")
                    continue
                if not resp.candidates or not (resp.text or "").strip():
                    last = LLMError(f"{model} returned an empty answer")
                    _log(f"{model} returned empty answer -> trying next model")
                    continue
                _log(f"{model} ok in {time.time() - t0:.1f}s")
                GeminiLLM._good_model = model
                self.model = model
                if self.chain[0] != model:
                    self.chain.remove(model)
                    self.chain.insert(0, model)
                return resp
            wait = 20 * (rnd + 1)
            if rnd < self.passes - 1:
                _log(f"all models busy - waiting {wait}s and trying again")
                time.sleep(wait)
        raise LLMError(self._friendly(last))

    @staticmethod
    def _friendly(e: Exception | None) -> str:
        code = getattr(e, "code", None)
        msg = str(e)
        if code == 429:
            return "Gemini rate limit / quota exceeded (HTTP 429). Wait a minute and press Retry."
        if code in (401, 403):
            return "Gemini rejected the API key (HTTP %s). Check GEMINI_API_KEY in .env." % code
        if isinstance(e, TimeoutError):
            return f"Gemini did not respond in time on any model ({msg}). Google's servers are busy - wait a few minutes and press Retry."
        if code == 404:
            return f"Model not found (HTTP 404). Check GEMINI_MODEL in .env. Details: {msg[:200]}"
        if code and code >= 500:
            return f"Gemini server error (HTTP {code}). Press Retry. Details: {msg[:200]}"
        return f"AI call failed: {msg[:300]}"

    # ---------- public ----------
    def generate_json(self, prompt: str, *, task: str, system: str = "", temperature: float = 0.3) -> Any:
        from google.genai import types

        cfg = types.GenerateContentConfig(
            temperature=temperature,
            response_mime_type="application/json",
            system_instruction=system or None,
        )
        big = task in ("generate_lesson", "apply_fixes", "qc_factual", "qc_instructional")
        resp = self._call(prompt, cfg, timeout=240 if big else 90)
        try:
            return parse_json(resp.text)
        except (ValueError, json.JSONDecodeError):
            repair = (
                "The following text was supposed to be a single valid JSON value but is malformed. "
                "Return ONLY the corrected JSON, no commentary.\n\n" + (resp.text or "")[:30000]
            )
            resp2 = self._call(repair, types.GenerateContentConfig(temperature=0, response_mime_type="application/json"), timeout=240)
            try:
                return parse_json(resp2.text)
            except Exception as e:
                raise LLMError(f"Model returned invalid JSON for step '{task}' twice. Press Retry. ({e})")

    def generate_grounded(self, prompt: str, *, task: str) -> GroundedResult:
        from google.genai import types

        cfg = types.GenerateContentConfig(
            temperature=0.2,
            tools=[types.Tool(google_search=types.GoogleSearch())],
        )
        resp = self._call(prompt, cfg, timeout=self.grounded_timeout)
        cand = resp.candidates[0]
        gm = getattr(cand, "grounding_metadata", None)
        sources, supports = [], []
        if gm is not None:
            for ch in getattr(gm, "grounding_chunks", None) or []:
                web = getattr(ch, "web", None)
                if web is not None:
                    sources.append({"title": getattr(web, "title", "") or "", "url": getattr(web, "uri", "") or ""})
            for sp in getattr(gm, "grounding_supports", None) or []:
                seg = getattr(sp, "segment", None)
                supports.append(
                    {
                        "text": getattr(seg, "text", "") if seg else "",
                        "source_idx": list(getattr(sp, "grounding_chunk_indices", None) or []),
                    }
                )
        return GroundedResult(text=resp.text or "", sources=sources, supports=supports)


def make_llm(settings: Settings, purpose: str = "gen") -> BaseLLM:
    """purpose: 'gen' for research/generation, 'qc' for the QC layers."""
    if settings.llm_backend == "fake":
        from .fake_llm import FakeLLM  # test-suite only

        return FakeLLM()
    if settings.provider == "groq":
        from .groq_llm import GroqLLM

        return GroqLLM(settings, purpose=purpose)
    model = settings.qc_model if purpose == "qc" else settings.gen_model
    return GeminiLLM(settings, model=model)

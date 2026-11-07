"""Groq backend (free tier, OpenAI-compatible API, very fast open-weight models).

Used for all research planning, lesson writing, QC audits and revisions.
Google-Search grounding (research notes + QC1 independent web check) is delegated to Gemini
when a Gemini key is present; if Gemini is busy/unavailable that optional step is skipped with a
warning and the rest of the run continues.

Robustness:
* models are discovered from /models, so renamed/retired models never break the run;
* per-call timeout; 429 waits for the server's retry-after (short waits) or moves to the next model
  (daily limit); 413 "request too large for this model's per-minute limit" moves to a model with a
  bigger limit; 5xx moves to the next model;
* JSON mode with automatic retry without it if a model doesn't support it.
"""
from __future__ import annotations

import re
import time
from typing import Any, Optional

import requests

from .config import Settings
from .llm import BaseLLM, GroundedResult, LLMError, parse_json

API = "https://api.groq.com/openai/v1"

# preference order: strongest first; free-tier per-minute token limits differ per model, a request that
# is too large for one model is retried on the next
PREFERRED = [
    "openai/gpt-oss-120b",
    "llama-3.3-70b-versatile",
    "moonshotai/kimi-k2-instruct-0905",
    "moonshotai/kimi-k2-instruct",
    "qwen/qwen3-32b",
    "meta-llama/llama-4-maverick-17b-128e-instruct",
    "meta-llama/llama-4-scout-17b-16e-instruct",
    "openai/gpt-oss-20b",
    "llama-3.1-8b-instant",
]
SKIP = ("whisper", "tts", "guard", "playai", "orpheus", "compound", "prompt-guard", "distil", "allam", "safeguard")


def _log(msg: str) -> None:
    print(f"[groq] {msg}", flush=True)


class GroqLLM(BaseLLM):
    excerpt_chars = 800  # keeps every prompt inside the free-tier per-minute token limits
    max_sources = 10
    _good: dict = {}  # purpose -> model that last worked
    _dead: set = set()
    _available: Optional[list[str]] = None

    def __init__(self, settings: Settings, purpose: str = "gen"):
        if not settings.groq_api_key:
            raise LLMError("GROQ_API_KEY is not set. Add it to .env (free key: https://console.groq.com/keys).")
        self.settings = settings
        self.purpose = purpose
        self.s = requests.Session()
        self.s.headers.update({"Authorization": f"Bearer {settings.groq_api_key}", "Content-Type": "application/json"})
        self.chain = self._build_chain()
        self.model = self.chain[0]

    # ---------------------------------------------------------------- models
    def _build_chain(self) -> list[str]:
        if GroqLLM._available is None:
            try:
                r = self.s.get(f"{API}/models", timeout=20)
                if r.status_code in (401, 403):
                    raise LLMError("Groq rejected the API key (HTTP %s). Check GROQ_API_KEY in .env." % r.status_code)
                r.raise_for_status()
                ids = [m["id"] for m in r.json().get("data", []) if m.get("active", True)]
                GroqLLM._available = [i for i in ids if not any(x in i.lower() for x in SKIP)]
                _log("available models: " + ", ".join(GroqLLM._available[:15]))
            except LLMError:
                raise
            except Exception as e:
                _log(f"could not list models ({e}); using built-in list")
                GroqLLM._available = list(PREFERRED)
        avail = GroqLLM._available
        pref = [m.strip() for m in self.settings.groq_models.split(",") if m.strip()] or PREFERRED
        chain = [m for m in pref if m in avail] + [m for m in avail if m not in pref]
        if self.purpose == "qc" and len(chain) > 1:
            # QC layers start on a DIFFERENT model family than the writer, so the lesson isn't grading itself
            chain = chain[1:2] + chain[:1] + chain[2:]
        good = GroqLLM._good.get(self.purpose)
        if good in chain:
            chain.remove(good)
            chain.insert(0, good)
        if not chain:
            raise LLMError("No usable Groq chat models were found for this key.")
        return chain

    # ---------------------------------------------------------------- core call
    def _chat(self, messages: list[dict], *, temperature: float, json_mode: bool, max_tokens: int, timeout: int) -> str:
        last = "unknown error"
        for rnd in range(3):
            for model in self.chain:
                if model in GroqLLM._dead:
                    continue
                body: dict[str, Any] = {"model": model, "messages": messages, "temperature": temperature,
                                        "max_completion_tokens": max_tokens}
                if json_mode:
                    body["response_format"] = {"type": "json_object"}
                if "gpt-oss" in model:
                    body["reasoning_effort"] = "low"
                if "qwen3" in model:
                    body["reasoning_effort"] = "none"
                for attempt in range(3):
                    _log(f"calling {model} (pass {rnd + 1})...")
                    t0 = time.time()
                    try:
                        r = self.s.post(f"{API}/chat/completions", json=body, timeout=timeout)
                    except requests.RequestException as e:
                        last = f"{model}: network error {type(e).__name__}"
                        _log(f"{last} -> next model")
                        break
                    if r.status_code == 200:
                        try:
                            choice = r.json()["choices"][0]
                            text = choice["message"].get("content") or ""
                            finish = choice.get("finish_reason")
                        except Exception:
                            text, finish = "", None
                        if finish == "length":
                            _log(f"{model}: answer was cut off at the token limit (will be repaired if possible)")
                        if not text.strip():
                            last = f"{model}: empty answer"
                            _log(f"{last} -> next model")
                            break
                        _log(f"{model} ok in {time.time() - t0:.1f}s")
                        GroqLLM._good[self.purpose] = model
                        self.model = model
                        return text
                    msg = r.text[:300]
                    last = f"{model}: HTTP {r.status_code} {msg}"
                    if r.status_code in (401, 403):
                        raise LLMError("Groq rejected the API key (HTTP %s). Check GROQ_API_KEY in .env." % r.status_code)
                    if r.status_code == 400 and json_mode and ("response_format" in msg or "json" in msg.lower()):
                        if "json_validate_failed" in msg or "failed_generation" in msg:
                            _log(f"{model} produced invalid JSON -> retrying")
                            continue
                        _log(f"{model} does not support JSON mode -> retrying without it")
                        body.pop("response_format", None)
                        continue
                    if r.status_code == 400 and "reasoning_effort" in msg:
                        body.pop("reasoning_effort", None)
                        continue
                    if r.status_code == 404 or (r.status_code == 400 and "decommissioned" in msg):
                        GroqLLM._dead.add(model)
                        _log(f"{model} unavailable -> skipping")
                        break
                    if r.status_code == 413:
                        _log(f"{model}: request bigger than its free per-minute limit -> next model")
                        break
                    if r.status_code == 429:
                        wait = self._retry_after(r)
                        if "per day" in msg.lower() or "tpd" in msg.lower() or "rpd" in msg.lower() or wait > 30:
                            _log(f"{model}: daily/long limit reached -> next model")
                            break
                        _log(f"{model}: rate limited, waiting {wait:.0f}s")
                        time.sleep(wait)
                        continue
                    if r.status_code >= 500:
                        _log(f"{model}: server error {r.status_code} -> next model")
                        break
                    raise LLMError(f"Groq request failed: HTTP {r.status_code} {msg}")
            if rnd < 2:
                _log(f"all models busy - waiting {20 * (rnd + 1)}s")
                time.sleep(20 * (rnd + 1))
        raise LLMError(f"All Groq models failed or are rate-limited right now. Wait a minute and press Retry. Last error: {last[:250]}")

    def _dump(self, task: str, text: str) -> None:
        try:
            d = self.settings.data_dir / "debug"
            d.mkdir(parents=True, exist_ok=True)
            (d / f"{task}-{int(time.time())}.txt").write_text(text or "(empty)", encoding="utf-8")
        except Exception:
            pass

    @staticmethod
    def _retry_after(r) -> float:
        h = r.headers.get("retry-after")
        try:
            if h:
                return min(float(h) + 1, 120)
        except ValueError:
            pass
        m = re.search(r"try again in (?:(\d+)m)?([\d.]+)s", r.text)
        if m:
            return min(int(m.group(1) or 0) * 60 + float(m.group(2)) + 1, 120)
        return 10

    # ---------------------------------------------------------------- public
    def generate_json(self, prompt: str, *, task: str, system: str = "", temperature: float = 0.3) -> Any:
        # output budgets sized so prompt + output fit the free-tier per-minute token limits
        out_tokens = {"generate_lesson": 6000, "apply_fixes": 5000, "qc_factual": 3500, "qc_instructional": 3000}.get(task, 1500)
        big = task in ("generate_lesson", "apply_fixes", "qc_factual", "qc_instructional")
        sys_msg = (system + "\n\n" if system else "") + "Respond with a single valid JSON object only."
        messages = [{"role": "system", "content": sys_msg}, {"role": "user", "content": prompt}]
        text = self._chat(messages, temperature=temperature, json_mode=True, max_tokens=out_tokens,
                          timeout=180 if big else 60)
        try:
            return parse_json(text)
        except Exception as e:
            self._dump(task, text)
            _log(f"answer was not valid JSON ({e}) -> asking the model to repair it")
            fix = self._chat([{"role": "system", "content": "Return ONLY corrected valid JSON."},
                              {"role": "user", "content": "Fix this into valid JSON:\n" + text[:20000]}],
                             temperature=0, json_mode=True, max_tokens=7000, timeout=180)
            try:
                return parse_json(fix)
            except Exception as e:
                raise LLMError(f"Model returned invalid JSON for step '{task}' twice. Press Retry. ({e})")

    def generate_grounded(self, prompt: str, *, task: str) -> GroundedResult:
        """Google-Search-grounded call through Gemini (optional). Raises LLMError if unavailable,
        which the callers treat as a non-fatal, reported skip."""
        if not self.settings.gemini_api_key:
            raise LLMError("Google-Search grounding skipped (no GEMINI_API_KEY).")
        from .llm import GeminiLLM

        g = GeminiLLM(self.settings)
        g.passes = 1  # one quick try over a few Gemini models, never block the run
        g.chain = g.chain[:3]
        g.grounded_timeout = 60
        return g.generate_grounded(prompt, task=task)

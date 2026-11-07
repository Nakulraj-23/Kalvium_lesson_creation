"""Central configuration, loaded from environment / .env."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # pragma: no cover
    pass

ROOT = Path(__file__).resolve().parent.parent


def _bool(name: str, default: bool) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes", "on"}


@dataclass
class Settings:
    gemini_api_key: str = field(default_factory=lambda: os.getenv("GEMINI_API_KEY", "").strip())
    # Generation model and QC model are configurable separately so the QC layers can be
    # run by a different model than the one that wrote the lesson (more independent review).
    gen_model: str = field(default_factory=lambda: os.getenv("GEMINI_MODEL", "gemini-3.5-flash"))
    qc_model: str = field(default_factory=lambda: os.getenv("GEMINI_QC_MODEL", os.getenv("GEMINI_MODEL", "gemini-3.5-flash")))
    groq_api_key: str = field(default_factory=lambda: os.getenv("GROQ_API_KEY", "").strip())
    # optional comma-separated preference order of Groq models; available ones are detected automatically
    groq_models: str = field(default_factory=lambda: os.getenv("GROQ_MODELS", ""))
    llm_provider: str = field(default_factory=lambda: os.getenv("LLM_PROVIDER", "").strip().lower())
    youtube_api_key: str = field(default_factory=lambda: os.getenv("YOUTUBE_API_KEY", "").strip())
    google_books_api_key: str = field(default_factory=lambda: os.getenv("GOOGLE_BOOKS_API_KEY", "").strip())
    use_grounded_search: bool = field(default_factory=lambda: _bool("USE_GROUNDED_SEARCH", True))
    data_dir: Path = field(default_factory=lambda: Path(os.getenv("LESSON_DATA_DIR", str(ROOT / "data"))))
    http_timeout: int = field(default_factory=lambda: int(os.getenv("HTTP_TIMEOUT", "15")))
    max_web_sources: int = field(default_factory=lambda: int(os.getenv("MAX_WEB_SOURCES", "8")))
    lesson_minutes: int = 45
    # "gemini" in normal use; "fake" is ONLY for the automated test-suite (offline, deterministic).
    llm_backend: str = field(default_factory=lambda: os.getenv("LESSON_TOOL_LLM", "gemini"))


    @property
    def provider(self) -> str:
        """'groq' or 'gemini'. Explicit LLM_PROVIDER wins; otherwise Groq if a Groq key exists."""
        if self.llm_provider in ("groq", "gemini"):
            return self.llm_provider
        return "groq" if self.groq_api_key else "gemini"


def get_settings() -> Settings:
    return Settings()

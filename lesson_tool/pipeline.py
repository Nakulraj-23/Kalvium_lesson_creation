"""Step runner with status tracking, retries and work preservation.

Every step:
  1. marks itself 'running' and saves;
  2. on success writes its output + 'done' and saves;
  3. on failure records the error + 'failed' and saves - WITHOUT touching existing research,
     lesson content, versions or reports. The UI then offers a Retry button for that step.
"""
from __future__ import annotations

import traceback
from typing import Callable, Optional

from .config import Settings
from .generator import generate_lesson
from .llm import make_llm
from .models import LessonProject, StepStatus, now_iso
from .qc import default_link_checker, run_qc_factual, run_qc_instructional
from .research import run_research
from .storage import Store

STEP_ORDER = ["research", "generate", "qc_factual", "qc_instructional"]
STEP_LABEL = {"research": "Research", "generate": "Lesson generation", "qc_factual": "QC 1 - Factual accuracy",
              "qc_instructional": "QC 2 - Instructional quality"}
Progress = Optional[Callable[[str], None]]


class StepBlocked(RuntimeError):
    pass


def validate_inputs(title: str, objective: str) -> list[str]:
    errs = []
    t, o = (title or "").strip(), (objective or "").strip()
    if not t:
        errs.append("Lesson Title is required.")
    elif len(t) < 3:
        errs.append("Lesson Title is too short (min 3 characters).")
    elif len(t) > 150:
        errs.append("Lesson Title is too long (max 150 characters).")
    if not o:
        errs.append("Learning Objective is required.")
    elif len(o.split()) < 4:
        errs.append("Learning Objective is too short - describe what learners should be able to do (at least 4 words).")
    elif len(o) > 600:
        errs.append("Learning Objective is too long (max 600 characters).")
    return errs


class Pipeline:
    def __init__(self, store: Store, settings: Settings, providers=None, link_checker=default_link_checker):
        self.store = store
        self.settings = settings
        self.providers = providers
        self.link_checker = link_checker

    def _set(self, p: LessonProject, step: str, state: str, error: str | None = None, warnings: list[str] | None = None):
        cur = p.steps.get(step, StepStatus())
        p.steps[step] = StepStatus(state=state, error=error, warnings=warnings if warnings is not None else cur.warnings,
                                   updated_at=now_iso())
        self.store.save(p)

    def run_step(self, p: LessonProject, step: str, progress: Progress = None) -> bool:
        """Returns True on success. Never raises for step failures - they're recorded on the project."""
        say = progress or (lambda _m: None)
        try:
            self._check_prereq(p, step)
        except StepBlocked as e:
            self._set(p, step, "failed", str(e))
            return False
        self._set(p, step, "running", warnings=[])
        try:
            warnings: list[str] = []
            if step == "research":
                kwargs = {"providers": self.providers} if self.providers else {}
                bundle, warnings = run_research(p.title, p.objective, p.audience, make_llm(self.settings, "gen"),
                                                self.settings, progress=say, **kwargs)
                p.research = bundle
            elif step == "generate":
                say("Writing the lesson from the research sources...")
                lesson = generate_lesson(p.title, p.objective, p.audience, p.research, make_llm(self.settings, "gen"),
                                         minutes=self.settings.lesson_minutes)
                note = "AI generated" if p.lesson_version == 0 else "AI regenerated (previous versions kept)"
                self.store.commit_lesson(p, lesson, note)
                if lesson.total_minutes() != lesson.duration_minutes:
                    warnings.append(f"Section minutes sum to {lesson.total_minutes()} (target {lesson.duration_minutes}); QC 2 will flag this.")
            elif step == "qc_factual":
                say("QC 1: extracting claims, checking them against sources, verifying doubtful ones on the web...")
                p.qc_reports["qc_factual"] = run_qc_factual(p.lesson, p.lesson_version, p.research, make_llm(self.settings, "qc"),
                                                            link_checker=self.link_checker,
                                                            grounded_verify=self.settings.use_grounded_search)
            elif step == "qc_instructional":
                say("QC 2: checking objective alignment, structure, timing and assessment...")
                p.qc_reports["qc_instructional"] = run_qc_instructional(p.lesson, p.lesson_version, make_llm(self.settings, "qc"))
            else:
                raise ValueError(f"unknown step {step}")
            self._set(p, step, "done", warnings=warnings)
            return True
        except Exception as e:
            msg = str(e) or type(e).__name__
            if not getattr(e, "__module__", "").startswith("lesson_tool") and type(e).__name__ not in ("LLMError", "ResearchError"):
                msg = f"{type(e).__name__}: {msg}"
            # reload from disk so a half-modified in-memory object can never be persisted
            fresh = self.store.load(p.id)
            for field in type(fresh).model_fields:
                setattr(p, field, getattr(fresh, field))
            self._set(p, step, "failed", msg[:600])
            traceback.print_exc()
            return False

    def _check_prereq(self, p: LessonProject, step: str):
        if step == "generate" and not (p.research and p.research.sources):
            raise StepBlocked("Research must complete successfully before the lesson can be generated.")
        if step in ("qc_factual", "qc_instructional") and not p.lesson:
            raise StepBlocked("Generate the lesson before running QC.")
        if step == "qc_factual" and not p.research:
            raise StepBlocked("Research data missing - re-run research.")

    def run_all(self, p: LessonProject, progress: Progress = None, start_at: str = "research") -> bool:
        for step in STEP_ORDER[STEP_ORDER.index(start_at):]:
            if not self.run_step(p, step, progress):
                return False
        return True

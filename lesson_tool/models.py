"""Data models for the lesson project. Everything is persisted as JSON."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal, Optional

from pydantic import BaseModel, Field


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


StepName = Literal["research", "generate", "qc_factual", "qc_instructional"]
StepState = Literal["pending", "running", "done", "failed"]
SourceKind = Literal["web", "wikipedia", "grounded", "book", "video"]
SectionType = Literal["hook", "concept", "example", "activity", "knowledge_check", "summary"]
Severity = Literal["high", "medium", "low"]


class StepStatus(BaseModel):
    state: StepState = "pending"
    error: Optional[str] = None
    warnings: list[str] = Field(default_factory=list)
    updated_at: Optional[str] = None


class Source(BaseModel):
    id: str  # S1, S2 ... (books B1.., videos V1..)
    kind: SourceKind
    title: str
    url: str = ""
    domain: str = ""
    excerpt: str = ""  # text the generator / QC can actually read
    tier: Literal["A", "B", "C", "D"] = "C"  # reliability tier (see research/reliability.py)
    authors: list[str] = Field(default_factory=list)
    year: Optional[str] = None
    channel: Optional[str] = None
    duration_sec: Optional[int] = None
    query: str = ""


class ResearchBundle(BaseModel):
    queries: dict[str, list[str]] = Field(default_factory=dict)
    key_subtopics: list[str] = Field(default_factory=list)
    sources: list[Source] = Field(default_factory=list)  # web / wikipedia / grounded
    books: list[Source] = Field(default_factory=list)
    videos: list[Source] = Field(default_factory=list)
    provider_errors: dict[str, str] = Field(default_factory=dict)
    created_at: str = Field(default_factory=now_iso)

    def by_id(self) -> dict[str, Source]:
        return {s.id: s for s in [*self.sources, *self.books, *self.videos]}


class SubObjective(BaseModel):
    id: str
    text: str


class Section(BaseModel):
    id: str
    type: SectionType
    title: str
    minutes: int
    content_md: str
    objectives: list[str] = Field(default_factory=list)


class VideoPick(BaseModel):
    source_id: str  # must reference a V* id from research
    why: str = ""
    watch_when: str = ""


class Lesson(BaseModel):
    title: str
    objective: str
    audience: str = ""
    duration_minutes: int = 45
    sub_objectives: list[SubObjective] = Field(default_factory=list)
    sections: list[Section] = Field(default_factory=list)
    videos: list[VideoPick] = Field(default_factory=list)
    further_reading: list[str] = Field(default_factory=list)  # B* ids

    def total_minutes(self) -> int:
        return sum(s.minutes for s in self.sections)


class QCIssue(BaseModel):
    id: str
    category: str
    severity: Severity
    section_id: Optional[str] = None
    description: str
    evidence: str = ""
    suggestion: str = ""
    origin: Literal["llm", "rule", "web"] = "llm"


class ClaimCheck(BaseModel):
    claim: str
    section_id: Optional[str] = None
    cited: list[str] = Field(default_factory=list)
    verdict: Literal["supported", "partially_supported", "unsupported", "contradicted", "not_checkable"]
    note: str = ""
    verified_by: list[str] = Field(default_factory=list)  # source ids or grounded URLs


class SourceAssessment(BaseModel):
    source_id: str
    tier: str
    relevance: Literal["high", "medium", "low"] = "medium"
    note: str = ""


class QCReport(BaseModel):
    layer: Literal["qc_factual", "qc_instructional"]
    lesson_version: int
    model: str
    score: int  # 0-100
    summary: str
    issues: list[QCIssue] = Field(default_factory=list)
    claims: list[ClaimCheck] = Field(default_factory=list)  # QC1 only
    sources: list[SourceAssessment] = Field(default_factory=list)  # QC1 only
    objective_coverage: list[dict] = Field(default_factory=list)  # QC2 only
    rubric: dict[str, int] = Field(default_factory=dict)  # QC2 only (criterion -> 1..5)
    created_at: str = Field(default_factory=now_iso)


class VersionInfo(BaseModel):
    version: int
    note: str
    created_at: str = Field(default_factory=now_iso)


class LessonProject(BaseModel):
    id: str
    title: str
    objective: str
    audience: str = ""
    created_at: str = Field(default_factory=now_iso)
    updated_at: str = Field(default_factory=now_iso)
    steps: dict[str, StepStatus] = Field(
        default_factory=lambda: {k: StepStatus() for k in ["research", "generate", "qc_factual", "qc_instructional"]}
    )
    research: Optional[ResearchBundle] = None
    lesson: Optional[Lesson] = None
    lesson_version: int = 0
    versions: list[VersionInfo] = Field(default_factory=list)
    qc_reports: dict[str, QCReport] = Field(default_factory=dict)
    applied_issue_ids: list[str] = Field(default_factory=list)

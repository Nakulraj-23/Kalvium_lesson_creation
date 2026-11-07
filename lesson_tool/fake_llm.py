"""Deterministic fake LLM used ONLY by the automated tests (LESSON_TOOL_LLM=fake).
It never produces real lesson content; it lets the pipeline, QC rules, storage and UI be
exercised offline without spending API quota."""
from __future__ import annotations

from .llm import BaseLLM, GroundedResult


class FakeLLM(BaseLLM):
    model = "fake-llm"
    fail_tasks: set[str] = set()  # tests can make specific tasks fail

    def generate_json(self, prompt, *, task, system="", temperature=0.3):
        if task in self.fail_tasks:
            from .llm import LLMError

            raise LLMError(f"simulated failure in {task}")
        if task == "research_plan":
            return {"key_subtopics": ["GET", "POST", "status codes"], "web_queries": ["http get post", "http status codes"],
                    "youtube_queries": ["http explained"], "book_queries": ["http definitive guide"]}
        if task == "generate_lesson":
            return {
                "sub_objectives": [{"id": "O1", "text": "Explain GET and POST"}, {"id": "O2", "text": "Distinguish 2xx/4xx/5xx"}],
                "sections": [
                    {"id": "s1", "type": "hook", "title": "Why HTTP?", "minutes": 3, "objectives": ["O1"], "content_md": "Every page load is a request."},
                    {"id": "s2", "type": "concept", "title": "GET vs POST", "minutes": 10, "objectives": ["O1"],
                     "content_md": "GET retrieves a representation and is safe [S1]. POST submits data for processing [S1]."},
                    {"id": "s3", "type": "concept", "title": "Status classes", "minutes": 8, "objectives": ["O2"],
                     "content_md": "2xx means success, 4xx client error, 5xx server error [S2]. Bogus cite [S99]."},
                    {"id": "s4", "type": "example", "title": "Worked example", "minutes": 7, "objectives": ["O1", "O2"],
                     "content_md": "```\nGET /users HTTP/1.1\n```\nSee https://invented-site.io/x for more."},
                    {"id": "s5", "type": "activity", "title": "Try curl", "minutes": 9, "objectives": ["O1", "O2"], "content_md": "Run curl -i https://example.com"},
                    {"id": "s6", "type": "knowledge_check", "title": "Quiz", "minutes": 6, "objectives": ["O1"],
                     "content_md": "1. Is GET safe?\n2. What is 404?\n3. What is 503?\n4. When use POST?\n\n**Answer key**: 1 yes..."},
                    {"id": "s7", "type": "summary", "title": "Summary", "minutes": 2, "objectives": ["O1", "O2"], "content_md": "Recap."},
                ],
                "videos": [{"source_id": "V1", "why": "visual overview", "watch_when": "after s3"}, {"source_id": "V99", "why": "bad id"}],
                "further_reading": ["B1", "B42"],
            }
        if task == "qc_factual":
            return {
                "claims": [
                    {"claim": "GET is safe", "section_id": "s2", "cited": ["S1"], "verdict": "supported", "note": "S1 says so"},
                    {"claim": "POST is idempotent", "section_id": "s2", "cited": [], "verdict": "unsupported", "note": "not in sources"},
                    {"claim": "5xx means server error", "section_id": "s3", "cited": ["S2"], "verdict": "supported", "note": ""},
                ],
                "sources": [{"source_id": "S1", "relevance": "high", "note": "official docs"}, {"source_id": "S2", "relevance": "high", "note": ""}],
                "issues": [{"category": "gap", "severity": "medium", "section_id": "s3", "description": "No examples of specific codes",
                            "suggestion": "Add 200, 201, 404, 500 examples"}],
                "summary": "Mostly accurate.",
            }
        if task == "qc_instructional":
            return {
                "objective_coverage": [{"component": "Explain GET/POST", "taught_in": ["s2"], "practised_in": ["s5"], "assessed_in": ["s6"], "coverage": "full"},
                                       {"component": "Distinguish status categories", "taught_in": ["s3"], "practised_in": [], "assessed_in": [], "coverage": "partial"}],
                "rubric": {"objective_alignment": 3, "clarity": 4, "structure_and_flow": 4, "examples_quality": 3, "practical_application": 4,
                           "assessment_alignment": 3, "engagement": 3, "time_feasibility": 4, "audience_fit": 4},
                "issues": [{"category": "assessment", "severity": "high", "section_id": "s6", "description": "Quiz doesn't ask to distinguish categories",
                            "suggestion": "Add scenario questions mapping responses to 2xx/4xx/5xx"}],
                "summary": "Solid structure, assessment gap.",
            }
        if task == "apply_fixes":
            return {"sections": [{"id": "s6", "type": "knowledge_check", "title": "Quiz", "minutes": 6, "objectives": ["O1", "O2"],
                                  "content_md": "1. Is GET safe?\n2. A server returns 503 - which category?\n\n**Answer key**: ..."}],
                    "minutes_changes": {}, "change_log": [{"issue_id": "I1", "change": "Added categorisation questions"}]}
        raise AssertionError(f"FakeLLM: unexpected task {task}")

    def generate_grounded(self, prompt, *, task):
        if task in self.fail_tasks:
            from .llm import LLMError

            raise LLMError(f"simulated failure in {task}")
        if task == "grounded_research":
            return GroundedResult(text="notes", sources=[{"title": "rfc-editor.org", "url": "https://www.rfc-editor.org/rfc/rfc9110"}],
                                  supports=[{"text": "GET is safe and idempotent.", "source_idx": [0]}])
        if task == "qc_grounded_verify":
            return GroundedResult(text="1 | FALSE | POST is not idempotent per RFC 9110.", sources=[{"title": "rfc", "url": "https://www.rfc-editor.org/rfc/rfc9110"}])
        raise AssertionError(task)

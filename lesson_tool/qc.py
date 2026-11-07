"""The two independent Quality-Control layers.

Each layer = deterministic rule checks (reproducible, cheap) + an LLM audit with its own prompt and
system role. The layers never see each other's reports, and they can run on a different model from
the generator (GEMINI_QC_MODEL) so the lesson isn't simply grading itself.

QC1  Research & factual accuracy
     rules : citation ids exist, no invented URLs, uncited factual sections, broken links,
             low-reliability-only sections
     LLM   : claim extraction + verdict against source excerpts, source relevance, gaps/inconsistencies
     extra : claims the excerpts don't support are re-checked with an independent Google-Search-grounded
             call, so "not in our sources" is separated from "actually wrong"
QC2  Instructional quality
     rules : 45-minute budget, reading time vs. allotted time, required lesson components,
             every sub-objective taught + assessed
     LLM   : independent objective decomposition & coverage map, 9-criterion rubric, issues
"""
from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Optional

import requests

from .generator import CITE_RE, URL_RE, format_lesson, lesson_metrics
from .llm import BaseLLM
from .models import ClaimCheck, Lesson, QCIssue, QCReport, ResearchBundle, SourceAssessment
from .prompts import QC1_AUDIT, QC1_GROUNDED_VERIFY, QC1_SYSTEM, QC2_AUDIT, QC2_SYSTEM, render
from .research.reliability import tier_for

SEV_COST = {"high": 12, "medium": 6, "low": 2}
LinkChecker = Callable[[list[str]], dict[str, bool]]


def default_link_checker(urls: list[str], timeout: int = 10) -> dict[str, bool]:
    def ok(u: str) -> bool:
        try:
            r = requests.head(u, allow_redirects=True, timeout=timeout, headers={"User-Agent": "Mozilla/5.0"})
            if r.status_code in (403, 405, 429) or r.status_code >= 500:  # many sites block HEAD/bots
                r = requests.get(u, allow_redirects=True, timeout=timeout, headers={"User-Agent": "Mozilla/5.0"}, stream=True)
            return r.status_code < 400 or r.status_code in (403, 429)
        except Exception:
            return False

    with ThreadPoolExecutor(max_workers=8) as ex:
        return dict(zip(urls, ex.map(ok, urls)))


def _norm_issue(raw: dict, origin: str = "llm") -> Optional[dict]:
    if not isinstance(raw, dict) or not raw.get("description"):
        return None
    sev = str(raw.get("severity", "medium")).lower()
    return {
        "category": str(raw.get("category", "other")),
        "severity": sev if sev in SEV_COST else "medium",
        "section_id": raw.get("section_id") or None,
        "description": str(raw["description"]),
        "evidence": str(raw.get("evidence", "") or ""),
        "suggestion": str(raw.get("suggestion", "") or ""),
        "origin": origin,
    }


def _number(issues: list[dict], prefix: str) -> list[QCIssue]:
    order = {"high": 0, "medium": 1, "low": 2}
    issues = sorted(issues, key=lambda i: order[i["severity"]])
    return [QCIssue(id=f"{prefix}{n}", **i) for n, i in enumerate(issues, 1)]


# ======================================================================= QC 1
def qc1_rule_checks(lesson: Lesson, bundle: ResearchBundle, link_checker: Optional[LinkChecker]) -> list[dict]:
    issues: list[dict] = []
    ids = bundle.by_id()
    known_urls = {s.url for s in ids.values()}
    for s in lesson.sections:
        cites = CITE_RE.findall(s.content_md)
        bad = sorted({c for c in cites if c not in ids})
        if bad:
            issues.append(dict(category="citation", severity="high", section_id=s.id,
                               description=f"Cites source id(s) {', '.join(bad)} that do not exist in the research bundle.",
                               evidence=f"section {s.id}", suggestion="Replace with a valid source id or remove the claim.", origin="rule"))
        for u in URL_RE.findall(s.content_md):
            if u.rstrip(".,") not in known_urls and not re.search(r"(example\.(com|org)|localhost|127\.0\.0\.1|httpbin\.org|jsonplaceholder)", u):
                issues.append(dict(category="citation", severity="medium", section_id=s.id,
                                   description=f"URL not taken from research sources (possibly invented): {u}",
                                   suggestion="Remove the URL or replace it with a researched source citation.", origin="rule"))
        if s.type in ("concept", "example") and not cites:
            issues.append(dict(category="unsupported_claim", severity="medium", section_id=s.id,
                               description=f"Section '{s.title}' makes factual statements but cites no sources.",
                               suggestion="Add [S#] citations to the key factual sentences.", origin="rule"))
        valid = [ids[c] for c in cites if c in ids]
        if valid and all(v.tier in ("C", "D") for v in valid) and s.type == "concept":
            issues.append(dict(category="source_quality", severity="low", section_id=s.id,
                               description=f"Section '{s.title}' relies only on lower-reliability sources (tier C/D).",
                               suggestion="Corroborate with an official/standards source (tier A/B) if available.", origin="rule"))
    if link_checker:
        cited_ids = {c for s in lesson.sections for c in CITE_RE.findall(s.content_md)}
        to_check = [ids[c].url for c in cited_ids if c in ids and ids[c].url]
        to_check += [ids[v.source_id].url for v in lesson.videos if v.source_id in ids]
        to_check += [ids[b].url for b in lesson.further_reading if b in ids and ids[b].url]
        try:
            results = link_checker(sorted(set(to_check)))
        except Exception:
            results = {}
        for url, ok in results.items():
            if not ok:
                issues.append(dict(category="source_quality", severity="medium", section_id=None,
                                   description=f"Reference link appears broken or unreachable: {url}",
                                   suggestion="Replace the link or drop the source.", origin="rule"))
    return issues


def _parse_grounded_lines(text: str) -> dict[int, tuple[str, str]]:
    out = {}
    for line in (text or "").splitlines():
        m = re.match(r"\s*\**\s*(\d+)\s*\**\s*[|:.)-]\s*\**\s*(TRUE|FALSE|PARTLY)\s*\**\s*[|:-]?\s*(.*)", line.strip(), re.I)
        if m:
            out[int(m.group(1))] = (m.group(2).upper(), m.group(3).strip())
    return out


def run_qc_factual(lesson: Lesson, version: int, bundle: ResearchBundle, llm: BaseLLM,
                   link_checker: Optional[LinkChecker] = default_link_checker, grounded_verify: bool = True) -> QCReport:
    issues = qc1_rule_checks(lesson, bundle, link_checker)

    data = llm.generate_json(
        render(QC1_AUDIT, title=lesson.title, objective=lesson.objective, lesson=format_lesson(lesson),
               sources="\n\n".join(f"[{s.id}] {s.title} ({s.url}) tier {s.tier}\n{s.excerpt[:llm.excerpt_chars]}" for s in bundle.sources[:llm.max_sources])),
        task="qc_factual", system=QC1_SYSTEM, temperature=0.1,
    )
    data = data if isinstance(data, dict) else {}

    claims: list[ClaimCheck] = []
    for c in data.get("claims", []) or []:
        if not isinstance(c, dict) or not c.get("claim"):
            continue
        v = c.get("verdict", "not_checkable")
        if v not in {"supported", "partially_supported", "unsupported", "contradicted", "not_checkable"}:
            v = "not_checkable"
        claims.append(ClaimCheck(claim=c["claim"], section_id=c.get("section_id"), cited=c.get("cited", []) or [],
                                 verdict=v, note=c.get("note", "") or "", verified_by=[x for x in c.get("cited", []) or []]))

    # independent web verification of the doubtful claims
    doubtful = [c for c in claims if c.verdict in ("unsupported", "contradicted", "partially_supported")][:15]
    if grounded_verify and doubtful:
        try:
            g = llm.generate_grounded(
                render(QC1_GROUNDED_VERIFY, claims="\n".join(f"{i}. {c.claim}" for i, c in enumerate(doubtful, 1))),
                task="qc_grounded_verify",
            )
            parsed = _parse_grounded_lines(g.text)
            urls = [s["url"] for s in g.sources][:5]
            for i, c in enumerate(doubtful, 1):
                if i not in parsed:
                    continue
                verdict, note = parsed[i]
                c.note = (c.note + f" | Web check: {verdict} - {note}").strip(" |")
                c.verified_by += ["google-search"] + urls[:2]
                if verdict == "FALSE":
                    issues.append(dict(category="factual_error", severity="high", section_id=c.section_id,
                                       description=f"Claim judged FALSE by independent web verification: \"{c.claim}\"",
                                       evidence=note, suggestion="Correct the statement (see evidence) and cite an authoritative source.", origin="web"))
                elif verdict == "PARTLY":
                    issues.append(dict(category="misleading", severity="medium", section_id=c.section_id,
                                       description=f"Claim only partly correct per web verification: \"{c.claim}\"",
                                       evidence=note, suggestion="Qualify or correct the statement.", origin="web"))
                elif verdict == "TRUE" and c.verdict == "unsupported":
                    issues.append(dict(category="citation", severity="low", section_id=c.section_id,
                                       description=f"Claim is true but not backed by the cited sources: \"{c.claim}\"",
                                       evidence=note, suggestion="Add a citation to a source that states this.", origin="web"))
        except Exception as e:
            issues.append(dict(category="process", severity="low", section_id=None,
                               description=f"Independent web verification step failed ({str(e)[:150]}); verdicts rely on source excerpts only.",
                               suggestion="Re-run QC1 later.", origin="rule"))

    for raw in data.get("issues", []) or []:
        n = _norm_issue(raw)
        if n:
            issues.append(n)

    ids = bundle.by_id()
    assessments = []
    for sa in data.get("sources", []) or []:
        if isinstance(sa, dict) and sa.get("source_id") in ids:
            rel = sa.get("relevance", "medium")
            assessments.append(SourceAssessment(source_id=sa["source_id"], tier=ids[sa["source_id"]].tier,
                                                relevance=rel if rel in ("high", "medium", "low") else "medium", note=sa.get("note", "")))

    checkable = [c for c in claims if c.verdict != "not_checkable"]
    support = (sum(1 for c in checkable if c.verdict == "supported") + 0.5 * sum(1 for c in checkable if c.verdict == "partially_supported"))
    support_rate = support / len(checkable) if checkable else 0.5
    deductions = sum(SEV_COST[i["severity"]] for i in issues)
    score = round(0.6 * support_rate * 100 + 0.4 * max(0, 100 - deductions))

    return QCReport(layer="qc_factual", lesson_version=version, model=llm.model, score=score,
                    summary=str(data.get("summary", "")) + f" (Claims checked: {len(claims)}; supported by sources: {support_rate:.0%}.)",
                    issues=_number(issues, "F"), claims=claims, sources=assessments)


# ======================================================================= QC 2
def qc2_rule_checks(lesson: Lesson) -> tuple[list[dict], dict]:
    m = lesson_metrics(lesson)
    issues: list[dict] = []
    total, target = m["total_minutes"], lesson.duration_minutes
    if total != target:
        diff = total - target
        issues.append(dict(category="timing", severity="high" if abs(diff) > 3 else "medium", section_id=None,
                           description=f"Section times add up to {total} min, target is {target} min ({'+' if diff > 0 else ''}{diff}).",
                           suggestion="Rebalance section minutes so the lesson fits exactly in the time budget.", origin="rule"))
    for s in m["sections"]:
        if s["type"] in ("hook", "concept", "example", "summary") and s["reading_minutes"] > s["minutes"] * 1.3 + 0.5:
            issues.append(dict(category="timing", severity="medium", section_id=s["id"],
                               description=f"Section {s['id']} has ~{s['words']} words (~{s['reading_minutes']} min to read) but only {s['minutes']} min allotted.",
                               suggestion="Trim the text or allot more time.", origin="rule"))
    types = set(m["section_types"])
    for need, sev in (("activity", "high"), ("knowledge_check", "high"), ("hook", "low"), ("summary", "medium"), ("example", "medium")):
        if need not in types:
            issues.append(dict(category="structure", severity=sev, section_id=None,
                               description=f"Lesson has no '{need}' section.",
                               suggestion=f"Add a {need.replace('_', ' ')} section.", origin="rule"))
    for o in lesson.sub_objectives:
        serving = [s for s in lesson.sections if o.id in s.objectives]
        if not serving:
            issues.append(dict(category="alignment", severity="high", section_id=None,
                               description=f"Sub-objective {o.id} ('{o.text}') is not addressed by any section.",
                               suggestion="Add teaching and practice for this sub-objective.", origin="rule"))
        elif not any(s.type == "knowledge_check" for s in serving):
            issues.append(dict(category="assessment", severity="medium", section_id=None,
                               description=f"Sub-objective {o.id} ('{o.text}') is never assessed in the knowledge check.",
                               suggestion="Add at least one knowledge-check question for it.", origin="rule"))
    kc = next((s for s in lesson.sections if s.type == "knowledge_check"), None)
    if kc:
        body = re.split(r"answer key", kc.content_md, flags=re.I)[0]
        q = len(re.findall(r"\?", body))
        m["knowledge_check_questions"] = q
        if q < 4:
            issues.append(dict(category="assessment", severity="low", section_id=kc.id,
                               description=f"Knowledge check seems to contain only {q} question(s).",
                               suggestion="Use 5-6 questions covering every sub-objective.", origin="rule"))
        if not re.search(r"answer", kc.content_md, re.I):
            issues.append(dict(category="assessment", severity="medium", section_id=kc.id,
                               description="Knowledge check has no answer key.",
                               suggestion="Add an answer key with brief explanations for self-learners.", origin="rule"))
    return issues, m


def run_qc_instructional(lesson: Lesson, version: int, llm: BaseLLM) -> QCReport:
    issues, metrics = qc2_rule_checks(lesson)
    metrics_txt = "\n".join(
        [f"total minutes: {metrics['total_minutes']} (target {metrics['target_minutes']})",
         f"total words: {metrics['total_words']} (~{metrics['total_reading_minutes']} min reading at 180 wpm)",
         f"knowledge-check questions detected: {metrics.get('knowledge_check_questions', 'n/a')}",
         f"supplementary videos: {metrics['videos']}"]
        + [f"  {s['id']} {s['type']}: {s['minutes']} min allotted, {s['words']} words (~{s['reading_minutes']} min)" for s in metrics["sections"]]
    )
    data = llm.generate_json(
        render(QC2_AUDIT, title=lesson.title, objective=lesson.objective, minutes=lesson.duration_minutes,
               audience=lesson.audience or "beginner / undergraduate", metrics=metrics_txt, lesson=format_lesson(lesson)),
        task="qc_instructional", system=QC2_SYSTEM, temperature=0.2,
    )
    data = data if isinstance(data, dict) else {}
    for raw in data.get("issues", []) or []:
        n = _norm_issue(raw)
        if n:
            issues.append(n)
    rubric = {}
    for k, v in (data.get("rubric") or {}).items():
        try:
            rubric[str(k)] = max(1, min(5, int(v)))
        except (TypeError, ValueError):
            continue
    coverage = [c for c in data.get("objective_coverage", []) or [] if isinstance(c, dict)]
    for c in coverage:
        if c.get("coverage") == "missing":
            issues.append(dict(category="alignment", severity="high", section_id=None,
                               description=f"Objective component not covered: {c.get('component')}",
                               suggestion="Teach, practise and assess this component.", origin="llm"))
    rubric_pct = (sum(rubric.values()) / (5 * len(rubric)) * 100) if rubric else 50
    deductions = sum(SEV_COST[i["severity"]] for i in issues)
    score = round(0.7 * rubric_pct + 0.3 * max(0, 100 - deductions))
    return QCReport(layer="qc_instructional", lesson_version=version, model=llm.model, score=score,
                    summary=str(data.get("summary", "")), issues=_number(issues, "I"),
                    objective_coverage=coverage, rubric=rubric)

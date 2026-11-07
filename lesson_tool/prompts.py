"""All prompts in one place so they can be reviewed and tuned.

Templates use $placeholders (string.Template) so JSON examples don't need brace escaping.
"""
from string import Template


def render(tpl: str, **kw) -> str:
    return Template(tpl).safe_substitute(**kw)


# ------------------------------------------------------------------ research
RESEARCH_PLAN = """You are planning research for a 45-minute lesson.
Lesson title: $title
Learning objective: $objective
Audience: $audience

Return JSON:
{
  "key_subtopics": ["the 4-8 concepts the objective requires"],
  "web_queries": ["3-4 precise search queries; prefer ones that surface official docs/standards (e.g. MDN, RFCs, vendor docs, .edu)"],
  "youtube_queries": ["2 queries for short explainer videos"],
  "book_queries": ["2 queries for textbooks/reference books on the topic"]
}"""

GROUNDED_RESEARCH = """Research the following topic using Google Search and write concise, factual teaching notes.
Topic: $title
Learning objective: $objective

Cover: precise definitions, how it works, key distinctions the objective requires, 2-3 concrete examples,
common misconceptions, and any version/standard numbers that matter. Prefer authoritative sources
(standards bodies, official documentation, universities). Plain text bullet points, no more than 400 words."""

# ------------------------------------------------------------------ generation
GENERATE_SYSTEM = """You are an expert instructional designer and subject-matter expert. You write accurate,
engaging lessons grounded ONLY in the research sources provided. You never invent URLs, statistics,
quotes or source ids."""

GENERATE_LESSON = """Create a complete lesson.

LESSON TITLE: $title
LEARNING OBJECTIVE: $objective
AUDIENCE: $audience
TOTAL TIME: exactly $minutes minutes (self-study or instructor-led), INCLUDING explanations, examples,
activities and the knowledge check. Supplementary videos are optional and NOT counted in the 45 minutes.

KEY SUBTOPICS FROM RESEARCH: $subtopics

RESEARCH SOURCES (cite them inline as [S1], [S2] ... right after the sentence they support):
$sources

BOOKS FOUND (may be recommended as further reading by id):
$books

YOUTUBE CANDIDATES (choose 2-3 by id; prefer short, clear, reputable channels, directly on-objective):
$videos

REQUIREMENTS
1. Break the objective into 2-4 measurable sub-objectives (O1, O2, ...). Every sub-objective must be taught,
   practised and assessed.
2. Sections, in this order, with realistic minutes that sum to exactly $minutes:
   - hook (2-4 min): a relatable scenario/question that motivates the topic
   - 2-4 concept sections: clear explanations, analogies, tables/diagrams in markdown where useful
   - example section(s): concrete, realistic worked examples (code/commands/requests where relevant)
   - activity (8-12 min): a hands-on practical task with step-by-step instructions and expected outcome
   - knowledge_check (5-8 min): 5-6 questions (mix of multiple-choice and scenario-based) aligned to the
     sub-objectives, followed by an "Answer key" with a one-line explanation for each
   - summary (2-3 min): key takeaways + common mistakes to avoid
   Budget reading at ~180 words per minute; do not write more text than the minutes allow.
3. Factual sentences must be supported by a cited source id from the list above. If the sources don't
   support something, either leave it out or state it as general guidance without a number. Never cite an
   id that is not listed. Do NOT put any URLs in content_md.
4. Write in clear, friendly, second-person language appropriate to the audience. Use markdown
   (headings level 3+, lists, tables, code blocks).
5. Each section lists the sub-objective ids it serves.

Return JSON only:
{
  "sub_objectives": [{"id": "O1", "text": "..."}],
  "sections": [
    {"id": "s1", "type": "hook|concept|example|activity|knowledge_check|summary", "title": "...",
     "minutes": 3, "objectives": ["O1"], "content_md": "..."}
  ],
  "videos": [{"source_id": "V1", "why": "what it adds", "watch_when": "e.g. after section s3"}],
  "further_reading": ["B1"]
}"""

# ------------------------------------------------------------------ QC layer 1
QC1_SYSTEM = """You are an independent fact-checker and research auditor. You did not write this lesson.
Be skeptical and precise. Judge claims ONLY against the evidence you are given unless told otherwise."""

QC1_AUDIT = """Audit the lesson below for RESEARCH QUALITY and FACTUAL ACCURACY.

LESSON TITLE: $title
LEARNING OBJECTIVE: $objective

LESSON (sections with ids; inline [S#] are citations):
$lesson

SOURCE EXCERPTS (the evidence):
$sources

Tasks:
A. Extract every checkable factual claim (definitions, numbers, status codes, behaviours, rules, dates) -
   up to 30, prioritising the ones most important to the objective. For each give a verdict judged
   against the CITED source excerpts (or any listed excerpt if uncited):
   supported | partially_supported | unsupported | contradicted | not_checkable.
   "unsupported" = no excerpt backs it (it may still be true). "contradicted" = an excerpt says otherwise.
   Also flag claims that are technically true but misleading or oversimplified (verdict partially_supported).
B. Assess each source: relevance to the objective (high/medium/low) and a short note on reliability
   (official/standard, reputable reference, blog, outdated, commercial bias...).
C. Find gaps and inconsistencies: important facts the objective needs that are missing or wrong,
   contradictions between sections, wrong citations (cited source does not discuss the claim),
   outdated information.

Return JSON only:
{
  "claims": [{"claim": "...", "section_id": "s2", "cited": ["S1"], "verdict": "supported", "note": "why"}],
  "sources": [{"source_id": "S1", "relevance": "high", "note": "..."}],
  "issues": [{"category": "factual_error|unsupported_claim|misleading|citation|source_quality|gap|inconsistency|outdated",
              "severity": "high|medium|low", "section_id": "s2", "description": "...",
              "evidence": "quote or source id", "suggestion": "concrete fix"}],
  "summary": "2-3 sentence overall assessment"
}"""

QC1_GROUNDED_VERIFY = """Independently verify each numbered claim using Google Search. Prefer standards bodies,
official documentation and university sources.

$claims

For EACH claim, write one line in exactly this format:
<number> | <TRUE|FALSE|PARTLY> | <one-sentence correction or confirmation>"""

# ------------------------------------------------------------------ QC layer 2
QC2_SYSTEM = """You are a senior instructional designer reviewing a colleague's lesson. You did not write it.
Use evidence-based instructional design (constructive alignment, Bloom's taxonomy, worked examples,
retrieval practice, cognitive load). Be specific: point to section ids and quote the problem."""

QC2_AUDIT = """Review this lesson for INSTRUCTIONAL QUALITY.

LESSON TITLE: $title
LEARNING OBJECTIVE (as given by the instructor): $objective
TARGET DURATION: $minutes minutes total
AUDIENCE: $audience

AUTOMATED MEASUREMENTS (computed by code, trust these numbers):
$metrics

LESSON:
$lesson

Tasks:
1. Decompose the learning objective into its required components YOURSELF (do not just reuse the lesson's
   own sub-objectives). For each component state where it is taught, practised and assessed
   (section ids) and rate coverage: full | partial | missing.
2. Score each rubric criterion 1-5: objective_alignment, clarity, structure_and_flow, examples_quality,
   practical_application, assessment_alignment, engagement, time_feasibility, audience_fit.
3. List concrete issues: misalignment, verbs not matched (e.g. objective says "distinguish" but nothing asks
   learners to distinguish), unclear or jargon-heavy explanations, missing/weak examples, missing practical
   application, quiz questions that test something not taught or have ambiguous answers, poor sequencing,
   unrealistic timing.

Return JSON only:
{
  "objective_coverage": [{"component": "...", "taught_in": ["s2"], "practised_in": ["s5"], "assessed_in": ["s6"], "coverage": "full"}],
  "rubric": {"objective_alignment": 4, "clarity": 4, "structure_and_flow": 4, "examples_quality": 4,
             "practical_application": 4, "assessment_alignment": 4, "engagement": 4, "time_feasibility": 4, "audience_fit": 4},
  "issues": [{"category": "alignment|clarity|structure|examples|practical_application|assessment|timing|engagement|audience",
              "severity": "high|medium|low", "section_id": "s3", "description": "...", "evidence": "...",
              "suggestion": "concrete, actionable fix"}],
  "summary": "2-3 sentence overall assessment"
}"""

# ------------------------------------------------------------------ apply QC recommendations
APPLY_SYSTEM = GENERATE_SYSTEM

APPLY_FIXES = """Revise the lesson to resolve the QC issues listed. Change only what is needed.

LESSON TITLE: $title
LEARNING OBJECTIVE: $objective
TOTAL TIME must stay exactly $minutes minutes (adjust 'minutes' of sections if you add/remove material).

CURRENT SECTIONS (JSON):
$sections

ISSUES TO FIX:
$issues

AVAILABLE SOURCES (cite only these ids; never add URLs):
$sources

Rules: keep section ids stable; you may add a new section only if an issue requires it (give it a new id
like "s9"); keep [S#] citations on factual sentences; if a claim cannot be supported by the sources, remove
or soften it rather than inventing support.

Return JSON only:
{
  "sections": [ only the sections you changed or added, full objects:
     {"id": "s2", "type": "concept", "title": "...", "minutes": 8, "objectives": ["O1"], "content_md": "..."} ],
  "minutes_changes": {"s5": 9},
  "change_log": [{"issue_id": "F3", "change": "what you changed"}]
}"""

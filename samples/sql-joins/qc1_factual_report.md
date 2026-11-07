# QC Layer 1 - Research & Factual Accuracy - Audit Report

- **Score:** 72/100
- **Lesson version audited:** v3
- **Reviewer model:** openai/gpt-oss-120b
- **Date:** 2026-11-07T10:33:10+00:00

## Summary

The lesson accurately defines INNER, LEFT, and FULL OUTER joins and correctly cites authoritative PostgreSQL and Oracle sources for most claims. However, several statements (e.g., MySQL lack of FULL OUTER JOIN, optimizer behavior) lack supporting citations, and a few outdated sources are referenced. Adding up‑to‑date citations for MySQL behavior and optimizer details, and addressing minor gaps such as RIGHT JOIN explanation, would improve factual robustness. (Claims checked: 14; supported by sources: 75%.)

## Issues (7)

### F1 - [HIGH] gap (section s5; found by AI audit)

**Problem:** The lesson does not mention that RIGHT JOIN is equivalent to LEFT JOIN with table order swapped, which is useful for the objective.  
**Suggested improvement:** Include a concise definition of RIGHT JOIN and its equivalence to LEFT JOIN.

### F2 - [MEDIUM] source_quality (whole lesson; found by rule check)

**Problem:** Reference link appears broken or unreachable: https://openlibrary.org/works/OL9559525W  
**Suggested improvement:** Replace the link or drop the source.

### F3 - [MEDIUM] unsupported_claim (section s7; found by AI audit)

**Problem:** Claims about MySQL lacking FULL OUTER JOIN and its emulation have no supporting citations.  
**Suggested improvement:** Add citations to MySQL documentation or reputable source confirming lack of native support and the UNION workaround.

### F4 - [LOW] process (whole lesson; found by rule check)

**Problem:** Independent web verification step failed (Gemini rate limit / quota exceeded (HTTP 429). Wait a minute and press Retry.); verdicts rely on source excerpts only.  
**Suggested improvement:** Re-run QC1 later.

### F5 - [LOW] citation (section s5; found by AI audit)

**Problem:** The statement that INNER JOINs allow the optimizer to reorder joins cites S8 (Oracle) but the lesson is about PostgreSQL; better to cite PostgreSQL optimizer docs.  
**Evidence:** S8  
**Suggested improvement:** Replace or supplement with PostgreSQL optimizer documentation (e.g., S1 or another PostgreSQL source).

### F6 - [LOW] misleading (section s2; found by AI audit)

**Problem:** The claim that nesting does not affect INNER JOIN results is technically true but not explicitly backed; could be clarified.  
**Evidence:** S6  
**Suggested improvement:** Add a brief note or citation confirming that INNER JOIN is associative.

### F7 - [LOW] outdated (section s2; found by AI audit)

**Problem:** Citation S4 refers to PostgreSQL 7.1 documentation, which is obsolete.  
**Evidence:** S4  
**Suggested improvement:** Remove or replace with current PostgreSQL version documentation.

## Claim verification

| # | Claim | Section | Cited | Verdict | Notes |
|---|---|---|---|---|---|
| 1 | An INNER JOIN returns rows where the join condition is true for both tables. | s2 | S1 | supported | PostgreSQL docs describe INNER JOIN as combining rows that satisfy the expression. |
| 2 | When several joins are chained they nest left‑to‑right, and parentheses can change the nesting. | s2 | S6 | supported | S6 states that in the absence of parentheses, JOIN clauses nest left‑to‑right. |
| 3 | For INNER JOINs the nesting doesn't change the result, but for OUTER JOINs it can. | s2 | S6 | partially_supported | S6 confirms nesting can affect logical order; it does not explicitly say INNER JOIN results are invariant, but that is generally true. |
| 4 | A LEFT OUTER JOIN returns all rows from the left table and matching rows from the right; non‑matching right rows become NULL. | s3 | S7 | supported | Oracle docs (S7) define LEFT OUTER JOIN as preserving unmatched rows from the left table with NULLs for the right. |
| 5 | NULL never equals another NULL, so a left join can produce NULL values that must be considered in later calculations. | s3 | S9 | supported | Wikipedia (S9) notes that NULL never matches another NULL. |
| 6 | A FULL OUTER JOIN returns the union of a left and a right outer join: all rows from both tables, with NULL filling gaps where no match exists. | s4 | S1 | supported | PostgreSQL docs (S1) describe FULL OUTER JOIN as returning all rows from both sides. |
| 7 | PostgreSQL supports FULL OUTER JOIN. | s4 | S1 | supported | S1 is PostgreSQL documentation that includes FULL OUTER JOIN. |
| 8 | With INNER JOINs the database's query planner is free to reorder them for speed. | s5 | S8 | supported | Oracle docs (S8) explain the optimizer can determine join order for performance. |
| 9 | Parentheses can change the logical order and affect performance. | s5 | S6, S8 | supported | Both S6 (nesting) and S8 (optimizer) support this. |
| 10 | FULL OUTER JOIN is NOT supported natively in MySQL. | s7 |  | unsupported | No source provided; while true in practice, the claim is not backed by the given excerpts. |
| 11 | FULL OUTER JOIN can be emulated in MySQL by UNION of LEFT and RIGHT joins. | s7 |  | unsupported | No citation; claim is common knowledge but not sourced. |
| 12 | After a LEFT JOIN, a condition on the right table in WHERE discards NULL rows and turns it into an INNER JOIN. | s8 |  | unsupported | No source cited; statement is accurate but not verified against provided excerpts. |
| 13 | NULL never matches another NULL; test for it explicitly. | s8 | S9 | supported | S9 explicitly states NULL never matches another NULL. |
| 14 | Running SELECT * FROM students JOIN enrollments ON students.id = enrollments.student_id returns fewer rows because INNER JOIN discards non‑matching rows. | s1 | S1 | supported | S1 defines INNER JOIN behavior that explains missing rows. |

## Source assessment

| Source | Tier | Relevance | Note |
|---|---|---|---|
| S1 PostgreSQL: Documentation: 18: 2.6. Joins Between Tables (postgresql.org) | A | high | Official PostgreSQL documentation; authoritative for join definitions. |
| S6 PostgreSQL: Documentation: 18: 7.2. Table Expressions (postgresql.org) | A | high | Official PostgreSQL docs on table expressions and join nesting. |
| S7 LEFT OUTER JOIN operation - Oracle (docs.oracle.com) | A | high | Oracle official documentation on LEFT OUTER JOIN semantics. |
| S8 Joins - docs.oracle.com (docs.oracle.com) | A | medium | Oracle docs on optimizer join order; reliable but not specific to PostgreSQL. |
| S9 Join (SQL) - Wikipedia (wikipedia.org) | B | medium | Wikipedia entry on SQL joins; generally accurate but secondary source. |
| S2 Documentation - PostgreSQL (postgresql.org) | A | low | Generic PostgreSQL documentation index; does not contain substantive content for claims. |
| S3 PostgreSQL 18.6 Documentation (postgresql.org) | A | low | Copyright notice page; no factual content. |
| S4 PostgreSQL: Documentation: 7.1: Joins Between Tables (postgresql.org) | A | low | Very old PostgreSQL version; not used for current claims. |
| S5 PostgreSQL: Documentation: 18: Chapter 2. The SQL Language (postgresql.org) | A | low | Generic documentation page; no specific claim support. |
| S10 NoSQL - Wikipedia (wikipedia.org) | B | medium | Irrelevant to SQL joins; about NoSQL. |

_Tier key: A = standards/official docs/.gov/.edu, B = reputable reference, C = general web/blog, D = user-generated._

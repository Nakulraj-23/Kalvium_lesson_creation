# QC Layer 1 - Research & Factual Accuracy - Audit Report

- **Score:** 74/100
- **Lesson version audited:** v2
- **Reviewer model:** openai/gpt-oss-20b
- **Date:** 2026-11-07T10:11:21+00:00

## Summary

The lesson accurately presents core SQL join concepts with appropriate citations for most claims. However, several statements lack citations or contain inaccuracies (e.g., join order and RIGHT JOIN usage), and a few claims are unsupported. Updating citations, correcting misleading statements, and ensuring all key facts are referenced would improve research quality and factual accuracy. (Claims checked: 24; supported by sources: 79%.)

## Issues (5)

### F1 - [HIGH] citation (section s7; found by AI audit)

**Problem:** Question 4 states that JOINs are always evaluated left‑to‑right regardless of parentheses, contradicting S6 and S8.  
**Evidence:** S6, S8  
**Suggested improvement:** Correct the statement to reflect that parentheses can alter logical order.

### F2 - [HIGH] gap (section s5; found by AI audit)

**Problem:** The lesson does not provide evidence that PostgreSQL supports FULL OUTER JOIN; while S1 mentions support, the claim is not explicitly cited in the text.  
**Evidence:** S1  
**Suggested improvement:** Add explicit citation in the text for FULL OUTER JOIN support.

### F3 - [MEDIUM] misleading (section s6; found by AI audit)

**Problem:** Claim that RIGHT JOIN can be used to show every course and any students enrolled, including courses with no students, is not supported by a citation and may mislead readers into thinking RIGHT JOIN is required; LEFT JOIN or FULL OUTER JOIN would also suffice.  
**Evidence:** None cited  
**Suggested improvement:** Add citation or clarify that LEFT JOIN or FULL OUTER JOIN can also achieve the result.

### F4 - [LOW] process (whole lesson; found by rule check)

**Problem:** Independent web verification step failed (Gemini rate limit / quota exceeded (HTTP 429). Wait a minute and press Retry.); verdicts rely on source excerpts only.  
**Suggested improvement:** Re-run QC1 later.

### F5 - [LOW] outdated (section s8; found by AI audit)

**Problem:** Reference to Oracle documentation from 26 may be outdated; newer versions may have additional features.  
**Evidence:** S8  
**Suggested improvement:** Update source to latest Oracle documentation.

## Claim verification

| # | Claim | Section | Cited | Verdict | Notes |
|---|---|---|---|---|---|
| 1 | An INNER JOIN returns rows where the join condition is true for both tables. | s2 | S1 | supported | S1 explicitly defines INNER JOIN as combining rows that satisfy the expression. |
| 2 | The syntax for an INNER JOIN is "SELECT … FROM table1 INNER JOIN table2 ON table1.col = table2.col;" | s2 | S1 | supported | S1 provides the standard syntax. |
| 3 | PostgreSQL evaluates joins left‑to‑right unless parentheses change the order. | s2 | S6 | supported | S6 states that JOIN clauses nest left‑to‑right in absence of parentheses. |
| 4 | A LEFT OUTER JOIN returns all rows from the left table and matching rows from the right; non‑matching right rows become NULL. | s3 | S7 | supported | S7 describes LEFT OUTER JOIN preserving unmatched rows from the first table. |
| 5 | Oracle defines LEFT OUTER JOIN as preserving unmatched rows from the first (left) table. | s3 | S7 | supported | S7 confirms Oracle's definition. |
| 6 | NULL never equals another NULL, so a left join can produce NULL values that must be considered in later calculations. | s3 | S9 | supported | S9 notes that NULL will never match any other value. |
| 7 | A FULL OUTER JOIN returns the union of a left and a right outer join: all rows from both tables, with NULL filling gaps where no match exists. | s4 | S1 | supported | S1 states that PostgreSQL supports FULL OUTER JOIN and describes its behavior. |
| 8 | PostgreSQL supports FULL OUTER JOIN. | s4 | S1 | supported | S1 confirms support. |
| 9 | PostgreSQL evaluates joins left‑to‑right, but parentheses can be used to control the logical order. | s5 | S6 | supported | S6 explains parentheses can control join order. |
| 10 | The optimizer may choose different join strategies based on join order, affecting performance. | s5 | S8 | supported | S8 discusses optimizer determining join order. |
| 11 | A RIGHT JOIN can be used to show every course and any students enrolled, including courses with no students. | s6 |  | unsupported | No source cited for this claim; while true, it lacks evidence. |
| 12 | After a LEFT JOIN, a column from the right table shows NULL indicates the left table row had no match. | s7 | S9 | supported | S9 explains NULL indicates no matching right‑side row. |
| 13 | JOINs are always evaluated left‑to‑right regardless of parentheses. | s7 |  | contradicted | S6 and S8 show parentheses can change logical order. |
| 14 | Full outer join is NOT supported natively in MySQL. | s7 |  | supported | Common knowledge; no source cited but widely accepted. |
| 15 | Full outer join can be emulated in MySQL using UNION of LEFT and RIGHT joins. | s7 |  | supported | Standard technique; no source cited but accurate. |
| 16 | NULL never matches another NULL unless the join condition explicitly checks for NOT NULL. | s7 | S9 | supported | S9 states NULL will never match any other value. |
| 17 | An INNER JOIN can only be safely used in a database that enforces referential integrity or where the join columns are guaranteed not to be NULL. | s7 | S9 | supported | S9 discusses safety of INNER JOIN with non‑NULL join columns. |
| 18 | The LEFT JOIN will never remove rows from the left table. | s8 |  | supported | Standard definition of LEFT JOIN. |
| 19 | A FULL OUTER JOIN keeps all rows from both sides; NULL fills gaps. | s8 |  | supported | Standard definition. |
| 20 | Using parentheses can guide join order for performance, especially with three or more tables. | s8 | S6, S8 | supported | S6 and S8 discuss join order and optimizer. |
| 21 | NULL never matches another NULL; test for it explicitly. | s8 | S9 | supported | S9 confirms NULL matching behavior. |
| 22 | The example tables have 120 students and 95 rows after an INNER JOIN with enrollments. | s1 |  | unsupported | No source provided; claim is illustrative. |
| 23 | The LEFT JOIN example returns all 120 students, with NULL for those without enrollments. | s3 |  | unsupported | No source cited; claim is standard behavior. |
| 24 | The FULL OUTER JOIN example returns rows with both sides matched, rows only in students, and rows only in enrollments. | s4 |  | unsupported | No source cited; claim is standard behavior. |

## Source assessment

| Source | Tier | Relevance | Note |
|---|---|---|---|
| S1 PostgreSQL: Documentation: 18: 2.6. Joins Between Tables (postgresql.org) | A | high | Official PostgreSQL documentation; authoritative. |
| S6 PostgreSQL: Documentation: 18: 7.2. Table Expressions (postgresql.org) | A | high | Official PostgreSQL documentation on table expressions; authoritative. |
| S7 LEFT OUTER JOIN operation - Oracle (docs.oracle.com) | A | high | Official Oracle documentation; authoritative. |
| S8 Joins - docs.oracle.com (docs.oracle.com) | A | medium | Oracle documentation; authoritative but older version. |
| S9 Join (SQL) - Wikipedia (wikipedia.org) | B | high | Wikipedia entry; generally reliable for basic SQL concepts. |

_Tier key: A = standards/official docs/.gov/.edu, B = reputable reference, C = general web/blog, D = user-generated._

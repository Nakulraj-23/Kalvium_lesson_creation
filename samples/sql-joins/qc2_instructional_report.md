# QC Layer 2 - Instructional Quality - Audit Report

- **Score:** 81/100
- **Lesson version audited:** v3
- **Reviewer model:** openai/gpt-oss-120b
- **Date:** 2026-11-07T10:33:26+00:00

## Summary

The lesson aligns well with its learning objective, offering clear explanations, relevant examples, and appropriate assessments. Minor gaps include insufficient coverage of RIGHT JOIN, a need for richer NULL‑handling examples, and slight timing overruns in the hands‑on activity. Addressing these will strengthen alignment and learner experience.

## Rubric (1-5)

| Criterion | Score |
|---|---|
| objective alignment | 4 |
| clarity | 4 |
| structure and flow | 4 |
| examples quality | 4 |
| practical application | 4 |
| assessment alignment | 4 |
| engagement | 4 |
| time feasibility | 4 |
| audience fit | 4 |

## Objective coverage

| Component | Taught | Practised | Assessed | Coverage |
|---|---|---|---|---|
| Differentiate INNER JOIN, LEFT JOIN, and FULL OUTER JOIN semantics and results | s2, s3, s4 | s5, s6 | s7 | full |
| Select the appropriate join type for a given query scenario | s5 | s6 | s7 | full |
| Explain how NULL values and join order affect results and performance | s3, s4, s5 | s6 | s7 | partial |

## Issues (4)

### I1 - [MEDIUM] clarity (section s3; found by AI audit)

**Problem:** The explanation of NULL handling is brief and uses jargon (“NULL never equals another NULL”) without a concrete example of how it impacts a query condition.  
**Evidence:** "NULL never equals another NULL, so a left join can produce `NULL` values that must be considered in later calculations"  
**Suggested improvement:** Add a short worked example showing a LEFT JOIN with a WHERE clause that unintentionally filters out NULL rows, and demonstrate moving the condition to the ON clause.

### I2 - [MEDIUM] practical_application (section s6; found by AI audit)

**Problem:** Task 2 asks learners to use RIGHT JOIN or FULL OUTER JOIN, but the lesson never introduced RIGHT JOIN explicitly, leaving a gap in knowledge.  
**Evidence:** Lesson sections cover INNER, LEFT, and FULL OUTER joins; RIGHT JOIN is only mentioned in the activity prompt.  
**Suggested improvement:** Either add a brief subsection on RIGHT JOIN in s3/s4 or replace the task with a FULL OUTER JOIN only.

### I3 - [LOW] assessment (section s7; found by AI audit)

**Problem:** Question 4 about join order includes a partially incorrect statement: “Parentheses can change the logical order and affect performance.” While true for OUTER joins, for INNER joins order does not affect result correctness, which may confuse learners.  
**Evidence:** Quiz option B claims parentheses affect performance, but the lesson states INNER JOIN order never changes result.  
**Suggested improvement:** Re‑phrase the question to focus on OUTER joins or add a clarifying note that order matters only for OUTER joins.

### I4 - [LOW] timing (section s6; found by AI audit)

**Problem:** The activity allocates 9 minutes for three tasks, each requiring script setup, query writing, and explanation, which may be optimistic for undergraduate novices.  
**Evidence:** Task breakdown: 2 min setup + 3 min Task 1 + 3 min Task 2 + 2 min Task 3 = 10 min (exceeds allocated 9 min).  
**Suggested improvement:** Extend the activity to 12 minutes or reduce one task’s time allocation.

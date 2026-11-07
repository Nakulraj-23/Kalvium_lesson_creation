# QC Layer 2 - Instructional Quality - Audit Report

- **Score:** 73/100
- **Lesson version audited:** v2
- **Reviewer model:** openai/gpt-oss-20b
- **Date:** 2026-11-07T10:11:52+00:00

## Summary

The lesson demonstrates solid alignment with the learning objectives and provides clear, structured content with practical activities. Minor issues in clarity, consistency, and assessment design should be addressed to enhance instructional quality.

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
| Identify the semantic differences between INNER, LEFT, and FULL OUTER JOIN | s2, s3, s4 | s5, s6 | s7 | full |
| Select the appropriate join type for a given scenario | s2, s3, s4, s5 | s6 | s7 | full |
| Explain the impact of NULL values and join order on results and performance | s3, s4, s5 | s6 | s7 | partial |

## Issues (6)

### I1 - [HIGH] timing (whole lesson; found by rule check)

**Problem:** Section times add up to 49 min, target is 45 min (+4).  
**Suggested improvement:** Rebalance section minutes so the lesson fits exactly in the time budget.

### I2 - [HIGH] assessment_alignment (section s7; found by AI audit)

**Problem:** Question 2 asks about employees and departments, which were not introduced earlier, creating a mismatch with the lesson content.  
**Evidence:** "You need a list of all employees and any department they belong to; some employees have no department."  
**Suggested improvement:** Replace the question with a scenario involving students, enrollments, and courses to maintain consistency.

### I3 - [MEDIUM] clarity (section s2; found by AI audit)

**Problem:** The explanation of INNER JOIN uses a vague reference to PostgreSQL documentation [S1] without providing the actual content, leaving learners uncertain about the semantics.  
**Evidence:** "PostgreSQL describes this as combining rows that satisfy the expression [S1]."  
**Suggested improvement:** Insert a concise paraphrase of the documentation or a direct example illustrating the matching condition.

### I4 - [MEDIUM] structure (section s5; found by AI audit)

**Problem:** The example mixes a three-table join with a full outer join scenario, causing confusion about the intended learning focus.  
**Evidence:** "What if we need all students and all courses, even if no enrollment exists?"  
**Suggested improvement:** Separate the two examples into distinct subsections or clearly label them as separate tasks.

### I5 - [MEDIUM] time_feasibility (section s7; found by AI audit)

**Problem:** The knowledge check section is allocated 6 minutes but contains 5 questions, each with multiple subparts, which may exceed the time budget.  
**Evidence:** "6 min allotted, 211 words (~1.2 min)"  
**Suggested improvement:** Shorten the quiz to 3 questions or extend the allotted time to 8 minutes.

### I6 - [LOW] practical_application (section s6; found by AI audit)

**Problem:** The activity does not explicitly require students to write queries that handle NULL checks or performance considerations.  
**Evidence:** Tasks 1-3 focus on join types but omit NULL handling or optimizer hints.  
**Suggested improvement:** Add a subtask asking students to identify NULL values in the result set and explain their significance.

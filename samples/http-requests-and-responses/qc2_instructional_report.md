# QC Layer 2 - Instructional Quality - Audit Report

- **Score:** 79/100
- **Lesson version audited:** v2
- **Reviewer model:** openai/gpt-oss-20b
- **Date:** 2026-11-07T10:09:39+00:00

## Summary

The lesson aligns well with the stated objectives, provides clear structure, and includes practical examples and assessment. Minor issues around wording, example accessibility, and activity pacing should be addressed to enhance learner experience.

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
| Explain GET and POST methods, their characteristics (safe, idempotent) and typical use‑cases | s2 | s5 | s6 | full |
| Distinguish 2xx, 4xx, and 5xx response status code categories and identify common codes within each | s3 | s5 | s6 | full |

## Issues (6)

### I1 - [MEDIUM] alignment (section s6; found by AI audit)

**Problem:** Quiz question 3 asks about 404 but the answer key incorrectly cites 404 as client error; the explanation in the key references 404 as non‑existent resource, which is correct, but the wording in the question could mislead learners into thinking 404 is a server error.  
**Evidence:** Question 3: "What does a 404 status code indicate?" – answer key says "Client requested a non‑existent resource" but the question wording could be interpreted as a server error.  
**Suggested improvement:** Rephrase question to: "A 404 status code indicates that the requested resource does not exist on the server."

### I2 - [MEDIUM] examples (section s4; found by AI audit)

**Problem:** Worked examples rely heavily on curl syntax; beginners may not be familiar with command line, reducing accessibility.  
**Evidence:** Examples 1-3 all use bash commands without explanation of flags.  
**Suggested improvement:** Add a brief explanation of each curl flag, or provide a GUI-based tool example (e.g., Postman) to broaden accessibility.

### I3 - [MEDIUM] practical_application (section s5; found by AI audit)

**Problem:** Activity steps 4 and 5 assume availability of a mock server for 500 errors; not all learners will have this setup, leading to incomplete practice.  
**Evidence:** Step 5: "Trigger a server error (optional – use a mock service that returns 500"  
**Suggested improvement:** Provide a ready‑to‑use mock endpoint (e.g., https://httpstat.us/500) or include a local script example.

### I4 - [LOW] clarity (section s1; found by AI audit)

**Problem:** Hook uses phrase "web page sometimes disappear" – minor grammatical error; could confuse beginners.  
**Evidence:** "Why does a web page sometimes disappear after you click a button?"  
**Suggested improvement:** Change to "Why does a web page sometimes disappear after you click a button?" (add question mark) and consider rephrasing to "Why might a web page disappear after you click a button?"

### I5 - [LOW] assessment (section s6; found by AI audit)

**Problem:** Quiz question 2 includes option C "To bookmark a page" which is not a correct use of POST but could be confusing as bookmarking is typically GET.  
**Evidence:** Option C: "To bookmark a page"  
**Suggested improvement:** Replace with a clearly incorrect option such as "To delete a resource".

### I6 - [LOW] timing (section s5; found by AI audit)

**Problem:** Activity time allotment (9 min) may be tight for all four steps plus table completion, especially for beginners.  
**Evidence:** s5 allotted 9 min  
**Suggested improvement:** Extend activity to 12 min or split into two parts.

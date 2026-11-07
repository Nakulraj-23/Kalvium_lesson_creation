# QC Layer 2 - Instructional Quality - Audit Report

- **Score:** 85/100
- **Lesson version audited:** v3
- **Reviewer model:** openai/gpt-oss-20b
- **Date:** 2026-11-07T10:33:03+00:00

## Summary

The lesson aligns well with the objectives, offers clear explanations, solid examples, and practical application. Minor adjustments to quiz wording, example breadth, and timing would enhance clarity and learner confidence.

## Rubric (1-5)

| Criterion | Score |
|---|---|
| objective alignment | 5 |
| clarity | 4 |
| structure and flow | 4 |
| examples quality | 4 |
| practical application | 5 |
| assessment alignment | 5 |
| engagement | 4 |
| time feasibility | 4 |
| audience fit | 5 |

## Objective coverage

| Component | Taught | Practised | Assessed | Coverage |
|---|---|---|---|---|
| Explain GET and POST methods, their characteristics (safe, idempotent) and typical use‑cases | s2 | s5 | s6 | full |
| Distinguish 2xx, 4xx, and 5xx response status code families and identify common codes within each | s3 | s5 | s6 | full |

## Issues (6)

### I1 - [MEDIUM] alignment (section s6; found by AI audit)

**Problem:** Quiz question 3 asks about 404 but answer key incorrectly cites 404 as client error; the explanation in the key is correct but the question wording could mislead learners into thinking 404 is a server error.  
**Evidence:** Question 3: "What does a 404 status code indicate?" – answer key says client requested a non‑existent resource.  
**Suggested improvement:** Rephrase answer key to explicitly state 404 is a client error and add a brief note in the question to avoid confusion.

### I2 - [MEDIUM] examples (section s4; found by AI audit)

**Problem:** Worked examples rely on a fake API that does not allow triggering 400 errors, limiting the demonstration of client‑error handling.  
**Evidence:** Example 3 notes that JSONPlaceholder cannot trigger 400.  
**Suggested improvement:** Include a second example using httpbin.org/status/400 to show a real 400 response, or explain why 400 cannot be demonstrated with the chosen API.

### I3 - [MEDIUM] engagement (section s1; found by AI audit)

**Problem:** Hook uses a scenario but could be more interactive by asking learners to predict the outcome before revealing the explanation.  
**Evidence:** Hook text only describes scenario.  
**Suggested improvement:** Add a quick poll or a prompt: "What do you think will happen when you click Submit?" to increase engagement.

### I4 - [LOW] clarity (section s2; found by AI audit)

**Problem:** The table of safe vs idempotent properties uses check marks that may not be accessible to all learners; also the term "idempotent" is not defined in plain language.  
**Evidence:** Table under "Safe vs Idempotent" uses ✅/❌ symbols.  
**Suggested improvement:** Add a brief definition of idempotent (e.g., "repeating the request has the same effect") and replace symbols with text for clarity.

### I5 - [LOW] assessment (section s6; found by AI audit)

**Problem:** Quiz question 5 asks learners to infer from a 201 response but does not explicitly connect it to the earlier explanation of POST creating resources.  
**Evidence:** Question 5: "A POST request receives a 201 response. What should you infer?"  
**Suggested improvement:** Add a short explanatory note in the quiz or in the lesson that 201 indicates a resource was created to reinforce the link.

### I6 - [LOW] timing (section s5; found by AI audit)

**Problem:** The activity allocates 9 minutes but includes five curl commands plus a table to fill; this may be tight for beginners.  
**Evidence:** Activity steps 1-5 plus table.  
**Suggested improvement:** Provide a pre‑filled example table and reduce the number of curl commands to two (GET and POST) to fit the time budget.

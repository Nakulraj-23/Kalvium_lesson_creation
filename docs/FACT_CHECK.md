# Independent fact-check sheets

These facts were written independently of the tool and come from primary sources. Use them to (a) verify the generated lesson by hand and (b) check whether QC1's verdicts were correct. Record the results in the table at the bottom for your demo.

---

## Lesson 1: HTTP Requests and Responses

Primary source: **RFC 9110 "HTTP Semantics"** (IETF, June 2022, Internet Standard STD 97), https://www.rfc-editor.org/rfc/rfc9110. Secondary: MDN Web Docs, https://developer.mozilla.org/en-US/docs/Web/HTTP

| # | Fact | Source |
|---|---|---|
| H1 | GET requests transfer of a current representation of the target resource | RFC 9110 §9.3.1 |
| H2 | GET is **safe** (read-only semantics) and **idempotent** | RFC 9110 §9.2.1, §9.2.2 |
| H3 | Responses to GET are cacheable by default | RFC 9110 §9.3.1, §9.2.3 |
| H4 | Content in a GET request has no generally defined semantics; servers may reject it | RFC 9110 §9.3.1 |
| H5 | POST asks the target resource to process the enclosed representation according to its own semantics (form submission, creating resources, appending data) | RFC 9110 §9.3.3 |
| H6 | POST is **neither safe nor idempotent** (repeating it may create duplicates) | RFC 9110 §9.2.1, §9.2.2 |
| H7 | A successful POST that creates a resource should return **201 Created** (ideally with a Location header) | RFC 9110 §9.3.3, §15.3.2 |
| H8 | Status codes are three-digit integers; the first digit defines the class: 1xx informational, 2xx successful, 3xx redirection, **4xx client error**, **5xx server error** | RFC 9110 §15 |
| H9 | 2xx = the request was successfully received, understood and accepted (e.g. 200 OK, 201 Created, 204 No Content) | RFC 9110 §15.3 |
| H10 | 4xx = the client seems to have erred (e.g. 400 Bad Request, 401 Unauthorized = missing/invalid authentication, 403 Forbidden, 404 Not Found, 405 Method Not Allowed, 409 Conflict, 422 Unprocessable Content) | RFC 9110 §15.5 |
| H11 | 429 Too Many Requests is defined in RFC 6585, not RFC 9110 | RFC 6585 §4 |
| H12 | 5xx = the server is aware it has erred or cannot perform the request (500 Internal Server Error, 502 Bad Gateway, 503 Service Unavailable, 504 Gateway Timeout) | RFC 9110 §15.6 |
| H13 | A client that sees an unrecognised status code must treat it as the x00 code of its class (e.g. unknown 4xx → 400) | RFC 9110 §15 |

**Common errors the QC layers should catch:**
* "POST is more secure than GET". Without HTTPS both are plaintext. GET parameters do appear in URLs, logs and history, which is a privacy concern, but the request isn't encrypted either way.
* "GET cannot send data". It can send data in the query string; it just shouldn't change server state.
* "401 means forbidden". 401 means *unauthenticated*; 403 means authenticated but not allowed.
* "4xx means the server is broken". That is 5xx.
* "PUT/POST are both idempotent". PUT is idempotent; POST is not.

---

## Lesson 2: SQL Joins (second test lesson)

Sources: PostgreSQL docs, "Joins Between Tables" (https://www.postgresql.org/docs/current/tutorial-join.html) and "Table Expressions §7.2.1.1" (https://www.postgresql.org/docs/current/queries-table-expressions.html); SQLite 3.39.0 release notes (https://www.sqlite.org/releaselog/3_39_0.html); MySQL Reference Manual "JOIN Clause" (https://dev.mysql.com/doc/refman/8.4/en/join.html).

| # | Fact | Source |
|---|---|---|
| J1 | INNER JOIN returns only row pairs that satisfy the join condition in both tables | PostgreSQL §7.2.1.1 |
| J2 | LEFT (OUTER) JOIN returns every row of the left table; where no right-side row matches, right columns are NULL | PostgreSQL §7.2.1.1 |
| J3 | RIGHT JOIN is the mirror image of LEFT JOIN | PostgreSQL §7.2.1.1 |
| J4 | FULL OUTER JOIN returns all rows from both tables, NULL-filled on the side with no match | PostgreSQL §7.2.1.1 |
| J5 | The keyword OUTER is optional (LEFT JOIN = LEFT OUTER JOIN) | PostgreSQL §7.2.1.1 |
| J6 | MySQL does not support FULL OUTER JOIN; it is usually emulated with LEFT JOIN UNION RIGHT JOIN | MySQL manual, JOIN clause |
| J7 | SQLite added RIGHT and FULL OUTER JOIN in version 3.39.0 (2022) | SQLite release log |
| J8 | Putting a condition on the right table in WHERE (not ON) after a LEFT JOIN discards the NULL rows, so it behaves like an INNER JOIN | PostgreSQL §7.2.1.1 (ON vs WHERE note) |
| J9 | NULL never equals NULL in a join condition, so rows with NULL keys do not match each other | SQL three-valued logic; PostgreSQL docs on comparison |
| J10 | CROSS JOIN produces the Cartesian product (every row combined with every row) | PostgreSQL §7.2.1.1 |

---

## Verification log (actual run, 7 Nov 2026)

I checked every factual claim in both generated lessons by hand against the facts above. QC1 had audited version 2 of each lesson (after the QC recommendations were applied).

### Lesson 1: HTTP Requests and Responses

| Claim in lesson | Fact # | Correct? | QC1 verdict | QC caught it? |
|---|---|---|---|---|
| GET is safe and idempotent | H2 | ✅ | supported | n/a |
| POST is neither safe nor idempotent | H6 | ✅ | supported | n/a |
| GET parameters go in the query string; GET has no body | H1, H4 | ✅ (simplified) | supported | n/a |
| Status code first digit defines the class: 2xx success, 4xx client error, 5xx server error | H8–H12 | ✅ | supported | n/a |
| 201 is returned after a POST that creates a resource | H7 | ✅ | supported | n/a |
| 404 = target resource not found; 503 = service unavailable | H10, H12 | ✅ | supported | n/a |
| "`Content-Type` describes the body you are sending (**only for POST**)" | – | ❌ also used by PUT/PATCH and on responses | not flagged as wrong (only "lacks citation", F3) | ⚠️ partly |
| Example 3: POSTing invalid data to JSONPlaceholder returns **400** | – | ❌ JSONPlaceholder is a fake API and accepts any body, so it returns 201 | QC1 F5 flagged Example 3 as inconsistent; QC2 I3 flagged the 500 step as impractical | ⚠️ partly |
| Activity step 5: "use a mock service that returns 500" (no concrete way given) | – | vague, not wrong | QC2 I3 | ✅ |
| Reference cites RFC 7231 | – | ⚠️ outdated: RFC 7231 was obsoleted by RFC 9110 in 2022 (the facts in the lesson are still correct) | not flagged | ❌ |

### Lesson 2: SQL Joins

| Claim in lesson | Fact # | Correct? | QC1 verdict | QC caught it? |
|---|---|---|---|---|
| INNER JOIN returns only rows that satisfy the condition in both tables | J1 | ✅ | supported | n/a |
| LEFT JOIN keeps all left rows, NULL-fills unmatched right columns | J2 | ✅ | supported | n/a |
| FULL OUTER JOIN returns all rows from both tables with NULLs for gaps | J4 | ✅ | supported | n/a |
| LEFT JOIN = LEFT OUTER JOIN | J5 | ✅ | supported | n/a |
| NULL never equals NULL in a join condition | J9 | ✅ | supported | n/a |
| MySQL has no native FULL OUTER JOIN; emulate it with LEFT UNION RIGHT | J6 | ✅ | the uncited MySQL claim was removed by an applied QC1 fix; it stays in the quiz | n/a |
| An earlier quiz answer key said joins are "always evaluated left-to-right regardless of parentheses" | J-docs | ❌ | **contradicted** (F1, high) → fixed by "Apply recommendations" | ✅ |
| "Use parentheses to guide join order **for performance**" | – | ⚠️ misleading: the planner reorders inner joins; parentheses matter for outer-join *results* | not flagged | ❌ |
| Section minutes add up to 49 (after the QC revision) | – | ❌ the budget is 45 | QC2 rule check I1 (high) | ✅ |
| Missing pitfall: a WHERE condition on the right table after a LEFT JOIN turns it into an INNER JOIN | J8 | gap | not flagged | ❌ |

### What was fixed and how
* **Through the tool (Apply QC recommendations, v1 → v2):** 6 QC1 issues per lesson: missing citations, an invented URL, the contradicted join-order answer key, and an unsupported MySQL claim. QC1 scores went from **71 → 85** (HTTP) and **49 → 74** (SQL).
* **Instructor edits after this manual check (v2 → v3, `finalize_samples.py`):** Content-Type wording, Example 3 replaced with a real 404 example, a concrete httpbin 500 step, accurate join-order wording, and the WHERE-vs-ON pitfall added. Minutes rebalanced to 45. Both QC layers were then **re-run on v3**, and those are the reports in `samples/`. Final scores: HTTP QC1 **94** / QC2 **85**, SQL QC1 **72** / QC2 **81**. The SQL QC1 score is lower because the re-audit raised new, valid points: RIGHT JOIN is used in the activity but never taught, the MySQL claim has no citation, and a book link is unreachable. Those are left as open recommendations.
* **Code fixes prompted by this check:** citation-format normalisation (the model wrote `【S1】`), cleanup of glued search-result titles in references, and automatic 45-minute rebalancing after a QC revision.

### Summary
* **20 claims and items checked by hand.** 12 were correct. The other 8 had problems: 3 were wrong (Content-Type, Example 3, the join-order answer key), 1 was misleading (join performance), 1 was outdated (RFC 7231), 1 was vague (the 500 step), 1 was a timing error (49 minutes) and 1 was a missing pitfall (WHERE vs ON).
* **The QC layers caught 5 of the 8:** 3 fully (the contradicted answer key, the timing error, the vague 500 step) and 2 partly (both HTTP example problems were flagged, but not identified as factual errors). They missed 3: the outdated RFC, the join-performance wording and the WHERE-vs-ON gap.
* **Why the misses happened:** the free-tier daily limit on the strongest model (GPT-OSS-120B) was used up, so the QC layers ran on GPT-OSS-20B, and Gemini's Google-Search verification was rate-limited (429). That step is reported in each QC1 report as "Independent web verification step failed". With grounding available, the outdated-RFC and "only for POST" claims are exactly what the web re-check is designed to catch.
* **Takeaway:** the QC layers reduce risk a lot, but they don't replace a final human review. That's why the tool makes every change a reviewable, versioned instructor decision.

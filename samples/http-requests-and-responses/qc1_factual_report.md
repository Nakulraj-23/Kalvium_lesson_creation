# QC Layer 1 - Research & Factual Accuracy - Audit Report

- **Score:** 85/100
- **Lesson version audited:** v2
- **Reviewer model:** openai/gpt-oss-20b
- **Date:** 2026-11-07T10:09:18+00:00

## Summary

The lesson accurately presents core HTTP method semantics and status code meanings, with most claims supported by reputable MDN and RFC sources. Minor gaps include lack of explicit citations for some statements and a few oversimplified claims about bookmarking and caching. Overall research quality is high, but adding precise references and clarifying ambiguous points would strengthen factual accuracy. (Claims checked: 17; supported by sources: 94%.)

## Issues (5)

### F1 - [HIGH] gap (section s2; found by AI audit)

**Problem:** Missing explicit definition of idempotence for POST (though implied)  
**Evidence:** S2  
**Suggested improvement:** Add statement that POST is not idempotent with citation

### F2 - [MEDIUM] misleading (section s2; found by AI audit)

**Problem:** Claim that GET is ideal for bookmarking and caching is not explicitly supported by cited sources  
**Evidence:** S1  
**Suggested improvement:** Add citation to caching behavior or rephrase

### F3 - [MEDIUM] citation (section s2; found by AI audit)

**Problem:** Content-Type header claim lacks direct citation  
**Evidence:** S4  
**Suggested improvement:** Provide explicit source stating Content-Type is required for POST bodies

### F4 - [LOW] process (whole lesson; found by rule check)

**Problem:** Independent web verification step failed (Gemini rate limit / quota exceeded (HTTP 429). Wait a minute and press Retry.); verdicts rely on source excerpts only.  
**Suggested improvement:** Re-run QC1 later.

### F5 - [LOW] inconsistency (section s4; found by AI audit)

**Problem:** Example 3 shows 400 Bad Request but does not explain why (invalid data)  
**Evidence:** S5  
**Suggested improvement:** Clarify that server rejected due to missing required fields

## Claim verification

| # | Claim | Section | Cited | Verdict | Notes |
|---|---|---|---|---|---|
| 1 | GET requests are safe and idempotent | s2 | S1, S2 | supported | MDN sources state GET is safe and idempotent |
| 2 | GET requests should not contain a body | s2 | S1, S2 | supported | MDN explicitly says GET should not contain a body |
| 3 | GET parameters are placed in the query string | s2 | S1 | supported | MDN example shows query string usage |
| 4 | GET is ideal for reading data, bookmarking, and caching | s2 | S1 | partially_supported | MDN mentions reading data; bookmarking and caching are common but not explicitly stated |
| 5 | POST is not safe and not idempotent | s2 | S2 | supported | MDN states POST is not safe nor idempotent |
| 6 | POST is used for creating resources, submitting forms, or any operation that changes state | s2 | S2 | supported | MDN describes POST for state-changing operations |
| 7 | Content-Type header is required for POST bodies | s2 | S4 | partially_supported | MDN notes Content-Type describes body; not strictly required but recommended |
| 8 | GET is safe and idempotent | s6 | S1 | supported | Quiz answer aligns with MDN |
| 9 | POST is used for actions that change server state | s6 | S5 | supported | Answer key cites S5 which covers POST semantics |
| 10 | 404 indicates the target URL does not exist | s6 | S5 | supported | RFC 7231 defines 404 as Not Found |
| 11 | 503 belongs to 5xx family and means service unavailable | s6 | S5 | supported | RFC 7231 defines 503 |
| 12 | 201 response to POST indicates a new resource was created | s6 | S5 | supported | RFC 7231 defines 201 Created |
| 13 | GET returns 200 OK for successful retrieval | s4 | S5 | supported | Example shows 200 |
| 14 | POST returns 201 Created for successful creation | s4 | S5 | supported | Example shows 201 |
| 15 | 400 Bad Request indicates malformed client data | s4 | S5 | supported | RFC 7231 defines 400 |
| 16 | GET is safe and idempotent, POST is not safe nor idempotent | s7 | S1, S2 | supported | Summary repeats earlier claims |
| 17 | Common codes include 200, 201, 400, 401, 404, 500, 503 | s7 | S5 | supported | RFC 7231 lists these codes |

## Source assessment

| Source | Tier | Relevance | Note |
|---|---|---|---|
| S1 GET request method - HTTP | MDN - MDN Web Docs (developer.mozilla.org) | A | high | MDN authoritative reference for GET semantics |
| S2 HTTP request methods - MDN Web Docs (developer.mozilla.org) | A | high | MDN authoritative reference for HTTP methods |
| S3 HTTP: Hypertext Transfer Protocol | MDN - MDN Web Docs (developer.mozilla.org) | A | medium | General HTTP overview, not directly cited |
| S4 HTTP reference - HTTP | MDN - MDN Web Docs (developer.mozilla.org) | A | medium | MDN reference for headers, used for Content-Type claim |
| S5 RFC 7231 - Hypertext Transfer Protocol (HTTP/1.1): Semantics ...List of HTTP status codes - WikipediaHTTP Status Codes Reference — Complete List with ExplanationsHypertext Transfer Protocol (HTTP) Status Code RegistryHTTP Status Codes Reference - 1xx-5xx Explained - OltoolSMTP Status Codes Explained — 2xx, 4xx, 5xx & X.Y.ZHTTP Status Code Lookup – Find & Explain 1xx, 2xx, 3xx, 4xx ... (datatracker.ietf.org) | A | high | RFC 7231 official standard for status codes |
| S6 List of HTTP status codes - Wikipedia (en.wikipedia.org) | B | low | Wikipedia list, not directly cited |
| S7 HTTP - Wikipedia (wikipedia.org) | B | low | Wikipedia overview, not directly cited |
| S8 GET - HTTP | MDN - devdoc.net (devdoc.net) | C | low | MDN alternative source, not directly cited |
| S9 HTTP GET Method: Complete Guide with Examples (howhttpworks.com) | C | low | Blog article, not directly cited |

_Tier key: A = standards/official docs/.gov/.edu, B = reputable reference, C = general web/blog, D = user-generated._

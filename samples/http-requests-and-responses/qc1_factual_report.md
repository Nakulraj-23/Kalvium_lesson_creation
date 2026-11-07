# QC Layer 1 - Research & Factual Accuracy - Audit Report

- **Score:** 94/100
- **Lesson version audited:** v3
- **Reviewer model:** openai/gpt-oss-20b
- **Date:** 2026-11-07T10:32:44+00:00

## Summary

The lesson accurately presents core HTTP method semantics and status code families, with most claims supported by authoritative sources such as MDN and RFC 7231. Minor oversimplifications (e.g., bookmarking/caching for GET) and a few uncited assertions are noted, but overall research quality and factual accuracy are high. (Claims checked: 25; supported by sources: 98%.)

## Issues (4)

### F1 - [MEDIUM] misleading (section s2; found by AI audit)

**Problem:** Claim that GET is ideal for bookmarking and caching is not explicitly supported by cited sources  
**Evidence:** S1  
**Suggested improvement:** Add citation to caching behavior or rephrase to 'commonly used for bookmarking and caching due to idempotence and cacheability'

### F2 - [LOW] process (whole lesson; found by rule check)

**Problem:** Independent web verification step failed (Gemini rate limit / quota exceeded (HTTP 429). Wait a minute and press Retry.); verdicts rely on source excerpts only.  
**Suggested improvement:** Re-run QC1 later.

### F3 - [LOW] gap (section s2; found by AI audit)

**Problem:** Missing explicit mention that POST is not cacheable  
**Evidence:** S2  
**Suggested improvement:** Include note that POST responses are generally not cached unless explicitly allowed by Cache-Control

### F4 - [LOW] citation (section s4; found by AI audit)

**Problem:** Example 3 claims JSONPlaceholder does not validate input to trigger 400, but no source cited  
**Evidence:** none  
**Suggested improvement:** Add citation or remove claim

## Claim verification

| # | Claim | Section | Cited | Verdict | Notes |
|---|---|---|---|---|---|
| 1 | GET requests are safe and idempotent | s2 | S1, S2 | supported | MDN sources state GET is safe and idempotent |
| 2 | GET requests should not contain a body | s2 | S1, S2 | supported | MDN explicitly says GET should not contain a body |
| 3 | GET parameters are placed in the query string | s2 | S1 | supported | MDN example shows query string usage |
| 4 | GET is ideal for reading data, bookmarking, and caching | s2 | S1 | partially_supported | MDN mentions reading data; bookmarking and caching are implied but not explicitly stated |
| 5 | POST requests send data in the request body and are not safe or idempotent | s2 | S2 | supported | MDN states POST is not safe or idempotent |
| 6 | POST is used for creating resources, submitting forms, or any operation that changes state | s2 | S2 | supported | MDN describes POST for state-changing operations |
| 7 | Content-Type header is sent whenever the request has a body (POST, PUT, PATCH) | s2 | S4 | supported | MDN reference explains Content-Type usage |
| 8 | Host header together with request line identifies the target resource | s2 | S4 | supported | MDN reference mentions Host header role |
| 9 | 2xx status codes indicate success – request was received, understood, and processed | s3 | S5 | supported | RFC 7231 defines 2xx as success |
| 10 | 4xx status codes indicate client error – bad syntax or cannot be fulfilled | s3 | S5 | supported | RFC 7231 defines 4xx as client error |
| 11 | 5xx status codes indicate server error – server failed to fulfill a valid request | s3 | S5 | supported | RFC 7231 defines 5xx as server error |
| 12 | 200 OK means GET succeeded and body contains requested data | s3 | S5 | supported | RFC 7231 specifies 200 OK semantics |
| 13 | 201 Created is returned after a successful POST that created a new resource | s3 | S5 | supported | RFC 7231 specifies 201 Created semantics |
| 14 | 400 Bad Request indicates client sent malformed data (e.g., missing required fields) | s3 | S5 | supported | RFC 7231 defines 400 Bad Request |
| 15 | 404 Not Found means target URL does not exist | s3 | S5 | supported | RFC 7231 defines 404 Not Found |
| 16 | 500 Internal Server Error signals a problem on the server side, not the client’s fault | s3 | S5 | supported | RFC 7231 defines 500 Internal Server Error |
| 17 | 503 Service Unavailable is a 5xx server error indicating service unavailable | s3 | S5 | supported | RFC 7231 defines 503 Service Unavailable |
| 18 | GET request to https://jsonplaceholder.typicode.com/posts/1 returns 200 OK | s4 | S5 | supported | curl example shows 200 OK |
| 19 | POST request to https://jsonplaceholder.typicode.com/posts returns 201 Created | s4 | S5 | supported | curl example shows 201 Created |
| 20 | GET request to https://jsonplaceholder.typicode.com/posts/99999 returns 404 Not Found | s4 | S5 | supported | curl example shows 404 Not Found |
| 21 | GET is safe and idempotent | s6 | S1 | supported | Quiz answer aligns with MDN |
| 22 | POST is used for actions that change server state | s6 | S5 | supported | Quiz answer aligns with RFC |
| 23 | 404 indicates client requested a non-existent resource | s6 | S5 | supported | Quiz answer aligns with RFC |
| 24 | 503 belongs to 5xx family and means service unavailable | s6 | S5 | supported | Quiz answer aligns with RFC |
| 25 | 201 response to POST means a new resource was created successfully | s6 | S5 | supported | Quiz answer aligns with RFC |

## Source assessment

| Source | Tier | Relevance | Note |
|---|---|---|---|
| S1 GET request method - HTTP | MDN - MDN Web Docs (developer.mozilla.org) | A | high | MDN Web Docs, authoritative for HTTP method semantics |
| S2 HTTP request methods - MDN Web Docs (developer.mozilla.org) | A | high | MDN Web Docs, authoritative for HTTP method semantics |
| S3 HTTP: Hypertext Transfer Protocol | MDN - MDN Web Docs (developer.mozilla.org) | A | medium | General MDN overview, less specific to claims |
| S4 HTTP reference - HTTP | MDN - MDN Web Docs (developer.mozilla.org) | A | medium | MDN reference for headers, reliable but not primary for method semantics |
| S5 RFC 7231 - Hypertext Transfer Protocol (HTTP/1.1): Semantics ...List of HTTP status codes - WikipediaHTTP Status Codes Reference — Complete List with ExplanationsHypertext Transfer Protocol (HTTP) Status Code RegistryHTTP Status Codes Reference - 1xx-5xx Explained - OltoolSMTP Status Codes Explained — 2xx, 4xx, 5xx & X.Y.ZHTTP Status Code Lookup – Find & Explain 1xx, 2xx, 3xx, 4xx ... (datatracker.ietf.org) | A | high | RFC 7231, official standard for HTTP/1.1 semantics |
| S6 List of HTTP status codes - Wikipedia (en.wikipedia.org) | B | low | Wikipedia list, secondary source |
| S7 HTTP - Wikipedia (wikipedia.org) | B | low | Wikipedia overview, secondary source |
| S8 GET - HTTP | MDN - devdoc.net (devdoc.net) | C | low | MDN devdoc, duplicate of S1 |
| S9 HTTP GET Method: Complete Guide with Examples (howhttpworks.com) | C | medium | Third‑party guide, not primary source |

_Tier key: A = standards/official docs/.gov/.edu, B = reputable reference, C = general web/blog, D = user-generated._

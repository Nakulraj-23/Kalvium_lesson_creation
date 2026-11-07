# HTTP Requests and Responses

**Learning objective:** Explain GET and POST methods and distinguish between 2xx, 4xx, and 5xx response status categories.  
**Duration:** 45 minutes (self-study or instructor-led)  
**Audience:** Beginner web-development students

### By the end of this lesson you will be able to:

- **O1** Explain the GET and POST HTTP methods, their characteristics (safe, idempotent) and typical use‑cases.
- **O2** Distinguish the 2xx, 4xx, and 5xx response status code categories and identify common codes within each.

### Lesson plan

| # | Section | Type | Minutes | Objectives |
|---|---|---|---|---|
| 1 | Why does a web page sometimes disappear after you click a button? | hook | 3 | O1, O2 |
| 2 | GET vs POST: What they are and when to use them | concept | 8 | O1 |
| 3 | Response status code families | concept | 7 | O2 |
| 4 | Worked examples with curl | example | 6 | O1, O2 |
| 5 | Hands‑on: Make GET and POST calls and interpret status codes | activity | 9 | O1, O2 |
| 6 | Quiz – Test your understanding | knowledge check | 6 | O1, O2 |
| 7 | Key takeaways & common pitfalls | summary | 6 | O1, O2 |
| | **Total** | | **45** | |

## 1. Why does a web page sometimes disappear after you click a button? (3 min)

Imagine you built a form that saves a new blog post. When you press **Submit**, the page either shows the new post or shows an error like *404 Not Found*. Which part of the HTTP conversation decides what you see?  In the next 45 minutes you’ll learn how the request method you choose (GET vs POST) and the server’s status code shape that experience.

## 2. GET vs POST: What they are and when to use them (8 min)

### GET
- Retrieves a representation of a resource without a request body. It is **safe** (doesn’t change server state) and **idempotent** – repeating the request has the same effect [1][2].
- Parameters are placed in the query string: `GET /search?q=books HTTP/1.1` [1].
- Ideal for reading data, bookmarking, and caching.

### POST
- Sends data to the server in the request body (e.g., form fields, JSON). Not safe and not idempotent – each call can create a new resource [2].
- Used for creating resources, submitting forms, or any operation that changes state.
- Example request line: `POST /api/articles HTTP/1.1` with `Content-Type: application/json` header.

### Safe vs Idempotent
| Property | GET | POST |
|----------|-----|------|
| Safe? | ✅ | ❌ |
| Idempotent? | ✅ | ❌ |
| Typical use‑case | Read‑only fetches, search queries | Create/update actions, file uploads |

**Headers that matter**
- `Accept` tells the server which media types you can handle.
- `Content-Type` describes the body you are sending (only for POST).
- `Host` and the request line together identify the target resource [3].

## 3. Response status code families (7 min)

HTTP responses start with a three‑digit status code. The first digit groups them:

| Family | Meaning | Common codes |
|--------|---------|--------------|
| **2xx** | Success – the request was received, understood, and processed [4]. | `200 OK`, `201 Created` |
| **4xx** | Client error – the request has bad syntax or cannot be fulfilled [4]. | `400 Bad Request`, `401 Unauthorized`, `404 Not Found` |
| **5xx** | Server error – the server failed to fulfill a valid request [4]. | `500 Internal Server Error`, `503 Service Unavailable` |

**What the codes tell you**
- `200` means the GET succeeded and the body contains the requested data.
- `201` is returned after a successful POST that created a new resource.
- `400` indicates the client sent malformed data (e.g., missing required fields).
- `404` means the target URL does not exist.
- `500` signals a problem on the server side, not the client’s fault.

These families help you decide how to handle the response in code (retry, show error, etc.).

## 4. Worked examples with curl (6 min)

### Example 1 – GET request
```bash
curl -i "https://jsonplaceholder.typicode.com/posts/1"
```
Output (truncated):
```
HTTP/1.1 200 OK
Content-Type: application/json; charset=utf-8
...
{"userId":1,"id":1,"title":"..."}
```
- Status **200** → success (2xx family) [4].
- No request body, only a query path [1].

### Example 2 – POST request
```bash
curl -i -X POST https://jsonplaceholder.typicode.com/posts \
     -H "Content-Type: application/json" \
     -d '{"title":"My Post","body":"Hello","userId":1}'
```
Output (truncated):
```
HTTP/1.1 201 Created
Content-Type: application/json; charset=utf-8
...
{"id":101,"title":"My Post","body":"Hello","userId":1}
```
- Status **201** → resource created (2xx family) [4].
- Request includes a JSON body and `Content-Type` header.

### Example 3 – Bad request (4xx)
```bash
curl -i -X POST https://jsonplaceholder.typicode.com/posts \
     -H "Content-Type: application/json" \
     -d '{"invalid":"data"}'
```
Possible response:
```
HTTP/1.1 400 Bad Request
```
Shows how the server signals client‑side problems [4].

## 5. Hands‑on: Make GET and POST calls and interpret status codes (9 min)

#### Goal
Use **curl** (or any HTTP client) to send GET and POST requests to a public test API and record the status codes.

#### Steps
1. Open a terminal.
2. **GET** a known resource:
   ```bash
   curl -s -o /dev/null -w "%{http_code}\n" https://jsonplaceholder.typicode.com/posts/5
   ```
   *Write down the code you see.*
3. **POST** a new resource:
   ```bash
   curl -s -o /dev/null -w "%{http_code}\n" -X POST https://jsonplaceholder.typicode.com/posts \
        -H "Content-Type: application/json" \
        -d '{"title":"Test","body":"Demo","userId":1}'
   ```
   *Note the code.*
4. **Trigger a client error** by requesting a non‑existent endpoint:
   ```bash
   curl -s -o /dev/null -w "%{http_code}\n" https://jsonplaceholder.typicode.com/unknown
   ```
5. **Trigger a server error** (optional – use a mock service that returns 500, e.g., a local mock server configured for this purpose).
6. Fill the table below:
| Request | URL | Method | Status code | Family |
|---------|-----|--------|-------------|--------|
| 1 | … | GET | … | … |
| 2 | … | POST | … | … |
| 3 | … | GET | … | … |
| 4 | … | GET | … | … |

#### Expected outcome
- GET returns **200** (2xx).
- POST returns **201** (2xx).
- Bad URL returns **404** (4xx).
- Optional server error returns **500** (5xx).
- Map each code to its family and explain why it occurred.

## 6. Quiz – Test your understanding (6 min)

1. **Which HTTP method is safe and idempotent?**
   - A) GET  **(Correct)**
   - B) POST
   - C) DELETE
2. **When should you use POST instead of GET?**
   - A) To retrieve a cached image
   - B) To submit form data that creates a new record **(Correct)**
   - C) To bookmark a page
3. **What does a 404 status code indicate?**
   - A) Server malfunction
   - B) Client requested a non‑existent resource **(Correct)**
   - C) Request succeeded
4. **Which family does 503 belong to and what does it mean?**
   - A) 2xx – Success
   - B) 4xx – Client error
   - C) 5xx – Server error, service unavailable **(Correct)**
5. **A POST request receives a 201 response. What should you infer?**
   - A) The request failed
   - B) A new resource was created successfully **(Correct)**
   - C) The client sent bad data

**Answer key**
1. GET is defined as safe and idempotent【S1】.
2. POST is used for actions that change server state【S5】.
3. 404 signals the target URL does not exist【S5】.
4. 5xx codes indicate server‑side problems; 503 means service unavailable【S5】.
5. 201 means the server created a resource as a result of the POST【S5】.

## 7. Key takeaways & common pitfalls (6 min)

### Remember
- **GET** = read‑only, safe, idempotent, query string for parameters.
- **POST** = send data, changes state, not safe nor idempotent.
- Status families: **2xx** success, **4xx** client error, **5xx** server error.
- Common codes: 200, 201, 400, 401, 404, 500, 503.

### Common mistakes
- Putting a request body in a GET – many servers will reject it with a 4xx [1].
- Ignoring the response code and assuming success.
- Forgetting to set `Content-Type` for POST bodies, leading to 400 errors.

Use the status code to decide whether to retry, show a user‑friendly error, or proceed.

## Supplementary videos (optional, not counted in the 45 minutes)

- **[HTTP Request Methods | GET, POST, PUT, DELETE](https://www.youtube.com/watch?v=tkfVQK6UxDI)** - Curious Code, 3:01. Clear visual of GET vs POST semantics in under 4 minutes *Watch: after concept sections s2.*
- **[HTTP Status Codes Explained In 5 Minutes](https://www.youtube.com/watch?v=qmpUfWN7hh4)** - ByteByteGo, 5:07. Concise explanation of 2xx, 4xx, 5xx families and common codes *Watch: after concept section s3.*

## References

1. GET request method - HTTP | MDN - MDN Web Docs. *developer.mozilla.org*. https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Methods/GET
2. HTTP request methods - MDN Web Docs. *developer.mozilla.org*. https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Methods
3. HTTP reference - HTTP | MDN - MDN Web Docs. *developer.mozilla.org*. https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference
4. RFC 7231 - Hypertext Transfer Protocol (HTTP/1.1): Semantics ...List of HTTP status codes - WikipediaHTTP Status Codes Reference — Complete List with ExplanationsHypertext Transfer Protocol (HTTP) Status Code RegistryHTTP Status Codes Reference - 1xx-5xx Explained - OltoolSMTP Status Codes Explained — 2xx, 4xx, 5xx & X.Y.ZHTTP Status Code Lookup – Find & Explain 1xx, 2xx, 3xx, 4xx .... *datatracker.ietf.org*. https://datatracker.ietf.org/doc/html/rfc7231

### Videos

- HTTP Request Methods | GET, POST, PUT, DELETE - Curious Code (3:01). https://www.youtube.com/watch?v=tkfVQK6UxDI
- HTTP Status Codes Explained In 5 Minutes - ByteByteGo (5:07). https://www.youtube.com/watch?v=qmpUfWN7hh4

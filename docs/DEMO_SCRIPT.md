# Demo video script (about 6–7 minutes)

**Before recording**
1. In Terminal: `cd ~/Desktop/lesson-creation-tool && source .venv312/bin/activate && streamlit run app.py`
2. Open the GitHub repo in a second browser tab.
3. Recorder: QuickTime → File → New Screen Recording (turn on the microphone in Options).
4. Close other tabs and turn on Do Not Disturb.

Text in *italics* is what you say. Read it naturally; it doesn't have to be word-perfect.

---

### 1. Intro (0:00–0:30) · show the GitHub README
*"Hi, I'm Nakul. This is my AI Lesson Creation Tool for the AI Research Intern task. You give it a lesson title and a learning objective. It researches websites, books and YouTube, writes a 45-minute lesson with citations, and then checks it with two independent quality-control layers. It's built in Python with Streamlit. Groq's free open-weight models write and audit the lessons, and Gemini adds Google-Search grounding."*

### 2. Input validation (0:30–0:50) · app → New lesson
Click **Research & generate lesson** with both fields empty.
*"Empty or too-short inputs are rejected before anything runs."*

### 3. Generate a lesson live (0:50–2:00)
Click **Load sample: HTTP Requests and Responses** → **Research & generate lesson**.
While the progress messages scroll:
*"The pipeline has four steps: research, generation, QC 1 and QC 2. Each step is saved separately, so if one fails, the earlier work is kept and only that step needs a retry. Research plans search queries, then searches DuckDuckGo and reads the full pages, checks Wikipedia, Google Books and Open Library, and finds YouTube videos."*
(If it's slow, open the saved HTTP lesson from the sidebar instead and say *"here's one I generated earlier"*.)

### 4. Research tab (2:00–2:40)
Scroll through the websites, books and videos tables. Open one source excerpt.
*"Every source gets a reliability tier: A is standards and official docs like MDN and RFCs, B is reputable references, C is general web. User-generated sites like Reddit are excluded. Code gives each source an ID, and the model can only cite those IDs, so it can't invent references. This is the actual text the model and the fact-checker read."*

### 5. Preview tab (2:40–3:20)
Scroll the lesson.
*"The lesson plan adds up to exactly 45 minutes: a hook, concepts, worked examples, a hands-on activity, a quiz with an answer key, and a summary. Each section maps to sub-objectives. Citations are numbered, the supplementary videos are embedded, and the reference list at the end is built by code from the sources that were actually cited."*

### 6. QC 1 · Facts (3:20–4:10)
Show the score, the claim table, source assessment and issues.
*"QC 1 checks research and factual accuracy. It pulls out every factual claim and checks it against the source excerpts. Claims it can't support get re-checked separately with Google Search. Code also catches citations to sources that don't exist, URLs the model made up, and broken links. Every issue shows evidence and a suggested fix, and says whether it came from a rule check or the AI audit."*

### 7. QC 2 · Instruction (4:10–4:40)
Show the objective coverage table and the rubric.
*"QC 2 checks instructional quality. It breaks the objective down on its own and maps where each part is taught, practised and assessed. It scores a nine-point rubric. Code checks the timing and reading load, and confirms there's an activity and a quiz."*

### 8. Apply recommendations (4:40–5:20)
Tick two or three issues → **Apply** → show the diff → **Accept**.
*"I can pick recommendations and apply them. The AI drafts a revision of only the affected sections, I review the diff, and I accept or reject it. Accepting saves a new version."* Point at the warning: *"The QC reports now say they audited an older version, so I'd re-run them."*

### 9. Edit and history (5:20–5:50)
Edit tab: change a sentence → **Save changes**. History tab: show the versions.
*"I can edit any section directly. Every save is a new version, and any older version can be restored, so nothing is ever overwritten."*

### 10. Fact verification (5:50–6:20) · GitHub: docs/FACT_CHECK.md
*"I also fact-checked both test lessons by hand against RFC 9110 and the PostgreSQL and MySQL docs: 20 claims. The QC layers caught 5 of the 8 problems, like a contradicted quiz answer and a lesson that ran to 49 minutes. They missed 3, like an outdated RFC reference, because Gemini's web check was rate-limited on the free tier. I fixed those as instructor edits. So the QC layers reduce the work but don't replace a final human review, which is why every change goes through the instructor."*

### 11. Export and wrap-up (6:20–6:50)
Export tab → download the ZIP → open `lesson.html` and one QC report.
*"Export gives the lesson as Markdown, HTML and Word, plus the references and both QC reports. For errors: every AI call has a timeout and switches to another model automatically if one is busy, and failed steps get a Retry button. The second test lesson, SQL Joins, and both QC reports are in the samples folder in the repo. Thanks for watching."*

---

## Questions they may ask
| Question | Answer |
|---|---|
| How do you stop hallucinated references? | Code gives IDs to real retrieved sources, the model can only cite those IDs, and unknown IDs or made-up URLs are flagged by QC1. The reference list is built by code. |
| Why are the QC layers "independent"? | Each has its own prompt and system role, neither sees the other's report, QC starts on a different model from the writer, and code checks that no model can override. |
| How is the 45 minutes enforced? | Every section has minutes, code checks the sum and the reading time per section (180 words per minute), and revisions are rebalanced back to 45. |
| Why Groq and not only Gemini? | Gemini's free tier kept returning "high demand" and timeout errors while I was testing. Groq is free and fast. Gemini is kept for Google-Search grounding. |
| What if the AI fails? | A timeout on every call, automatic fallback to another model, and a failed step is saved with its error and a Retry button. Saved work is never touched. |
| What would you improve next? | Choosing videos by their transcripts, a dedicated claim-verification model, a second human reviewer workflow, and SCORM/LMS export. |

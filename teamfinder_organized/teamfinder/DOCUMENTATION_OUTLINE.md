# TeamFinder — Engineering Documentation Outline

This is a study/writing outline structured around Sommerville's *Software
Engineering* (10th ed.) chapters. It gives you the headings, what each
section should cover for **this specific project**, the key technical facts
to reference, and which Sommerville concepts each section draws on.

**Write the prose yourself.** I've left the connective tissue and analysis
out on purpose — that's the part your professor is grading. The notes
below are research/scaffolding, not a draft.

---

## Chapter 1 — Introduction

**What to cover**
- The problem you set out to solve (team formation in university courses).
- Why existing approaches fail (random assignment, friend groups, no
  visibility into peers' actual skills).
- High-level overview of your solution: verified skill profiles +
  similarity-based matching + a project discovery board.
- One paragraph of professional/ethical context: you're storing student
  data, you're using an LLM, you've disclosed both in the About page.

**Sommerville references**
- §1.1 Professional software development
- §1.3 Software engineering ethics (your About page disclosure is a
  worked example — write a sentence explaining how it satisfies the IEEE
  CS / ACM code's transparency principle)

---

## Chapter 2 — Software Processes

**What to cover**
- Which process model you used (likely an incremental / iterative model
  given you have one frontend, one backend, and built them in passes).
- Why a plan-driven (waterfall) model wouldn't fit: requirements
  evolved as you saw the frontend.
- The actual cycle you ran: requirements sketch → backend skeleton →
  frontend wiring → fix integration bugs → document.

**Sommerville references**
- §2.1 Software process models (compare waterfall, incremental, integration & configuration)
- §2.3 Coping with change — your matching algorithm is isolated in
  `matching.py` precisely so it can be swapped without touching the API
  (cite that as evidence of designing for change)

---

## Chapter 3 — Agile Software Development

**What to cover**
- Whether you ran anything resembling agile practices (probably yes:
  small commits, incremental features, no formal documentation up
  front).
- Honesty section: you were a one-person team; "agile" was really
  "iterative."

**Sommerville references**
- §3.1 Agile methods, §3.2 Agile development techniques

---

## Chapter 4 — Requirements Engineering

**What to cover** — this is one of the most important chapters; spend time here.

**Stakeholders identified**
- Students (primary users)
- Course coordinators (indirect — they assign group projects)
- The university (data custodian implications)

**User requirements (write these in plain English)**
- A student must register with an accepted email address before using
  the platform.
- A student can create and edit a profile listing major, courses,
  skills, weekly availability, GitHub URL, and a short bio.
- A student can take short multiple-choice exams that assign a
  proficiency level 0–5 per skill.
- A student can request a ranked list of compatible teammates.
- A student can browse student-posted projects and external project
  listings (GitHub / Kaggle / CTFtime).
- A student can ask an in-app advisor for guidance on skills, matches,
  and projects.

**System requirements (functional)** — translate each user requirement
into something testable. Example:
- *FR-AUTH-1:* The system shall reject registration attempts where the
  email domain is not in the configured accepted-domains set, returning
  HTTP 400.
- *FR-AUTH-2:* The system shall hash passwords with bcrypt before
  storing them.
- *FR-MATCH-1:* Given a requester's profile and N other profiles, the
  system shall return at most `top_n` matches ranked by cosine
  similarity, descending.
- *FR-EXAM-1:* On submission, the system shall compute the score as
  (correct answers / total questions) × 100 and map it to a proficiency
  level using the documented thresholds.

**Non-functional requirements**
- *Security:* passwords must never be stored in plaintext; JWTs must
  expire within 24 hours; protected endpoints must reject requests
  without a valid bearer token.
- *Portability:* the data layer must support both MySQL (production)
  and SQLite (local development) without code changes.
- *Transparency:* the use of automated/LLM systems must be disclosed
  to users.

**Sommerville references**
- §4.1 Functional and non-functional requirements
- §4.2 Requirements engineering processes (elicitation → analysis →
  validation)
- §4.5 Requirements specification — pattern your FRs after Sommerville's
  EARS or shall-statement style

---

## Chapter 5 — System Modeling

**What to cover** — draw these diagrams:

**Use case diagram**
- Actors: Unregistered Visitor, Registered Student, Advisor (external system)
- Use cases: Register, Login, Edit Profile, Take Skill Exam, Find
  Teammates, Browse Projects, Ask Advisor, View About

**Class / data model diagram**
- Entities: User, Profile, Project, Exam
- Relationships: User 1—1 Profile, User 1—* Project (as owner),
  User *—* Project (as member, via members JSON list)
- Note the trade-off: members stored as JSON list rather than a join
  table — denormalised for simplicity at the cost of query flexibility.

**Sequence diagram**
- Pick one: the "submit skill exam" flow is a good one. Show:
  Browser → POST /api/skills/exam → DB.get_exam_answers →
  scoring → DB.save_profile → response.

**Activity diagram**
- The matching flow from button click to rendered cards.

**Sommerville references**
- §5.2 Context models, §5.3 Interaction models, §5.4 Structural models,
  §5.5 Behavioral models

---

## Chapter 6 — Architectural Design

**What to cover** — this and Chapter 4 are the heart of the document.

**Architectural pattern: layered (client–server, single tier on the server side)**
- Presentation: `index.html` (browser)
- Application / API: FastAPI routes in `app.py`
- Business logic: `matching.py`, `ai_assistant.py`
- Data access: `database.py` (SQLAlchemy Core)
- Persistence: MySQL or SQLite

Draw a block diagram with arrows. Explain why layered: separation of
concerns lets you swap the persistence backend (MySQL ↔ SQLite) without
touching the API, and swap the matching algorithm without touching the
database.

**Architectural decisions to discuss explicitly**
- Why FastAPI over Flask/Django: native async, automatic OpenAPI,
  Pydantic validation.
- Why SQLAlchemy Core over an ORM: simpler for this size; portable
  upsert pattern works on both backends.
- Why JWT over server-side sessions: stateless, easy to scale, no
  session storage needed.
- Why a single HTML file: the project is small enough that a SPA
  framework would be more weight than it's worth.

**Sommerville references**
- §6.2 Architectural patterns (specifically the client-server and
  layered architecture patterns)
- §6.3 Application architectures — Sommerville's "transaction
  processing" and "information systems" archetypes both partly apply

---

## Chapter 7 — Design and Implementation

**What to cover**

**Object-oriented design**
- The Database class as a facade over SQLAlchemy Core.
- Pydantic models as immutable data transfer objects.

**Design patterns observed in the code**
- *Facade:* `Database` hides SQLAlchemy specifics.
- *Strategy:* `ai_assistant.py` — the LLM call is one strategy, the
  rule-based fallback is another, selected at runtime.
- *Repository:* `Database` methods (`get_user_by_email`, `save_profile`)
  mirror the repository pattern.

**Implementation notes worth discussing**
- The portable upsert: rather than using MySQL's `ON DUPLICATE KEY
  UPDATE` or SQLite's `ON CONFLICT`, the code does a `SELECT` followed
  by either `INSERT` or `UPDATE` in a transaction. Cite this as a
  deliberate trade-off: slightly more queries, but the same code runs
  on both engines.
- JSON columns: `courses`, `skills`, `members`, and `skills_required`
  are stored as JSON text rather than join tables. Trade-off: simpler
  schema, but you can't `WHERE` on individual list elements at the SQL
  level.

**Sommerville references**
- §7.1 Object-oriented design using the UML
- §7.2 Design patterns
- §7.3 Implementation issues (reuse, configuration management, host-target)

---

## Chapter 8 — Software Testing

**What to cover**

You probably haven't written formal tests. **Don't pretend you have.**
Instead:

- Describe the manual test plan you'd run end-to-end (register → log
  in → fill profile → take exam → see matches → ask advisor → log out).
- Sketch what unit tests would look like for `matching.py` (cosine
  similarity is purely functional, easy to test):
  - identical vectors → score 1.0
  - orthogonal vectors → score 0.0
  - one zero vector → score 0.0 (guard against division by zero)
- Describe one defect you found and fixed (e.g. the const-reassignment
  bug, the exam answer-format mismatch). Defect reports are a
  Sommerville-aligned artifact.

**Sommerville references**
- §8.1 Development testing (unit, component, system)
- §8.2 Test-driven development (write a sentence on why you didn't use
  it and what that cost you)
- §8.3 Release testing

---

## Chapter 9 — Software Evolution

**What to cover**
- The matching algorithm is in its own module precisely so it can be
  replaced (e.g. swap cosine for Jaccard, or for a learned embedding)
  without touching the API.
- The data layer is portable between two backends — that's a future-
  proofing decision.
- A few concrete evolution candidates: real-time notifications when a
  match accepts a connect request, OAuth login (replace the email/
  password flow), a proper join table for project membership.

**Sommerville references**
- §9.1 Evolution processes
- §9.4 Software reengineering — the "replace cosine with a learned
  model" path is a textbook reengineering scenario

---

## Chapter 24 — Quality Management *(optional but recommended)*

**What to cover**
- ISO 9001 / ISO/IEC 25010 quality characteristics that apply:
  functional suitability, security, maintainability, portability.
- How you addressed each: parameterised SQL via SQLAlchemy
  (security – injection-resistant), the dual-backend data layer
  (portability), the modular structure (maintainability).

---

## Appendix: Technical Facts You Will Need

**Languages and runtime**
- Python 3.10+
- HTML5 / CSS3 / vanilla JavaScript (ES2020)

**Backend libraries (versions from `requirements.txt`)**
- fastapi 0.111.0 — web framework
- uvicorn 0.29.0 — ASGI server
- pydantic 2.7.1 — validation
- sqlalchemy 2.0.30 — SQL toolkit (Core, not ORM)
- pymysql 1.1.1 — MySQL driver
- bcrypt 4.1.3 — password hashing
- pyjwt 2.8.0 — JWT encoding/decoding
- python-dotenv 1.0.1 — `.env` loader
- anthropic 0.25.6 — language-model client (optional)

**Advisor model**
- When an `ANTHROPIC_API_KEY` is configured, the in-app Advisor uses
  Anthropic's Claude (default model `claude-sonnet-4-20250514`, set via
  the `ADVISOR_MODEL` env var). When no key is set, a deterministic
  rule-based fallback in `ai_assistant.py::_fallback` handles requests.

**Database schema (4 tables)**
- `users` — `email` PK, `full_name`, `password_hash`, `profile_complete`, `created_at`
- `profiles` — `user_id` PK/FK, `major`, `courses` (JSON), `skills` (JSON),
  `availability_hours`, `github_url`, `bio`, `updated_at`
- `projects` — `id` PK, `title`, `description`, `skills_required` (JSON),
  `owner_id` FK, `source`, `created_at`, `members` (JSON)
- `exams` — `skill_name` PK, `questions` (JSON), `answers` (JSON)

**Auth**
- bcrypt for password hashing (work factor = library default)
- JWT (HS256) signed with `SECRET_KEY` env var; 24-hour expiry
- Bearer token in `Authorization` header on every protected endpoint
- Auth gate enforced both client-side (route guard in `showPage`) and
  server-side (`Depends(get_current_user)` on every protected route)

**Matching algorithm**
- Cosine similarity over skill vectors
- Skill universe = union of all skills across all profiles
- Each profile's vector is the proficiency level (0–5) at each skill,
  zero for absent skills
- Availability bonus: 0.05 × (1 − |h_a − h_b| / max(h_a, h_b))
- Final score = min(1.0, cosine + availability_bonus)
- Top-N returned, sorted descending

**Exam scoring thresholds**
- 0–20% → Level 0
- 21–40% → Level 1
- 41–60% → Level 2
- 61–70% → Level 3
- 71–85% → Level 4
- 86–100% → Level 5

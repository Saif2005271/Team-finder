# Team-Finder — Complete Project Analysis & Code Explanation
## Software Engineering Course 1902372 | Spring 2025/2026

---

## PART A — PROJECT ANALYSIS

### 1. What is Team-Finder?

Team-Finder is a **university collaboration platform** that solves a very real problem:
students waste enormous time finding suitable teammates for group projects because the
current process relies on personal friendships and random assignment — not actual skills.

The platform creates **verified, structured student profiles** and uses a **cosine
similarity algorithm** to compute a compatibility score between every pair of students.
An AI assistant (powered by Claude) guides users through the platform.

---

### 2. Key Problems Addressed

| Problem | Solution in Team-Finder |
|---|---|
| No visibility into peers' real skills | Structured profiles with course-unlocked skills |
| Self-reported skills are untrustworthy | Exam-based verification → proficiency level 0–5 |
| Random team formation | Cosine similarity matching algorithm |
| No exposure to real-world projects | GuideMe panel (GitHub, Kaggle, CTFtime) |
| No centralised collaboration hub | Single web platform for all academic collaboration |

---

### 3. System Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    CLIENT (Browser)                           │
│     HTML + CSS + JavaScript (index.html)                     │
│  Pages: Home │ Matches │ Projects │ AI Chat │ Profile │ Auth │
└──────────────────────┬───────────────────────────────────────┘
                       │ HTTP / REST API calls (fetch)
                       ▼
┌──────────────────────────────────────────────────────────────┐
│              FASTAPI BACKEND (Python)                         │
│  app.py — route definitions, JWT middleware                   │
│  models.py — Pydantic request/response schemas                │
│  matching.py — cosine similarity algorithm                    │
│  ai_assistant.py — Claude API integration                     │
│  database.py — data access layer (swap for Supabase)         │
└──────────────────────┬───────────────────────────────────────┘
                       │
          ┌────────────┴────────────┐
          ▼                         ▼
┌─────────────────┐       ┌────────────────────┐
│  Supabase DB    │       │  Anthropic Claude   │
│  (PostgreSQL)   │       │  API (AI Assistant) │
└─────────────────┘       └────────────────────┘
```

---

### 4. The Matching Algorithm — Cosine Similarity

This is the **mathematical core** of the system. Here's how it works:

**Step 1 — Skill Vectors**
Every student's skills are encoded as a numerical vector. Given the system knows 4
skills {Python, React, SQL, ML}:

- Alice: Python=4, React=0, SQL=2, ML=3 → vector [4, 0, 2, 3]
- Bob:   Python=3, React=4, SQL=0, ML=1 → vector [3, 4, 0, 1]

**Step 2 — Cosine Similarity Formula**

```
              A · B          (dot product)
cos(A,B) = ─────────── = ────────────────────
            |A| × |B|    (product of magnitudes)
```

```
A · B  = (4×3) + (0×4) + (2×0) + (3×1) = 12 + 0 + 0 + 3 = 15
|A|    = √(16 + 0 + 4 + 9) = √29 ≈ 5.39
|B|    = √(9 + 16 + 0 + 1) = √26 ≈ 5.10
score  = 15 / (5.39 × 5.10) ≈ 0.545 = 54.5%
```

**Why cosine and not Euclidean distance?**
Cosine is magnitude-invariant — it measures the *angle* between vectors, not their
length. A student with Python=2 and one with Python=4 are still "aligned" in the
Python direction; they just differ in depth. Euclidean distance would incorrectly
penalise this.

---

### 5. Security Design

| Layer | Mechanism |
|---|---|
| Authentication | JWT tokens (signed with HS256, expiry 24h) |
| Registration | University email domain validation |
| Password storage | Hashed (bcrypt in production) |
| API access | Bearer token required on all protected routes |
| Data access | Row-Level Security (RLS) in Supabase |
| Sensitive data | Beneficiary info accessible only to authorised roles |

---

## PART B — CODE EXPLANATION

---

### FILE 1: app.py — The FastAPI Application

**What it is:** The main entry point of the backend. It defines all HTTP routes (URLs
the frontend calls), sets up middleware (CORS, authentication), and wires together all
the other modules.

**Key concepts used:**

```python
app = FastAPI(...)
```
Creates the application. FastAPI automatically generates OpenAPI documentation at
`/docs` — you can test every endpoint in your browser.

```python
app.add_middleware(CORSMiddleware, allow_origins=["*"], ...)
```
Cross-Origin Resource Sharing: allows the HTML frontend (on a different port/domain)
to call the API. In production, replace `"*"` with your actual frontend URL.

```python
security = HTTPBearer()
def get_current_user(credentials = Depends(security)):
    return decode_jwt(credentials.credentials)
```
`Depends(...)` is FastAPI's dependency injection. Any route that uses
`user=Depends(get_current_user)` will automatically:
1. Read the `Authorization: Bearer <token>` header.
2. Decode and validate the JWT.
3. Raise a 401 error if invalid.
4. Pass the decoded user data into the route function.

```python
@app.post("/api/auth/register", response_model=TokenResponse)
def register(data: UserRegister):
```
The `@app.post(...)` decorator registers this function as the handler for
`POST /api/auth/register`. `response_model=TokenResponse` tells FastAPI to validate
the response against the `TokenResponse` Pydantic schema before sending it.

**JWT Flow:**
1. User registers → server creates a JWT containing `{sub: user_id, email, exp}`.
2. JWT is signed with `SECRET_KEY` using HS256 algorithm.
3. Client stores the JWT and sends it in every subsequent request.
4. Server decodes the JWT to identify the user — no session storage needed.

---

### FILE 2: models.py — Pydantic Schemas

**What it is:** Defines all the data shapes used by the API. Pydantic validates
incoming JSON automatically and raises clear error messages for invalid data.

```python
class UserRegister(BaseModel):
    email: str = Field(..., example="student@ju.edu.jo")
    password: str = Field(..., min_length=8)
    full_name: str = Field(..., min_length=2)
```

When FastAPI receives a POST to `/api/auth/register`, it automatically:
1. Parses the JSON body.
2. Validates each field (email is a string, password is at least 8 chars, etc.).
3. Returns a 422 Unprocessable Entity with detailed errors if validation fails.
4. Injects the validated `UserRegister` object into the route function.

The `Field(...)` call sets metadata: `...` means required, `min_length` sets a
minimum, `example` appears in the OpenAPI documentation.

**Why separate models?** Different operations need different data. A `ProfileCreate`
has all required fields, while `ProfileUpdate` has all optional fields (you only send
what you want to change). Using separate models makes this explicit and safe.

---

### FILE 3: matching.py — The Cosine Similarity Engine

**What it is:** A pure algorithmic module that computes compatibility scores. It has
no FastAPI imports — it can be unit-tested independently.

```python
def build_skill_vector(skills: Dict[str, int], all_skills: List[str]) -> List[float]:
    return [float(skills.get(skill, 0)) for skill in all_skills]
```
This is a **list comprehension** that converts a skill dict into a fixed-length vector.
`skills.get(skill, 0)` returns the proficiency for the skill, or 0 if the student
hasn't listed it. The resulting list is aligned to the global skill universe.

```python
def cosine_similarity(vec_a, vec_b):
    dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
    magnitude_a = math.sqrt(sum(a**2 for a in vec_a))
    magnitude_b = math.sqrt(sum(b**2 for b in vec_b))
    if magnitude_a == 0.0 or magnitude_b == 0.0:
        return 0.0
    return min(1.0, dot_product / (magnitude_a * magnitude_b))
```
Direct implementation of the cosine formula. The `min(1.0, ...)` guard prevents
floating-point arithmetic from occasionally returning 1.0000000001.

```python
def compute_match_scores(my_profile, other_profiles, top_n=10):
    all_skills = set()
    for profile in [my_profile] + other_profiles:
        all_skills.update(profile.get("skills", {}).keys())
    all_skills_list = sorted(all_skills)  # deterministic ordering
    ...
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:top_n]
```
**Step by step:**
1. Build the global skill universe (union of all students' skills).
2. Sort it so every vector has the same dimension ordering.
3. For each candidate, compute cosine + availability bonus.
4. Sort results descending by score.
5. Return only the top N.

`lambda x: x["score"]` is an anonymous function used as the sort key —
`sort(reverse=True)` means descending order (best match first).

---

### FILE 4: database.py — Data Access Layer

**What it is:** An in-memory data store for the prototype. Every method is designed to
mirror what a real Supabase/PostgreSQL query would look like, so swapping the
implementation is a one-file change.

```python
class InMemoryDatabase:
    def __init__(self):
        self._users: Dict[str, dict] = {}
        self._profiles: Dict[str, dict] = {}
        self._projects: List[dict] = []
```
Python type hints (`Dict[str, dict]`) make the code self-documenting and enable IDE
autocomplete. The `_` prefix indicates these are private (internal) attributes.

```python
def get_all_profiles(self, exclude_user_id=None):
    results = []
    for uid, profile in self._profiles.items():
        if uid == exclude_user_id: continue
        enriched = dict(profile)          # shallow copy so we don't mutate the stored record
        user = self._users.get(uid, {})
        enriched["full_name"] = user.get("full_name", "Unknown")
        results.append(enriched)
    return results
```
This joins profile and user data (like a SQL JOIN) to include the display name in
match results — without exposing the raw user record (which contains the password hash).

The `seed()` method populates realistic demo data on startup, making the API instantly
usable without needing a real database.

---

### FILE 5: ai_assistant.py — Claude Integration

**What it is:** Wraps the Anthropic Claude API to power the in-app assistant. Contains
a rule-based fallback so the UI never breaks if the API key is absent.

```python
def _build_system_prompt(profile):
    base = "You are the Team-Finder AI Assistant..."
    if not profile:
        return base
    skills_summary = ", ".join(f"{s} (Lv.{l})" for s, l in profile["skills"].items())
    return base + f"\n\nCurrent student profile:\n  Skills: {skills_summary}\n..."
```
The **system prompt** gives Claude its persona and injects the student's current
profile. This makes responses contextual — Claude knows which skills the student has
and can give specific advice rather than generic answers.

```python
def _trim_history(history):
    return history[-MAX_HISTORY_TURNS:]
```
**Cost control:** Only the last 6 turns are sent to the API. This limits token usage
(and therefore cost) while preserving enough context for coherent conversation.

```python
response = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=400,
    system=_build_system_prompt(profile),
    messages=messages
)
return response.content[0].text
```
`max_tokens=400` limits response length — shorter answers are faster and cheaper.
`response.content[0].text` extracts the text from the first content block.

---

### FILE 6: index.html — The Complete Frontend

**What it is:** A single-file web application with all HTML structure, CSS styling,
and JavaScript logic. Runs in any browser — no build step required.

**CSS Architecture:**

```css
:root {
  --bg: #0a0c14;
  --accent: #4f6ef7;
  --teal: #14b8a6;
  ...
}
```
CSS custom properties (variables) enable a consistent dark theme. Changing `--accent`
in one place updates every button, highlight, and glow across the entire page.

```css
.page { display: none; }
.page.active { display: block; animation: fadeUp .4s ease; }
```
The SPA (Single Page Application) routing system. JavaScript toggles the `active`
class to show/hide pages with a smooth animation. No full-page reloads.

**JavaScript Architecture:**

```javascript
const state = { currentPage:'home', loggedIn:false, user:null };
```
A global state object holds the application's current data. All functions read from
and write to this object.

```javascript
function showPage(name) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.getElementById('page-' + name).classList.add('active');
  if (name === 'match')    renderMatches();
  if (name === 'projects') renderProjects('all');
}
```
Navigation: hide all pages, show the target page, and trigger any data-loading for
that page. `querySelectorAll` + `forEach` replaces the need for jQuery.

```javascript
function matchCard(m) {
  const circ   = 2 * Math.PI * 20;           // SVG circle circumference
  const offset = circ - (m.score * circ);    // dash offset creates the arc
  return `<div class="match-card">...
    <circle stroke-dasharray="${circ}" stroke-dashoffset="${offset}"/>
  ...</div>`;
}
```
The SVG score ring is a circle with `stroke-dasharray` (total dash length = circumference)
and `stroke-dashoffset` (how much to offset = the unfilled part). This creates a
precise progress arc with no external library.

```javascript
function cosineSimFrontend(vecA, vecB) {
  const dot = vecA.reduce((sum, a, i) => sum + a * vecB[i], 0);
  const magA = Math.sqrt(vecA.reduce((sum, a) => sum + a*a, 0));
  const magB = Math.sqrt(vecB.reduce((sum, b) => sum + b*b, 0));
  return magA && magB ? dot / (magA * magB) : 0;
}
```
The same algorithm in JavaScript — shows how the same mathematical concept translates
between Python and JS.

---

## PART C — HOW TO RUN THE PROJECT

### Backend

```bash
# 1. Navigate to the backend folder
cd teamfinder/backend

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. (Optional) Set your Anthropic API key
export ANTHROPIC_API_KEY="your_key_here"

# 4. Start the server
uvicorn app:app --reload --port 8000

# 5. Open API documentation
# Visit: http://localhost:8000/docs
```

### Frontend

```bash
# Simply open the file in any browser — no server required
open teamfinder/frontend/index.html

# Or serve it with Python's built-in server:
cd teamfinder/frontend
python -m http.server 3000
# Visit: http://localhost:3000
```

---

## PART D — API ENDPOINTS SUMMARY

| Method | Endpoint | Description | Auth Required |
|---|---|---|---|
| POST | /api/auth/register | Register a new user | No |
| POST | /api/auth/login | Login and get JWT | No |
| POST | /api/profile | Create/replace profile | Yes |
| GET  | /api/profile/{id} | Get a user's profile | Yes |
| PATCH| /api/profile | Update partial profile | Yes |
| GET  | /api/skills/exam/{skill} | Get exam questions | Yes |
| POST | /api/skills/exam | Submit exam answers | Yes |
| POST | /api/match | Get top-N matches | Yes |
| GET  | /api/projects | List projects | Yes |
| POST | /api/projects | Create project | Yes |
| POST | /api/ai/chat | Chat with AI assistant | Yes |
| GET  | /api/health | Health check | No |

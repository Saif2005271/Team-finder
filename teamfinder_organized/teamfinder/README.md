# TeamFinder

A university team-matching platform. Students create accounts, fill out a
skill profile, take short verification exams, and get matched with
compatible teammates using cosine similarity over skill vectors.

## Stack

- **Backend:** FastAPI (Python 3.10+)
- **Database:** MySQL via SQLAlchemy + PyMySQL (production), or SQLite (local testing)
- **Auth:** JWT (PyJWT) + bcrypt-hashed passwords
- **Frontend:** Single-page `index.html` (vanilla HTML/CSS/JS), served by FastAPI

## Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Edit .env if you want to switch to MySQL or set ANTHROPIC_API_KEY for
# the language-model-backed advisor. Defaults are fine for local testing.

# 3. Run the server
uvicorn backend.app:app --reload
```

The server runs on `http://127.0.0.1:8000`. Open it in your browser and
you'll get the login page — register an account to access the rest of the
platform.

## Database

By default, the app uses **SQLite** (`./teamfinder.db`, created on first
run) so you can get going without installing a database server.

For **MySQL**, edit `.env`:

```
DB_BACKEND=mysql
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=yourpassword
DB_NAME=teamfinder
```

Then create the database (the app creates tables on first run):

```sql
CREATE DATABASE teamfinder CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

## Demo accounts

The first time the server starts on an empty database it seeds four demo
users — `sara@ju.edu.jo`, `omar@ju.edu.jo`, `lina@ju.edu.jo`,
`rami@ju.edu.jo` — all with the password `demo1234`. Use them to see
matches populate immediately.

## Project layout

```
backend/          Application + API (FastAPI)
  app.py            Routes: auth, profile, matching, projects, advisor
  models.py         Pydantic request/response models
  matching.py       Cosine-similarity matching algorithm
  ai_assistant.py   Advisor backend (LLM-backed with rule-based fallback)
database/         Persistence layer
  database.py       SQLAlchemy schema + portable data-access layer (MySQL / SQLite)
frontend/         User interface
  index.html        Single-page app (served by FastAPI at /)
  styles.css        Stylesheet (source)
  script.js         Client logic (source)
  logo.png          Logo asset
requirements.txt  Python dependencies
.env.example      Configuration template
```

Run from the project root so the `backend` and `database` packages resolve:
`uvicorn backend.app:app --reload`.

## How matching works

Each student's skills are encoded as a vector aligned to the global set
of known skills. For example, given the universe `[Python, React, SQL, ML]`:

- Alice (Python 4, SQL 2, ML 3) → `[4, 0, 2, 3]`
- Bob   (Python 3, React 4, ML 1) → `[3, 4, 0, 1]`

Their compatibility is the cosine of the angle between the two vectors:

    cos(A, B) = (A · B) / (|A| × |B|)

A score of 1.0 is perfect overlap; 0.0 is fully disjoint. A small
additive bonus (up to 0.05) is applied for similar weekly availability,
nudging the score toward pairs who can actually meet.

## Automated systems disclosure

See the in-app **About** page. Briefly: the matching algorithm is
deterministic and does not learn from user data. The in-app **Advisor**
chat generates replies using a large language model (Anthropic Claude)
when an API key is set, and a built-in rule-based fallback otherwise.

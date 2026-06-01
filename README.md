[README.md](https://github.com/user-attachments/files/28475190/README.md)
# Team-Finder

> Skill-based team formation platform for university students — matches collaborators on verified skills and availability rather than personal acquaintance.

Team-Finder is a web platform that helps students assemble effective project teams. Instead of relying on who already knows whom, it lets students build profiles around their actual skills and availability, then uses a cosine-similarity matching engine to suggest collaborators whose strengths complement one another. It was built as a full-stack project for a software engineering course at the University of Jordan.

## The Problem

Group projects are a familiar pain point: the team you end up with is rarely the team best suited to the work, because nobody has visibility into who in the class actually holds the skills the project needs. Team-Finder makes that information visible and actionable.

## Features

- **Profiles with verified skills** — each student lists their major, completed courses, skills (rated 0–5), weekly availability in hours, and an optional bio and GitHub link.
- **Skill-verification exams** — a testing subsystem that validates declared skills rather than taking them at face value.
- **Cosine-similarity matching engine** — pairs students with complementary collaborators based on the skill space, isolated in its own module so it can be tested and swapped independently of the API.
- **Projects board** — students can post and browse projects to join.
- **Advisor chat** — an assistant that helps users improve their profiles, understand their match scores, and find projects to join, backed by an LLM API with a deterministic rule-based fallback when no API key is configured.
- **Authentication & profile management** — account creation and profile editing.

## Tech Stack

- **Backend:** FastAPI (Python)
- **Persistence:** SQLAlchemy Core data-access layer targeting **MySQL** in production and **SQLite** for local development and testing — the same application code runs unchanged against either backend.
- **Matching:** cosine similarity over the skill vector space (`matching.py`)
- **Advisor:** optional LLM API integration with a rule-based fallback
- **Frontend:** HTML/CSS/JS

## Architecture

The persistence layer is portable across MySQL and SQLite so the project can be developed and tested locally without external infrastructure. The matching engine is isolated in its own module so it can be unit-tested independently of the HTTP surface and replaced in future iterations without changing the API contract. The advisor's rule-based fallback keeps the system fully functional even without an LLM API key.

## Getting Started

> Adjust the commands below to match your repository's actual entry points and dependency files.

```bash
# Clone the repository
git clone https://github.com/<your-username>/team-finder.git
cd team-finder

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate    # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the development server (uses SQLite by default)
uvicorn app.main:app --reload
```

### Configuration

For production with MySQL, set the database connection string via an environment variable (e.g. `DATABASE_URL`). To enable the LLM-powered advisor, provide your API key via the appropriate environment variable; without it, the advisor falls back to its rule-based responses.

## Project Status

Built as a course project. The full-stack implementation covers both the mandatory frontend and the optional backend.

## Authors

- Saif Salim Ibrahim Indrawes
- Nour Al-Bustanjee
- Khaled Saadeh

## License

Add a license of your choice (e.g. MIT) if you intend to make this repository public.

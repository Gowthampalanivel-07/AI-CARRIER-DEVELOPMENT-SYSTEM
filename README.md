# AI Placement & Career Development (Animated Demo)

This is a complete Python web app (FastAPI + Jinja templates) that provides:
- AI-powered placement/career guidance via `POST /api/assess`
- Unified AI brain via `POST /api/unified-insights` (dashboard + insights + jobs + learning)
- Context-aware assistant endpoint via `POST /api/assistant`
- A modern, animation-rich UI (glassmorphism, micro-interactions, scroll animations, skeletons, morphing transitions)

## Run locally

1. Create and activate a virtual environment
   - PowerShell:
     - `python -m venv .venv`
     - `.\.venv\Scripts\Activate.ps1`
2. Install deps
   - `pip install -r requirements.txt`
3. Start the server
   - `uvicorn app.main:app --reload --port 8000`
4. Open: `http://localhost:8000`

## Environment variables

Create a file named `.env` in the project root (see `.env.example` for keys).

If `OPENAI_API_KEY` is set, the backend will attempt to call OpenAI for richer recommendations.
Otherwise it uses a deterministic rule-based fallback (so the UI still works end-to-end).

## New v1 modules included

- Student Dashboard (smart profile, career score, growth tracker, timeline)
- AI Insights (skill gap analysis, career path predictor, salary simulation, next best action)
- Smart Job Portal (AI job matching + confidence)
- Learning Hub (course recommendations + micro-learning roadmap)
- AI Chat Assistant (career Q&A / resume / interview prompts)

## Phase 2 features included

- Real resume upload endpoint with spaCy pipeline fallback:
  - `POST /api/resume/upload` (`multipart/form-data`: `file`, `user_key`)
  - Supports true extraction for `.pdf` (via `pypdf`) and `.docx` (via `python-docx`), with fallback parsing for other text types.
- Auth-based user IDs:
  - `POST /api/auth/register`
  - `POST /api/auth/login`
  - Bearer token (`Authorization: Bearer <token>`) links activity and personalization to real user IDs.
- Persistent user activity tracking:
  - `POST /api/activity`
  - `GET /api/activity/{user_key}/summary`
- Real dataset ingestion endpoints (CSV/JSON):
  - `POST /api/datasets/ingest` (`multipart/form-data`: `kind=jobs|courses`, `source`, `file`)
- Personalization engine:
  - Click behavior (job/course/skill interactions) is stored in DB and used to adapt ranking and recommendations in `POST /api/unified-insights`.
- Background retraining jobs:
  - `POST /api/retrain/start`
  - `GET /api/retrain/status`
  - Builds global skill-weight signals from activity events for stronger long-term recommendation biasing.

## Dataset format (minimum columns)

- Jobs CSV/JSON:
  - `id`, `title`, `company`, `location`, `salary_lpa`, `skills`, `description`
  - `skills` can be comma-separated text (`"react,css,js"`) or JSON array.
- Courses CSV/JSON:
  - `id`, `title`, `provider`, `skills`

## spaCy note

The app will use `en_core_web_sm` automatically if installed. If unavailable, it falls back to a lightweight parser so the feature still works.

Install the model (optional but recommended):
- `python -m spacy download en_core_web_sm`


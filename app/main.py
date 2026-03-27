from __future__ import annotations

import os
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

import httpx
from dotenv import load_dotenv
from fastapi import BackgroundTasks, Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

load_dotenv()

from .ai import assess_profile
from .db import ENGINE, SessionLocal, get_db
from .intelligence import build_unified_insights, parse_resume_with_spacy
from .models import ActivityEvent, Base, DatasetCourse, DatasetJob, PersonalizationModel, Submission, UserAccount
from .schemas import (
    ActivityEventRequest,
    AssessResponse,
    AuthResponse,
    ChatRequest,
    ChatResponse,
    DatasetIngestResponse,
    LoginRequest,
    ProfileInput,
    RegisterRequest,
    UnifiedInsightsRequest,
)

app = FastAPI(title="AI Placement & Career Development")
security = HTTPBearer(auto_error=False)
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-me")
JWT_ALG = "HS256"
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))

templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.on_event("startup")
def on_startup() -> None:
    # Ensure DB schema exists.
    Base.metadata.create_all(bind=ENGINE)


def _hash_password(password: str) -> str:
    return pwd_context.hash(password)


def _verify_password(password: str, hashed: str) -> bool:
    return pwd_context.verify(password, hashed)


def _create_access_token(user_id: str, email: str) -> str:
    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=JWT_EXPIRE_MINUTES)
    payload = {"sub": user_id, "email": email, "iat": int(now.timestamp()), "exp": int(exp.timestamp())}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


def _resolve_user_id(
    credentials: HTTPAuthorizationCredentials | None,
    fallback_user_key: str | None = None,
) -> str:
    if credentials and credentials.scheme.lower() == "bearer":
        token = credentials.credentials
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
            sub = str(payload.get("sub", "")).strip()
            if sub:
                return sub
        except JWTError:
            pass
    return (fallback_user_key or "anonymous").strip().lower()


async def _openai_json(system_prompt: str, user_payload: Dict[str, Any]) -> Dict[str, Any] | None:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return None
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini"
    payload = {
        "model": model,
        "temperature": 0.3,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
        ],
    }
    headers = {"Authorization": f"Bearer {api_key}"}
    async with httpx.AsyncClient(timeout=45) as client:
        r = await client.post("https://api.openai.com/v1/chat/completions", json=payload, headers=headers)
        r.raise_for_status()
        content = r.json()["choices"][0]["message"]["content"]
    return json.loads(content)


async def _openai_text(system_prompt: str, user_text: str) -> str | None:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return None
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini"
    payload = {
        "model": model,
        "temperature": 0.4,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text},
        ],
    }
    headers = {"Authorization": f"Bearer {api_key}"}
    async with httpx.AsyncClient(timeout=45) as client:
        r = await client.post("https://api.openai.com/v1/chat/completions", json=payload, headers=headers)
        r.raise_for_status()
        return str(r.json()["choices"][0]["message"]["content"]).strip()


@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "app_name": "AI Placement & Career Development",
        },
    )


@app.post("/api/auth/register", response_model=AuthResponse)
def api_register(payload: RegisterRequest, db=Depends(get_db)) -> AuthResponse:
    email = payload.email.strip().lower()
    exists = db.query(UserAccount).filter(UserAccount.email == email).first()
    if exists:
        raise HTTPException(status_code=409, detail="Email already registered.")
    user = UserAccount(email=email, full_name=payload.full_name, password_hash=_hash_password(payload.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    token = _create_access_token(str(user.id), user.email)
    return AuthResponse(access_token=token, user_id=str(user.id), email=user.email)


@app.post("/api/auth/login", response_model=AuthResponse)
def api_login(payload: LoginRequest, db=Depends(get_db)) -> AuthResponse:
    email = payload.email.strip().lower()
    user = db.query(UserAccount).filter(UserAccount.email == email).first()
    if not user or not _verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials.")
    token = _create_access_token(str(user.id), user.email)
    return AuthResponse(access_token=token, user_id=str(user.id), email=user.email)


@app.post("/api/assess", response_model=AssessResponse)
async def api_assess(payload: ProfileInput, db=Depends(get_db)) -> AssessResponse:
    try:
        result = await assess_profile(payload)
        submission = Submission(
            name=payload.name,
            email=str(payload.email) if payload.email else None,
            raw_input_json=Submission.dumps(payload.model_dump()),
            output_json=Submission.dumps(result.model_dump(exclude={"submission_id"})),
        )
        db.add(submission)
        db.commit()
        db.refresh(submission)

        # Fill id for the response.
        result.submission_id = submission.id
        result.ai_notes = str(result.ai_notes)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Assessment failed: {e}")


@app.get("/api/submissions/{submission_id}", response_model=Dict[str, Any])
def api_submission(submission_id: int, db=Depends(get_db)) -> Dict[str, Any]:
    submission = db.get(Submission, submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    output = submission.loads(submission.output_json)
    output["submission_id"] = submission.id
    output["created_at"] = submission.created_at.isoformat()
    return output


@app.get("/api/health")
def health() -> Dict[str, str]:
    return {"status": "ok", "pid": str(os.getpid())}


@app.post("/api/unified-insights")
async def api_unified_insights(
    payload: UnifiedInsightsRequest,
    db=Depends(get_db),
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> Dict[str, Any]:
    try:
        user_key = _resolve_user_id(
            credentials,
            fallback_user_key=(payload.user_key or payload.profile.email or payload.profile.name),
        )
        result = build_unified_insights(payload.profile, payload.resume_text, db=db, user_key=user_key)

        # LLM enrichment layer for all dashboard modules.
        try:
            enrich = await _openai_json(
                "You are an expert career mentor. Improve recommendations quality. Return only JSON matching the requested structure.",
                {
                    "profile": {
                        "target_role": payload.profile.target_role,
                        "experience_years": payload.profile.experience_years,
                        "skills": payload.profile.skills,
                        "interests": payload.profile.interests,
                    },
                    "current_output": result,
                    "required_json": {
                        "insights": {
                            "next_best_action": "string",
                            "skill_gap_analysis": [{"skill": "string", "importance": "number"}],
                            "career_path_predictor": [{"path": "string", "timeline": "string", "expected_salary_lpa": "number"}],
                            "salary_insights": [{"scenario": "string", "salary_projection_lpa": "number"}],
                        },
                        "jobs": {"notifications": ["string"]},
                        "learning": {"dynamic_roadmap": [{"day": "string", "task": "string"}]},
                    },
                },
            )
            if enrich:
                if isinstance(enrich.get("insights"), dict):
                    result["insights"].update(enrich["insights"])
                if isinstance(enrich.get("jobs"), dict) and isinstance(enrich["jobs"].get("notifications"), list):
                    result["jobs"]["notifications"] = enrich["jobs"]["notifications"]
                if isinstance(enrich.get("learning"), dict) and isinstance(enrich["learning"].get("dynamic_roadmap"), list):
                    result["learning"]["dynamic_roadmap"] = enrich["learning"]["dynamic_roadmap"]
        except Exception:
            pass

        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unified insights failed: {e}")


@app.post("/api/assistant", response_model=ChatResponse)
async def api_assistant(payload: ChatRequest) -> ChatResponse:
    # OpenAI-first assistant with robust fallback.
    try:
        ai_reply = await _openai_text(
            "You are a concise career coach for students. Give specific, actionable guidance.",
            json.dumps(
                {
                    "profile": payload.profile.model_dump(),
                    "question": payload.message,
                    "style": "clear, actionable, 6-10 lines max",
                },
                ensure_ascii=False,
            ),
        )
        if ai_reply:
            return ChatResponse(reply=ai_reply)
    except Exception:
        pass

    # Fallback if OpenAI is unavailable.
    skills = ", ".join(payload.profile.skills[:6])
    role = payload.profile.target_role
    reply = (
        f"For {role}, prioritize one core gap, build one mini-project, then apply to 3 suitable roles this week. "
        f"Highlight these skills in your resume: {skills}."
    )
    return ChatResponse(reply=reply)


def _decode_uploaded_resume(file: UploadFile, content: bytes) -> str:
    filename = (file.filename or "").lower()
    # True parser path for common resume file types.
    if filename.endswith(".pdf"):
        try:
            from io import BytesIO
            from pypdf import PdfReader

            reader = PdfReader(BytesIO(content))
            parts = [page.extract_text() or "" for page in reader.pages]
            return "\n".join(parts).strip()
        except Exception:
            pass
    if filename.endswith(".docx"):
        try:
            from io import BytesIO
            from docx import Document

            doc = Document(BytesIO(content))
            parts = [p.text for p in doc.paragraphs if p.text]
            return "\n".join(parts).strip()
        except Exception:
            pass
    if filename.endswith(".doc"):
        # Legacy .doc is binary; decode fallback for partial text recovery.
        return content.decode("latin-1", errors="ignore")
    # Text-based fallback.
    if filename.endswith((".txt", ".md", ".csv", ".json", ".py", ".html")):
        return content.decode("utf-8", errors="ignore")
    # Generic binary fallback.
    return content.decode("utf-8", errors="ignore")


@app.post("/api/resume/upload")
async def api_resume_upload(
    file: UploadFile = File(...),
    user_key: str = Form("anonymous"),
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> Dict[str, Any]:
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    resume_text = _decode_uploaded_resume(file, content)
    parsed = parse_resume_with_spacy(resume_text)
    parsed["user_key"] = _resolve_user_id(credentials, fallback_user_key=user_key)
    parsed["filename"] = file.filename or "resume"
    return parsed


@app.post("/api/activity")
def api_track_activity(
    payload: ActivityEventRequest,
    db=Depends(get_db),
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> Dict[str, Any]:
    try:
        resolved_user_key = _resolve_user_id(credentials, fallback_user_key=payload.user_key)
        row = ActivityEvent(
            user_key=resolved_user_key,
            event_type=payload.event_type,
            entity_type=payload.entity_type,
            entity_id=payload.entity_id,
            metadata_json=json.dumps(payload.metadata, ensure_ascii=False),
        )
        db.add(row)
        db.commit()
        return {"status": "ok", "event_id": row.id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Track activity failed: {e}")


@app.get("/api/activity/{user_key}/summary")
def api_activity_summary(user_key: str, db=Depends(get_db)) -> Dict[str, Any]:
    rows = (
        db.query(ActivityEvent)
        .filter(ActivityEvent.user_key == user_key)
        .order_by(ActivityEvent.id.desc())
        .limit(200)
        .all()
    )
    by_type: Dict[str, int] = {}
    for r in rows:
        by_type[r.event_type] = by_type.get(r.event_type, 0) + 1
    return {"user_key": user_key, "total_events": len(rows), "by_type": by_type}


def _run_retraining_job() -> None:
    db = SessionLocal()
    try:
        rows = db.query(ActivityEvent).order_by(ActivityEvent.id.desc()).limit(5000).all()
        skill_weights: Dict[str, float] = {}
        event_counts: Dict[str, int] = {}
        for r in rows:
            event_counts[r.event_type] = event_counts.get(r.event_type, 0) + 1
            if r.entity_type == "skill" and r.entity_id:
                s = str(r.entity_id).strip().lower()
                skill_weights[s] = skill_weights.get(s, 0.0) + 1.0
            if r.metadata_json:
                try:
                    md = json.loads(r.metadata_json)
                    if isinstance(md, dict):
                        for s in md.get("skills", []):
                            sk = str(s).strip().lower()
                            if sk:
                                skill_weights[sk] = skill_weights.get(sk, 0.0) + 0.6
                except Exception:
                    pass

        max_w = max(skill_weights.values()) if skill_weights else 1.0
        normalized = {k: round(v / max_w, 4) for k, v in skill_weights.items()}
        model_payload = {"skill_weights": normalized, "event_counts": event_counts, "trained_on_events": len(rows)}
        artifact = PersonalizationModel(status="ready", model_json=json.dumps(model_payload, ensure_ascii=False))
        db.add(artifact)
        db.commit()
    finally:
        db.close()


@app.post("/api/retrain/start")
def api_retrain_start(
    background_tasks: BackgroundTasks,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> Dict[str, str]:
    user_id = _resolve_user_id(credentials, fallback_user_key=None)
    if user_id == "anonymous":
        raise HTTPException(status_code=401, detail="Authentication required.")
    background_tasks.add_task(_run_retraining_job)
    return {"status": "started", "message": "Retraining job started in background."}


@app.get("/api/retrain/status")
def api_retrain_status() -> Dict[str, Any]:
    db = SessionLocal()
    try:
        latest = db.query(PersonalizationModel).order_by(PersonalizationModel.id.desc()).first()
        if not latest:
            return {"status": "no_model"}
        payload = json.loads(latest.model_json or "{}")
        return {
            "status": latest.status,
            "created_at": latest.created_at.isoformat(),
            "trained_on_events": payload.get("trained_on_events", 0),
            "top_skills": list((payload.get("skill_weights") or {}).items())[:8],
        }
    finally:
        db.close()


def _skills_from_raw(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]
    s = str(value)
    if not s.strip():
        return []
    if s.strip().startswith("["):
        try:
            v = json.loads(s)
            if isinstance(v, list):
                return [str(x).strip() for x in v if str(x).strip()]
        except Exception:
            pass
    return [x.strip() for x in s.split(",") if x.strip()]


def _ingest_jobs_from_df(df, source: str, db: Session) -> int:
    count = 0
    for _, row in df.iterrows():
        title = str(row.get("title", "")).strip()
        if not title:
            continue
        rec = DatasetJob(
            external_id=str(row.get("id", "") or row.get("job_id", "")).strip() or None,
            title=title,
            company=str(row.get("company", "Unknown")).strip() or "Unknown",
            location=str(row.get("location", "Remote")).strip() or "Remote",
            salary_lpa=float(row.get("salary_lpa", row.get("salary", 0.0)) or 0.0),
            skills_json=json.dumps(_skills_from_raw(row.get("skills")), ensure_ascii=False),
            desc=str(row.get("desc", row.get("description", ""))).strip(),
            source=source,
        )
        db.add(rec)
        count += 1
    db.commit()
    return count


def _ingest_courses_from_df(df, source: str, db: Session) -> int:
    count = 0
    for _, row in df.iterrows():
        title = str(row.get("title", "")).strip()
        if not title:
            continue
        rec = DatasetCourse(
            external_id=str(row.get("id", "") or row.get("course_id", "")).strip() or None,
            title=title,
            provider=str(row.get("provider", "Unknown")).strip() or "Unknown",
            skills_json=json.dumps(_skills_from_raw(row.get("skills")), ensure_ascii=False),
            source=source,
        )
        db.add(rec)
        count += 1
    db.commit()
    return count


@app.post("/api/datasets/ingest", response_model=DatasetIngestResponse)
async def api_datasets_ingest(
    kind: str = Form(...),  # jobs | courses
    source: str = Form("uploaded"),
    file: UploadFile = File(...),
    db=Depends(get_db),
) -> DatasetIngestResponse:
    try:
        import pandas as pd

        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="Dataset file is empty.")
        filename = (file.filename or "").lower()
        if filename.endswith(".json"):
            rows = json.loads(content.decode("utf-8-sig", errors="ignore"))
            if not isinstance(rows, list):
                raise HTTPException(status_code=400, detail="JSON dataset must be an array of objects.")
            df = pd.DataFrame(rows)
        else:
            from io import StringIO

            text = content.decode("utf-8-sig", errors="ignore")
            df = pd.read_csv(StringIO(text))

        k = kind.strip().lower()
        if k == "jobs":
            ingested = _ingest_jobs_from_df(df, source, db)
        elif k == "courses":
            ingested = _ingest_courses_from_df(df, source, db)
        else:
            raise HTTPException(status_code=400, detail="kind must be 'jobs' or 'courses'.")
        return DatasetIngestResponse(kind=k, ingested_count=ingested, source=source)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Dataset ingestion failed: {e}")


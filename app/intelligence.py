from __future__ import annotations

from datetime import date
from typing import Any, Dict, List

import json
from .schemas import ProfileInput

try:
    import pandas as pd
except Exception:  # pragma: no cover
    pd = None

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
except Exception:  # pragma: no cover
    TfidfVectorizer = None
    cosine_similarity = None

try:
    import spacy
    from spacy.pipeline import EntityRuler
except Exception:  # pragma: no cover
    spacy = None
    EntityRuler = None

from sqlalchemy.orm import Session

from .models import ActivityEvent, DatasetCourse, DatasetJob, PersonalizationModel, UserState


SKILLS_TAXONOMY = {
    "frontend": ["html", "css", "javascript", "typescript", "react", "next.js", "accessibility"],
    "backend": ["python", "fastapi", "django", "node.js", "sql", "api design", "testing"],
    "data": ["sql", "excel", "python", "statistics", "power bi", "tableau", "machine learning"],
    "devops": ["linux", "docker", "kubernetes", "aws", "ci/cd", "monitoring"],
    "soft": ["communication", "problem solving", "teamwork", "presentation", "time management"],
}

JOBS = [
    {
        "id": "job-001",
        "title": "Frontend Developer",
        "company": "PixelForge Labs",
        "location": "Bengaluru",
        "salary_lpa": 8.0,
        "skills": ["html", "css", "javascript", "react", "accessibility"],
        "desc": "Build responsive student-facing web apps using React and modern CSS.",
    },
    {
        "id": "job-002",
        "title": "Data Analyst",
        "company": "InsightNest Analytics",
        "location": "Hyderabad",
        "salary_lpa": 9.5,
        "skills": ["sql", "excel", "statistics", "power bi", "python"],
        "desc": "Analyze datasets, build dashboards, and recommend decisions.",
    },
    {
        "id": "job-003",
        "title": "Backend Developer (Python)",
        "company": "CloudCanvas",
        "location": "Chennai",
        "salary_lpa": 10.0,
        "skills": ["python", "fastapi", "sql", "api design", "testing"],
        "desc": "Design APIs and backend systems for product workflows.",
    },
    {
        "id": "job-004",
        "title": "Junior ML Engineer",
        "company": "NeuroByte",
        "location": "Pune",
        "salary_lpa": 12.0,
        "skills": ["python", "machine learning", "sql", "statistics", "communication"],
        "desc": "Train and ship ML models with clear experimentation logs.",
    },
]

COURSES = [
    {"title": "React Fundamentals", "provider": "Coursera", "skills": ["react", "javascript", "html", "css"]},
    {"title": "SQL for Data Careers", "provider": "Udemy", "skills": ["sql", "excel"]},
    {"title": "Python + FastAPI Bootcamp", "provider": "Coursera", "skills": ["python", "fastapi", "api design"]},
    {"title": "Data Visualization with Power BI", "provider": "Udemy", "skills": ["power bi", "statistics"]},
]


def _norm(items: List[str]) -> List[str]:
    return [str(i).strip().lower() for i in items if str(i).strip()]


def _simple_resume_parse(resume_text: str) -> Dict[str, Any]:
    text = (resume_text or "").lower()
    extracted = []
    for bucket in SKILLS_TAXONOMY.values():
        for skill in bucket:
            if skill in text:
                extracted.append(skill)
    uniq = sorted(set(extracted))
    return {"skills": uniq, "summary": f"Parsed {len(uniq)} skills from resume text."}


_NLP = None


def _get_spacy_pipeline():
    global _NLP
    if _NLP is not None:
        return _NLP
    if spacy is None:
        _NLP = False
        return None
    try:
        nlp = spacy.load("en_core_web_sm")
    except Exception:
        nlp = spacy.blank("en")
    if EntityRuler and "entity_ruler" not in nlp.pipe_names:
        ruler = nlp.add_pipe("entity_ruler")
        patterns = []
        for bucket in SKILLS_TAXONOMY.values():
            for s in bucket:
                patterns.append({"label": "SKILL", "pattern": s})
        ruler.add_patterns(patterns)
    _NLP = nlp
    return _NLP


def parse_resume_with_spacy(resume_text: str) -> Dict[str, Any]:
    text = (resume_text or "").strip()
    if not text:
        return {"skills": [], "entities": [], "summary": "No resume text found."}
    nlp = _get_spacy_pipeline()
    if not nlp:
        fallback = _simple_resume_parse(text)
        return {"skills": fallback["skills"], "entities": [], "summary": "spaCy unavailable, using fallback parser."}
    doc = nlp(text)
    entities = [{"text": ent.text, "label": ent.label_} for ent in doc.ents[:80]]
    found_skills = sorted(set([e["text"].lower() for e in entities if e["label"] == "SKILL"]))
    fallback_skills = _simple_resume_parse(text)["skills"]
    found_skills = sorted(set(found_skills + fallback_skills))
    return {
        "skills": found_skills,
        "entities": entities,
        "summary": f"spaCy extracted {len(found_skills)} skill(s) and {len(entities)} entities.",
    }


def _skills_from_json(s: str) -> List[str]:
    try:
        v = json.loads(s or "[]")
        return [str(x) for x in v] if isinstance(v, list) else []
    except Exception:
        return []


def _load_jobs(db: Session | None) -> List[Dict[str, Any]]:
    if db is None:
        return JOBS
    rows = db.query(DatasetJob).all()
    if not rows:
        return JOBS
    out: List[Dict[str, Any]] = []
    for r in rows:
        out.append(
            {
                "id": r.external_id or f"db-job-{r.id}",
                "title": r.title,
                "company": r.company,
                "location": r.location,
                "salary_lpa": float(r.salary_lpa),
                "skills": _skills_from_json(r.skills_json),
                "desc": r.desc or "",
            }
        )
    return out


def _load_courses(db: Session | None) -> List[Dict[str, Any]]:
    if db is None:
        return COURSES
    rows = db.query(DatasetCourse).all()
    if not rows:
        return COURSES
    out: List[Dict[str, Any]] = []
    for r in rows:
        out.append({"title": r.title, "provider": r.provider, "skills": _skills_from_json(r.skills_json)})
    return out


def _get_user_preference(db: Session | None, user_key: str | None) -> Dict[str, Any]:
    if db is None or not user_key:
        return {}
    state = db.query(UserState).filter(UserState.user_key == user_key).first()
    if not state:
        return {}
    try:
        return json.loads(state.preference_json or "{}")
    except Exception:
        return {}


def _save_user_state(db: Session | None, user_key: str | None, profile: ProfileInput, preference: Dict[str, Any]) -> None:
    if db is None or not user_key:
        return
    state = db.query(UserState).filter(UserState.user_key == user_key).first()
    payload_profile = profile.model_dump()
    if not state:
        state = UserState(
            user_key=user_key,
            last_profile_json=json.dumps(payload_profile, ensure_ascii=False),
            preference_json=json.dumps(preference, ensure_ascii=False),
        )
        db.add(state)
    else:
        state.last_profile_json = json.dumps(payload_profile, ensure_ascii=False)
        state.preference_json = json.dumps(preference, ensure_ascii=False)
    db.commit()


def _build_preference_from_activity(db: Session | None, user_key: str | None) -> Dict[str, Any]:
    if db is None or not user_key:
        return {}
    rows = (
        db.query(ActivityEvent)
        .filter(ActivityEvent.user_key == user_key)
        .order_by(ActivityEvent.id.desc())
        .limit(400)
        .all()
    )
    clicked_jobs: Dict[str, int] = {}
    clicked_skills: Dict[str, int] = {}
    for r in rows:
        if r.entity_type == "job" and r.entity_id:
            clicked_jobs[r.entity_id] = clicked_jobs.get(r.entity_id, 0) + 1
        if r.entity_type == "skill" and r.entity_id:
            clicked_skills[r.entity_id.lower()] = clicked_skills.get(r.entity_id.lower(), 0) + 1
        if r.metadata_json:
            try:
                md = json.loads(r.metadata_json)
                for s in md.get("skills", []) if isinstance(md, dict) else []:
                    sl = str(s).lower()
                    clicked_skills[sl] = clicked_skills.get(sl, 0) + 1
            except Exception:
                pass
    return {"clicked_jobs": clicked_jobs, "clicked_skills": clicked_skills}


def _load_global_model(db: Session | None) -> Dict[str, Any]:
    if db is None:
        return {}
    row = db.query(PersonalizationModel).order_by(PersonalizationModel.id.desc()).first()
    if not row:
        return {}
    try:
        return json.loads(row.model_json or "{}")
    except Exception:
        return {}


def _career_score(profile: ProfileInput, matched_jobs: List[Dict[str, Any]]) -> float:
    skills = set(_norm(profile.skills))
    role_fit = min(1.0, len([s for s in skills if s in _norm(profile.target_role.split())]) / 3.0)
    experience_factor = 0.35 if profile.experience_years < 1 else 0.6 if profile.experience_years < 3 else 0.8
    job_factor = (matched_jobs[0]["match_score"] / 100.0) if matched_jobs else 0.3
    score = (0.45 * job_factor) + (0.35 * experience_factor) + (0.20 * role_fit)
    return round(max(0.15, min(0.99, score)) * 100, 1)


def _growth_percent(profile: ProfileInput) -> float:
    # Deterministic "live growth tracker" heuristic for demo.
    base = 4.0 + min(8.5, len(profile.skills) * 0.9)
    if profile.experience_years < 2:
        base += 1.5
    return round(base, 1)


def _skill_levels(profile: ProfileInput) -> List[Dict[str, Any]]:
    skills = _norm(profile.skills)
    out = []
    for s in skills[:10]:
        lvl = 35 + (len(s) % 6) * 9
        out.append({"skill": s.title(), "level": min(95, lvl)})
    return out


def _timeline(profile: ProfileInput) -> List[Dict[str, str]]:
    today = date.today().isoformat()
    return [
        {"date": today, "event": "Profile updated"},
        {"date": today, "event": f"AI generated roadmap for {profile.target_role}"},
        {"date": today, "event": "Recommended 4 jobs and 3 courses"},
    ]


def _match_jobs(
    profile: ProfileInput,
    jobs_data: List[Dict[str, Any]],
    preference: Dict[str, Any],
    global_model: Dict[str, Any],
) -> List[Dict[str, Any]]:
    user_skills = _norm(profile.skills)
    user_blob = " ".join(user_skills + [profile.target_role.lower()])
    clicked_jobs = preference.get("clicked_jobs", {}) if preference else {}
    clicked_skills = preference.get("clicked_skills", {}) if preference else {}
    skill_weights = global_model.get("skill_weights", {}) if global_model else {}

    if TfidfVectorizer and cosine_similarity:
        docs = [user_blob] + [" ".join(_norm(j["skills"]) + [j["title"].lower(), j.get("desc", "").lower()]) for j in jobs_data]
        vec = TfidfVectorizer().fit_transform(docs)
        sims = cosine_similarity(vec[0:1], vec[1:]).flatten()
        scored = []
        for idx, job in enumerate(jobs_data):
            overlap = len(set(user_skills).intersection(set(_norm(job["skills"]))))
            blended = 0.7 * float(sims[idx]) + 0.3 * (overlap / max(1, len(job["skills"])))
            job_bias = 1.0 + 0.08 * clicked_jobs.get(str(job.get("id")), 0)
            local_skill_bias = 1.0 + sum(0.02 * clicked_skills.get(s, 0) for s in _norm(job["skills"])[:5])
            global_skill_bias = 1.0 + sum(0.05 * float(skill_weights.get(s, 0.0)) for s in _norm(job["skills"])[:6])
            blended *= min(2.0, job_bias * local_skill_bias * global_skill_bias)
            scored.append((job, blended))
    else:
        scored = []
        for job in jobs_data:
            overlap = len(set(user_skills).intersection(set(_norm(job["skills"]))))
            blended = overlap / max(1, len(job["skills"]))
            job_bias = 1.0 + 0.08 * clicked_jobs.get(str(job.get("id")), 0)
            global_skill_bias = 1.0 + sum(0.05 * float(skill_weights.get(s, 0.0)) for s in _norm(job["skills"])[:6])
            blended *= min(1.8, job_bias * global_skill_bias)
            scored.append((job, blended))

    scored.sort(key=lambda x: x[1], reverse=True)
    top = []
    for job, score in scored[:4]:
        top.append(
            {
                **job,
                "match_score": round(score * 100, 1),
                "confidence_score": round(min(99.0, 52 + score * 48), 1),
            }
        )
    return top


def _skill_gap(profile: ProfileInput, top_jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    have = set(_norm(profile.skills))
    need_count: Dict[str, int] = {}
    for job in top_jobs[:3]:
        for s in _norm(job["skills"]):
            if s not in have:
                need_count[s] = need_count.get(s, 0) + 1
    gaps = sorted(need_count.items(), key=lambda kv: (-kv[1], kv[0]))
    return [{"skill": g, "importance": min(100, 60 + c * 15)} for g, c in gaps[:8]]


def _career_paths(profile: ProfileInput, top_jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    base_salary = top_jobs[0]["salary_lpa"] if top_jobs else 7.0
    return [
        {"path": "Current track", "timeline": "0-3 months", "expected_salary_lpa": round(base_salary, 1)},
        {"path": "With 2 new core skills", "timeline": "3-6 months", "expected_salary_lpa": round(base_salary * 1.2, 1)},
        {"path": "With project + interview prep", "timeline": "6-12 months", "expected_salary_lpa": round(base_salary * 1.45, 1)},
    ]


def _courses_for_gaps(
    gaps: List[Dict[str, Any]],
    courses_data: List[Dict[str, Any]],
    preference: Dict[str, Any],
    global_model: Dict[str, Any],
) -> List[Dict[str, Any]]:
    needed = set(_norm([g["skill"] for g in gaps]))
    clicked_skills = preference.get("clicked_skills", {}) if preference else {}
    skill_weights = global_model.get("skill_weights", {}) if global_model else {}
    picks = []
    for c in courses_data:
        overlap = len(set(_norm(c["skills"])).intersection(needed))
        if overlap > 0:
            bias = 1 + sum(clicked_skills.get(s, 0) * 0.15 for s in _norm(c["skills"]))
            bias += sum(float(skill_weights.get(s, 0.0)) * 0.2 for s in _norm(c["skills"]))
            picks.append({**c, "relevance": round(overlap * bias, 2)})
    picks.sort(key=lambda x: x["relevance"], reverse=True)
    return picks[:4]


def build_unified_insights(
    profile: ProfileInput,
    resume_text: str | None = None,
    db: Session | None = None,
    user_key: str | None = None,
) -> Dict[str, Any]:
    parsed_resume = parse_resume_with_spacy(resume_text or "")
    merged_skills = sorted(set(_norm(profile.skills + parsed_resume["skills"])))
    merged_profile = ProfileInput(
        name=profile.name,
        email=profile.email,
        target_role=profile.target_role,
        experience_years=profile.experience_years,
        skills=merged_skills if merged_skills else profile.skills,
        interests=profile.interests,
    )

    preference = _build_preference_from_activity(db, user_key)
    if not preference:
        preference = _get_user_preference(db, user_key)
    global_model = _load_global_model(db)

    jobs_data = _load_jobs(db)
    courses_data = _load_courses(db)
    jobs = _match_jobs(merged_profile, jobs_data, preference, global_model)
    gaps = _skill_gap(merged_profile, jobs)
    career_score = _career_score(merged_profile, jobs)
    growth = _growth_percent(merged_profile)
    skill_levels = _skill_levels(merged_profile)
    timeline = _timeline(merged_profile)
    courses = _courses_for_gaps(gaps, courses_data, preference, global_model)
    paths = _career_paths(merged_profile, jobs)

    next_action = (
        f"Learn {gaps[0]['skill'].title()} this week and apply for {jobs[0]['title']} roles."
        if gaps and jobs
        else "Complete one portfolio project and apply for 5 relevant roles."
    )

    salary_simulation = []
    if paths and gaps:
        salary_simulation.append(
            {
                "scenario": f"If you learn {gaps[0]['skill'].title()}",
                "salary_projection_lpa": paths[1]["expected_salary_lpa"],
            }
        )
    if len(gaps) > 1:
        salary_simulation.append(
            {
                "scenario": f"If you learn {gaps[1]['skill'].title()} + build one project",
                "salary_projection_lpa": paths[2]["expected_salary_lpa"],
            }
        )

    # Optional Pandas usage for aggregating category readiness.
    category_scores: List[Dict[str, Any]] = []
    if pd is not None:
        rows = []
        have = set(_norm(merged_profile.skills))
        for category, sk in SKILLS_TAXONOMY.items():
            total = len(sk)
            hit = len(set(_norm(sk)).intersection(have))
            rows.append({"category": category.title(), "score": round((hit / max(1, total)) * 100, 1)})
        df = pd.DataFrame(rows).sort_values("score", ascending=False)
        category_scores = df.to_dict(orient="records")
    else:
        for category, sk in SKILLS_TAXONOMY.items():
            hit = len(set(_norm(sk)).intersection(set(_norm(merged_profile.skills))))
            category_scores.append({"category": category.title(), "score": round((hit / max(1, len(sk))) * 100, 1)})

    _save_user_state(db, user_key, merged_profile, preference)

    return {
        "profile": {
            "name": merged_profile.name or "Student",
            "target_role": merged_profile.target_role,
            "experience_years": merged_profile.experience_years,
            "skills": merged_profile.skills,
            "resume_parse": parsed_resume,
        },
        "dashboard": {
            "career_score": career_score,
            "growth_percent_weekly": growth,
            "skill_levels": skill_levels,
            "timeline": timeline,
            "category_scores": category_scores,
            "gamification": {
                "level": "Beginner" if career_score < 55 else "Intermediate" if career_score < 75 else "Pro",
                "xp": int(career_score * 12),
                "streak_days": min(30, 3 + int(growth)),
                "badges": ["Consistency Starter", "Skill Mapper"],
            },
        },
        "insights": {
            "skill_gap_analysis": gaps,
            "career_path_predictor": paths,
            "salary_insights": salary_simulation,
            "next_best_action": next_action,
        },
        "jobs": {
            "matches": jobs,
            "notifications": [
                f"{len(jobs)} new jobs match your profile",
                f"You're {career_score}% ready for {merged_profile.target_role}",
            ],
        },
        "learning": {
            "recommended_courses": courses,
            "dynamic_roadmap": [
                {"day": "Mon", "task": "10-min concept revision"},
                {"day": "Tue", "task": "Practice 2 interview questions"},
                {"day": "Wed", "task": "Build a mini feature"},
                {"day": "Thu", "task": "Apply to 2 jobs"},
                {"day": "Fri", "task": "Portfolio update + reflection"},
            ],
        },
        "assistant": {
            "starter_prompts": [
                "Review my resume for frontend roles",
                "Give me a 7-day interview prep plan",
                "What should I learn next for better salary?",
            ]
        },
    }


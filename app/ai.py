from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Optional

import httpx

from .schemas import AssessResponse, ProfileInput


def _norm_list(items: List[str]) -> List[str]:
    return [str(x).strip().lower() for x in items if str(x).strip()]


def _choose_priority(missing_count: int, idx: int) -> int:
    # More missing items => slightly higher priority numbers, but keep stable bounds.
    base = max(1, min(5, 4 - missing_count + idx))
    return int(base)


ROLE_KEYWORDS: List[Dict[str, Any]] = [
    {
        "keywords": ["data", "analytics", "bi", "sql", "statistics", "ml", "machine learning", "model"],
        "roles": [
            {"role": "Data Analyst", "required": ["sql", "excel", "dashboards", "statistics"]},
            {"role": "Business Intelligence (BI) Analyst", "required": ["sql", "bi tools", "modeling", "dashboards"]},
            {"role": "Analytics Engineer", "required": ["sql", "data modeling", "etl", "testing"]},
        ],
    },
    {
        "keywords": ["web", "frontend", "react", "javascript", "typescript", "css", "ui"],
        "roles": [
            {"role": "Frontend Engineer", "required": ["javascript", "html", "css", "accessibility"]},
            {"role": "UI Developer", "required": ["ui patterns", "css", "performance", "accessibility"]},
            {"role": "Full-Stack Developer", "required": ["javascript", "api", "databases", "authentication"]},
        ],
    },
    {
        "keywords": ["cloud", "devops", "kubernetes", "docker", "infra", "terraform", "aws", "gcp", "azure"],
        "roles": [
            {"role": "DevOps Engineer", "required": ["linux", "ci/cd", "docker", "monitoring"]},
            {"role": "Cloud Engineer", "required": ["cloud networking", "iam", "automation", "observability"]},
            {"role": "Site Reliability Engineer (SRE)", "required": ["sre practices", "incident response", "monitoring", "capacity"]},
        ],
    },
]


def _match_role_templates(target_role: str) -> List[Dict[str, Any]]:
    t = target_role.lower()
    for tpl in ROLE_KEYWORDS:
        if any(k in t for k in tpl["keywords"]):
            return tpl["roles"]
    # Generic fallback: synthesize roles from the provided target.
    cleaned = re.sub(r"[^a-z0-9 ]+", "", target_role.lower()).strip()
    title = cleaned.title() if cleaned else "Specialist"
    return [
        {"role": f"Junior {title}", "required": ["fundamentals", "practical projects", "communication"]},
        {"role": f"Mid {title}", "required": ["advanced fundamentals", "system thinking", "shipping"]},
        {"role": f"Senior {title}", "required": ["leadership", "architecture", "mentoring"]},
    ]


def _extract_program_level(experience_years: int) -> str:
    if experience_years < 1:
        return "starter"
    if experience_years < 3:
        return "intermediate"
    return "advanced"


def _build_fallback(profile: ProfileInput) -> AssessResponse:
    candidate_skills = set(_norm_list(profile.skills))
    templates = _match_role_templates(profile.target_role)
    level = _extract_program_level(profile.experience_years)

    placements: List[Dict[str, Any]] = []
    skill_gaps: List[Dict[str, Any]] = []
    roadmap_steps: List[Dict[str, Any]] = []

    for i, item in enumerate(templates):
        required = [str(s).lower() for s in item.get("required", [])]
        have = sum(1 for s in required if s in candidate_skills or any(s in c for c in candidate_skills))
        missing = [s for s in required if s not in candidate_skills and not any(s in c for c in candidate_skills)]

        # Confidence heuristic: more overlap => higher.
        confidence = 0.35 + (have / max(1, len(required))) * 0.55
        confidence = max(0.05, min(0.98, confidence))

        why = (
            f"Your input matches {have} key area(s) for the role, and aligns with a {level} track."
            if missing
            else f"Your input strongly matches the role’s core requirements for a {level} track."
        )
        quick_start = [f"{m.title()} mini-project (2-3 hours)" for m in missing[:2]] or [
            "Pick a small project and ship the first version in 1 day"
        ]

        # Local import-free object creation via dict; FastAPI will validate into Pydantic models.
        placements.append(
            {
                "role": item["role"],
                "confidence": float(round(confidence, 2)),
                "why_it_fits": why,
                "quick_start": quick_start,
            }
        )

    # Skill gaps: aggregate top missing skills across top placements.
    required_counts: Dict[str, int] = {}
    required_sources: Dict[str, str] = {}
    for p in placements[:2]:
        role = p["role"]
        tpl = next((x for x in templates if x["role"] == role), None)
        if not tpl:
            continue
        required = [str(s).lower() for s in tpl.get("required", [])]
        missing = [s for s in required if s not in candidate_skills and not any(s in c for c in candidate_skills)]
        for m in missing:
            required_counts[m] = required_counts.get(m, 0) + 1
            required_sources[m] = role

    missing_sorted = sorted(required_counts.items(), key=lambda kv: (-kv[1], kv[0]))
    for idx, (gap_skill, count) in enumerate(missing_sorted[:6]):
        priority = _choose_priority(len(missing_sorted), idx)
        suggested = f"Build a focused {gap_skill} exercise, then apply it in a {required_sources.get(gap_skill, 'role')} artifact"
        skill_gaps.append(
            {
                "gap": gap_skill,
                "priority": priority,
                "suggested_next_step": suggested,
            }
        )

    if not skill_gaps:
        skill_gaps = [
            {
                "gap": "Portfolio polish",
                "priority": 2,
                "suggested_next_step": "Turn one project into a case study: problem, approach, results, and lessons learned",
                }
        ]

    # Roadmap: 4 steps (2-3 weeks each), tuned by experience.
    if profile.experience_years < 1:
        roadmap_steps = [
            {"timeframe": "0-2 weeks", "goal": "Foundation sprint", "actions": ["Pick 1 role target", "Complete 1 core tutorial set", "Ship a tiny project"]},
            {"timeframe": "2-6 weeks", "goal": "Skill gap closure", "actions": [f"Practice the top gap: {skill_gaps[0]['gap']}", "Add 1 demo to portfolio", "Get feedback from peers"]},
            {"timeframe": "6-10 weeks", "goal": "Role-aligned projects", "actions": ["Build 1 substantial project", "Add measurements/results", "Write a short case study"]},
            {"timeframe": "10-14 weeks", "goal": "Placement readiness", "actions": ["Create resume bullets", "Practice interviews", "Apply to 10 targeted postings"]},
        ]
    elif profile.experience_years < 3:
        roadmap_steps = [
            {"timeframe": "0-3 weeks", "goal": "Resume + narrative", "actions": ["Clarify impact metrics", "Update resume for target role", "Refactor 1 existing project"]},
            {"timeframe": "3-6 weeks", "goal": "Gap-driven improvements", "actions": [f"Deep-dive: {skill_gaps[0]['gap']}", "Add tests/checks", "Improve performance/accessibility"]},
            {"timeframe": "6-10 weeks", "goal": "Proof of competence", "actions": ["Ship 1 capstone", "Document decisions/tradeoffs", "Request mentor review"]},
            {"timeframe": "10-14 weeks", "goal": "Placement campaign", "actions": ["Build outreach list", "Tailor applications", "Mock interviews (2 rounds)"]},
        ]
    else:
        roadmap_steps = [
            {"timeframe": "0-3 weeks", "goal": "Leadership track", "actions": ["Define scope and ownership", "Document systems/processes", "Mentor a smaller contributor"]},
            {"timeframe": "3-6 weeks", "goal": "Advanced mastery", "actions": [f"Strengthen: {skill_gaps[0]['gap']}", "Prototype an architecture improvement", "Measure outcomes"]},
            {"timeframe": "6-10 weeks", "goal": "Strategic portfolio", "actions": ["Publish a technical write-up", "Create a migration/perf plan", "Summarize business impact"]},
            {"timeframe": "10-14 weeks", "goal": "Interview & negotiation", "actions": ["Mock system design", "Practice stakeholder comms", "Negotiate offers confidently"]},
        ]

    return AssessResponse(
        submission_id=-1,
        placement_recommendations=placements,
        skill_gaps=skill_gaps,
        roadmap_steps=roadmap_steps,
        ai_notes="Generated using deterministic fallback logic (set `OPENAI_API_KEY` for real LLM output).",
    )


async def _call_openai(profile: ProfileInput, timeout_s: int = 30) -> Optional[Dict[str, Any]]:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return None

    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini"

    system = (
        "You are an expert career coach and hiring strategist. "
        "Return ONLY valid JSON matching the requested schema."
    )

    # Keep output small and deterministic for parsing.
    user_prompt = {
        "target_role": profile.target_role,
        "experience_years": profile.experience_years,
        "skills": profile.skills,
        "interests": profile.interests,
        "requirements": {
            "placement_recommendations": [
                {"role": "string", "confidence": "number 0-1", "why_it_fits": "string", "quick_start": ["string"]}
            ],
            "skill_gaps": [{"gap": "string", "priority": "int 1-5", "suggested_next_step": "string"}],
            "roadmap_steps": [{"timeframe": "string", "goal": "string", "actions": ["string"]}],
            "ai_notes": "string",
        },
    }

    payload = {
        "model": model,
        "temperature": 0.4,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": str(user_prompt)},
        ],
        "response_format": {"type": "json_object"},
    }

    headers = {"Authorization": f"Bearer {api_key}"}
    async with httpx.AsyncClient(timeout=timeout_s) as client:
        r = await client.post("https://api.openai.com/v1/chat/completions", json=payload, headers=headers)
        r.raise_for_status()
        data = r.json()
        content = data["choices"][0]["message"]["content"]

    # content is expected to be JSON text due to response_format.
    import json

    return json.loads(content)


async def assess_profile(profile: ProfileInput) -> AssessResponse:
    fallback = _build_fallback(profile)

    try:
        openai_json = await _call_openai(profile)
        if not openai_json:
            return fallback

        # Map returned JSON -> schema. Keep parsing tolerant.
        placement_recommendations = openai_json.get("placement_recommendations", fallback.placement_recommendations)
        skill_gaps = openai_json.get("skill_gaps", fallback.skill_gaps)
        roadmap_steps = openai_json.get("roadmap_steps", fallback.roadmap_steps)
        ai_notes = openai_json.get("ai_notes", "Generated using OpenAI.")

        return AssessResponse(
            submission_id=-1,
            placement_recommendations=placement_recommendations,
            skill_gaps=skill_gaps,
            roadmap_steps=roadmap_steps,
            ai_notes=str(ai_notes),
        )
    except Exception:
        # Never fail UX; return fallback if OpenAI parsing/calls break.
        return fallback


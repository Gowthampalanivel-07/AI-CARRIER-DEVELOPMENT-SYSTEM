from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ProfileInput(BaseModel):
    name: Optional[str] = Field(default=None, max_length=200)
    # Use plain string (no EmailStr) to avoid the optional `email_validator` dependency.
    email: Optional[str] = Field(default=None, max_length=320)

    target_role: str = Field(..., min_length=2, max_length=120)
    experience_years: int = Field(..., ge=0, le=40)
    skills: List[str] = Field(..., min_length=1, max_length=30)
    interests: List[str] = Field(default_factory=list, max_length=20)


class PlacementRecommendation(BaseModel):
    role: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    why_it_fits: str
    quick_start: List[str] = Field(default_factory=list)


class SkillGap(BaseModel):
    gap: str
    priority: int = Field(..., ge=1, le=5)
    suggested_next_step: str


class RoadmapStep(BaseModel):
    timeframe: str
    goal: str
    actions: List[str] = Field(default_factory=list)


class AssessResponse(BaseModel):
    submission_id: int
    placement_recommendations: List[PlacementRecommendation]
    skill_gaps: List[SkillGap]
    roadmap_steps: List[RoadmapStep]
    ai_notes: str


class UnifiedInsightsRequest(BaseModel):
    profile: ProfileInput
    resume_text: Optional[str] = Field(default=None, max_length=20000)
    user_key: Optional[str] = Field(default=None, max_length=120)


class ChatRequest(BaseModel):
    profile: ProfileInput
    message: str = Field(..., min_length=2, max_length=2000)


class ChatResponse(BaseModel):
    reply: str


class ActivityEventRequest(BaseModel):
    user_key: Optional[str] = Field(default=None, min_length=3, max_length=120)
    event_type: str = Field(..., min_length=2, max_length=80)
    entity_type: Optional[str] = Field(default=None, max_length=80)
    entity_id: Optional[str] = Field(default=None, max_length=120)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DatasetIngestResponse(BaseModel):
    kind: str
    ingested_count: int
    source: Optional[str] = None


class RegisterRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=320)
    password: str = Field(..., min_length=8, max_length=128)
    full_name: Optional[str] = Field(default=None, max_length=200)


class LoginRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=320)
    password: str = Field(..., min_length=8, max_length=128)


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str


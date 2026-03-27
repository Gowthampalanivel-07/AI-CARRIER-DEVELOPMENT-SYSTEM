from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Submission(Base):
    __tablename__ = "submissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Minimal identity fields (optional). Stored as strings to keep it simple.
    name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(320), nullable=True)

    # Store raw request + computed AI output as JSON text.
    raw_input_json: Mapped[str] = mapped_column(Text, nullable=False)
    output_json: Mapped[str] = mapped_column(Text, nullable=False)

    @staticmethod
    def dumps(obj: Dict[str, Any]) -> str:
        return json.dumps(obj, ensure_ascii=False)

    @staticmethod
    def loads(s: str) -> Dict[str, Any]:
        return json.loads(s)


class UserState(Base):
    __tablename__ = "user_states"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_key: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    last_profile_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    preference_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")


class ActivityEvent(Base):
    __tablename__ = "activity_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_key: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    entity_type: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    entity_id: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    metadata_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class DatasetJob(Base):
    __tablename__ = "dataset_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    external_id: Mapped[Optional[str]] = mapped_column(String(120), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    company: Mapped[str] = mapped_column(String(240), nullable=False, default="Unknown")
    location: Mapped[str] = mapped_column(String(120), nullable=False, default="Remote")
    salary_lpa: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    skills_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    desc: Mapped[str] = mapped_column(Text, nullable=False, default="")
    source: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)


class DatasetCourse(Base):
    __tablename__ = "dataset_courses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    external_id: Mapped[Optional[str]] = mapped_column(String(120), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    provider: Mapped[str] = mapped_column(String(240), nullable=False, default="Unknown")
    skills_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    source: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)


class UserAccount(Base):
    __tablename__ = "user_accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False, index=True)
    full_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class PersonalizationModel(Base):
    __tablename__ = "personalization_models"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="ready")
    model_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")


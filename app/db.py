from __future__ import annotations

import os
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker


def _database_url() -> str:
    # Keep defaults deterministic for first-run. Use `.env` if available via pydantic-settings.
    return os.getenv("DATABASE_URL", "sqlite:///./app.db")


def create_engine_and_session() -> tuple[Engine, sessionmaker[Session]]:
    db_url = _database_url()

    # sqlite needs check_same_thread=False when used with FastAPI.
    connect_args = {}
    if db_url.startswith("sqlite"):
        connect_args = {"check_same_thread": False}

    engine = create_engine(db_url, connect_args=connect_args, future=True)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)
    return engine, SessionLocal


ENGINE, SessionLocal = create_engine_and_session()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


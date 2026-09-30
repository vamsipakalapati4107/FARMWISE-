"""Phase 7: SQLAlchemy engine/session for the platform's app database
(users, farms, crops, notifications -- separate from the read-only
weather pipeline CSVs, which stay file-based).

The DB file lives at data/app.db (gitignored, like the rest of data/).
"""
from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DB_FILE = Path(os.environ["APP_DB_PATH"]) if os.environ.get("APP_DB_PATH") else DATA_DIR / "app.db"

engine = create_engine(f"sqlite:///{DB_FILE}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def init_db() -> None:
    DB_FILE.parent.mkdir(parents=True, exist_ok=True)
    from migrate_db import run_migrations  # deferred: migrate_db imports Base/engine from here

    applied = run_migrations()
    if applied:
        print(f"Applied {len(applied)} database migration(s): {applied}")


def get_db():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()

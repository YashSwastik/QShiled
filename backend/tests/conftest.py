"""
conftest.py — shared pytest fixtures for all backend tests.

Uses a file-based temp SQLite database (test_qshield.db) so that
multiple connections within the same test process share state.
The test DB file is deleted and recreated fresh for each test session.
"""
import os
import pytest
from pathlib import Path
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.database import Base, get_db
from app.main import app as fastapi_app

# ── Temp test database file ───────────────────────────────────────────────────
_TEST_DB_PATH = Path(__file__).parent / "test_qshield.db"
TEST_DATABASE_URL = f"sqlite:///{_TEST_DB_PATH}"

# Remove stale test DB from previous runs
if _TEST_DB_PATH.exists():
    _TEST_DB_PATH.unlink()

TEST_ENGINE = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
)


@event.listens_for(TEST_ENGINE, "connect")
def _set_pragmas(dbapi_conn, _):
    c = dbapi_conn.cursor()
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA foreign_keys=ON")
    c.close()


TEST_SESSION = sessionmaker(autocommit=False, autoflush=False, bind=TEST_ENGINE)

# Register ORM models and create schema
import app.models as _models_pkg  # noqa: F401
Base.metadata.create_all(bind=TEST_ENGINE)


# ── Override the FastAPI DB dependency ───────────────────────────────────────
def _override_get_db():
    db = TEST_SESSION()
    try:
        yield db
    finally:
        db.close()


fastapi_app.dependency_overrides[get_db] = _override_get_db


# ── Shared TestClient ─────────────────────────────────────────────────────────
@pytest.fixture(scope="session")
def client():
    with TestClient(fastapi_app, raise_server_exceptions=True) as c:
        yield c


# ── Truncate data between tests (FK-safe delete order) ───────────────────────
TRUNCATE_ORDER = [
    "roadmap_items", "crypto_findings", "risk_assessments", "reports",
    "scans", "assets", "applications", "projects", "organizations",
    "migration_recommendations",
]


@pytest.fixture(autouse=True)
def clean_db():
    yield
    db = TEST_SESSION()
    for table in TRUNCATE_ORDER:
        try:
            db.execute(text(f"DELETE FROM {table}"))
        except Exception:
            db.rollback()
    db.commit()
    db.close()

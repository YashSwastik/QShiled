from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from app.config import get_settings

settings = get_settings()

# SQLite-specific: enable WAL mode and foreign keys for better behavior
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},  # needed for SQLite + FastAPI threading
    echo=settings.debug,
)


@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    """Enable WAL mode and foreign key enforcement for SQLite."""
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""
    pass


def get_db():
    """FastAPI dependency: yields a DB session and ensures cleanup."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _safe_migrate_sqlite():
    """
    Idempotent column additions for SQLite (no Alembic).
    Each ALTER TABLE is wrapped in a try/except — if the column already exists
    SQLite raises OperationalError which we silently ignore.
    This runs on every startup so a developer with an existing DB is never broken.
    """
    from sqlalchemy import text as sql_text
    new_columns = [
        ("risk_assessments", "overall_severity",          "VARCHAR(32)"),
        ("risk_assessments", "legacy_count",               "INTEGER DEFAULT 0"),
        ("risk_assessments", "per_finding_scores",         "JSON"),
        ("risk_assessments", "top_priority_finding_ids",   "JSON"),
        ("risk_assessments", "methodology_version",        "VARCHAR(32)"),
    ]
    with engine.connect() as conn:
        for table, column, col_type in new_columns:
            try:
                conn.execute(sql_text(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}"))
                conn.commit()
            except Exception:
                conn.rollback()


def init_db():
    """Create all tables and apply safe column migrations. Called at application startup."""
    # Import models so SQLAlchemy sees them before calling create_all
    import app.models  # noqa: F401  — triggers registration of all ORM models
    Base.metadata.create_all(bind=engine)
    _safe_migrate_sqlite()

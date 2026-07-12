# QShield — Quantum-Safe Cryptography Migration Toolkit

> **Hackathon project** — Discover, inventory, analyze, and migrate quantum-vulnerable cryptography.

## Quick Start

### Prerequisites
- Python 3.12+ (or 3.14 via `py` launcher)
- Node.js 18+

### Backend

```powershell
cd backend
py -m pip install fastapi "uvicorn[standard]" pydantic pydantic-settings sqlalchemy alembic python-multipart python-dotenv aiofiles cryptography
copy .env.example .env
py -m uvicorn app.main:app --reload --port 8000
```

Backend runs at: http://localhost:8000  
API docs: http://localhost:8000/docs

### Frontend

```powershell
cd frontend
npm install
npm run dev
```

Frontend runs at: http://localhost:5173

### Tests (Backend)

```powershell
cd backend
$env:PYTHONPATH="$PWD"; py -m pytest tests/ -v
```

## Project Structure

```
QSheild/
├── backend/          # FastAPI + Python
│   ├── app/
│   │   ├── main.py   # App entry point
│   │   ├── config.py # Settings
│   │   ├── database.py
│   │   ├── models/   # ORM models (Phase 1+)
│   │   ├── schemas/  # Pydantic schemas (Phase 1+)
│   │   ├── routers/  # API routes
│   │   └── services/ # Business logic
│   ├── tests/
│   └── requirements.txt
├── frontend/         # React + Vite + TypeScript + Tailwind
│   └── src/
├── PROJECT_CONTEXT.md  # Architecture source of truth
└── BUILD_PLAN.md       # Phase checklist
```

## Workflow

```
DISCOVER → INVENTORY → ANALYZE → PRIORITIZE → MIGRATE → VALIDATE → REPORT
```

See [PROJECT_CONTEXT.md](./PROJECT_CONTEXT.md) for full architecture and [BUILD_PLAN.md](./BUILD_PLAN.md) for the implementation roadmap.

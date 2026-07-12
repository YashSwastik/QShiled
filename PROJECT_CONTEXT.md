# QShield — Project Context (Source of Truth)

> **Last updated:** 2026-07-12  
> **Status:** Phase 0 — Foundation  
> This file is the persistent reference for all future coding sessions. Update it as the project evolves.

---

## 1. Product Purpose

QShield is a **Quantum-Safe Cryptography Migration Toolkit** for hackathon demonstration.
It helps security teams:
- Discover where classical (quantum-vulnerable) cryptography lives in their codebase, configs, and certificates.
- Build a machine-readable **Cryptographic Bill of Materials (CBOM)**.
- Calculate an **explainable quantum-migration risk score** (deterministic, no LLM).
- Receive **NIST PQC-aligned** migration recommendations.
- Produce a **prioritized migration roadmap** and exportable reports.

---

## 2. Core Workflow

```
DISCOVER → INVENTORY → ANALYZE → PRIORITIZE → MIGRATE → VALIDATE → REPORT
```

| Stage | Description |
|-------|-------------|
| DISCOVER | Upload source code, config files, or X.509 certs; static scanning (regex + AST) |
| INVENTORY | Build a CBOM — list of every cryptographic primitive found with file & line location |
| ANALYZE | Classify each primitive: quantum-safe / quantum-vulnerable / unknown |
| PRIORITIZE | Assign risk scores (0-100) based on algorithm, key size, exposure, and usage context |
| MIGRATE | Generate NIST-aligned replacement recommendations (ML-KEM, ML-DSA, SLH-DSA, etc.) |
| VALIDATE | Demonstrate real PQC operations using `cryptography` / `liboqs` bindings |
| REPORT | Dashboard overview + downloadable JSON / PDF CBOM and migration roadmap |

---

## 3. Technology Stack

### Frontend
| Tool | Version | Role |
|------|---------|------|
| React | 18.x | UI Framework |
| TypeScript | 5.x | Type safety |
| Vite | 5.x | Build tool / dev server |
| Tailwind CSS | 3.x | Utility-first styling |
| Framer Motion | 11.x | Animations |
| Lucide React | latest | Icons |
| Recharts | 2.x | Dashboard charts |
| React Router DOM | 6.x | Client-side routing |

### Backend
| Tool | Version | Role |
|------|---------|------|
| Python | 3.14.x | Runtime (`py` launcher on Windows) |
| FastAPI | 0.115.x | REST API framework |
| Pydantic v2 | 2.x | Data validation / schemas |
| SQLAlchemy | 2.x | ORM |
| Alembic | 1.x | DB migrations |
| Uvicorn | latest | ASGI server |
| python-multipart | latest | File upload support |
| cryptography | 42.x | X.509 parsing + PQC demo ops |
| python-dotenv | latest | Environment variable management |
| aiofiles | latest | Async file I/O |

### Database
- **SQLite** (dev) — file: `backend/qshield.db`
- Structured for zero-effort migration to **PostgreSQL** (SQLAlchemy ORM, no raw SQL)

### Infrastructure (local dev)
- Backend: `http://localhost:8000` (Uvicorn)
- Frontend: `http://localhost:5173` (Vite dev server)
- CORS configured to allow localhost:5173

---

## 4. Architecture

```
QSheild/
├── frontend/               # React + Vite + TypeScript SPA
│   ├── src/
│   │   ├── components/     # Reusable UI components
│   │   ├── pages/          # Route-level page components
│   │   ├── hooks/          # Custom React hooks
│   │   ├── services/       # API client (axios/fetch wrappers)
│   │   ├── store/          # State management (Zustand or Context)
│   │   ├── types/          # Shared TypeScript interfaces
│   │   └── utils/          # Helpers / constants
│   ├── public/
│   ├── index.html
│   ├── package.json
│   ├── vite.config.ts
│   └── tailwind.config.ts
│
├── backend/                # Python FastAPI service
│   ├── app/
│   │   ├── main.py         # FastAPI app entry point, CORS, router registration
│   │   ├── config.py       # Settings (python-dotenv)
│   │   ├── database.py     # SQLAlchemy engine + session factory
│   │   ├── models/         # SQLAlchemy ORM models
│   │   ├── schemas/        # Pydantic v2 schemas (request/response)
│   │   ├── routers/        # FastAPI APIRouter modules
│   │   │   ├── scans.py    # Scan lifecycle endpoints
│   │   │   ├── findings.py # CBOM findings endpoints
│   │   │   ├── reports.py  # Report generation endpoints
│   │   │   └── health.py   # Health check
│   │   ├── services/       # Business logic (no FastAPI deps)
│   │   │   ├── scanner/    # Crypto discovery engine
│   │   │   ├── analyzer.py # Risk scoring engine
│   │   │   ├── recommender.py # NIST migration recommendations
│   │   │   └── reporter.py # CBOM / report assembly
│   │   └── utils/          # Shared helpers
│   ├── tests/              # pytest test suite
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   └── .env.example
│
├── PROJECT_CONTEXT.md      # ← This file
├── BUILD_PLAN.md           # Phase-by-phase implementation checklist
└── README.md
```

### Key Architectural Rules
1. **No duplicate logic** — frontend never re-implements backend detection/scoring.
2. **Scanner is pure Python** — no LLM, deterministic regex + AST + cert parsing.
3. **Risk scoring is deterministic** — algorithm weight table, configurable via constants.
4. **AI/LLM layer is optional and additive** — used only for narrative explanation of findings; never for detection.
5. **All file uploads are scanned in memory / temp dirs** — uploaded code is NEVER executed.

---

## 5. Security Rules

| Rule | Rationale |
|------|-----------|
| Never execute uploaded code | Supply chain attack surface elimination |
| No secrets in source code | All via `.env` / environment variables |
| Scan in isolated temp directories | Prevent path traversal |
| CORS restricted to known origins | Prevent CSRF |
| File type + size validation on upload | Prevent DoS / malicious payloads |
| No LLM for primary detection or risk scoring | Maintain determinism and audibility |
| Demo data explicitly labeled | Prevent confusion with real scan results |

---

## 6. Module List

| Module | Location | Status |
|--------|----------|--------|
| Crypto Scanner (Source Code) | `backend/app/services/scanner/source_scanner.py` | 🔴 Not built |
| Crypto Scanner (Certificates) | `backend/app/services/scanner/cert_scanner.py` | 🔴 Not built |
| Crypto Scanner (Config Files) | `backend/app/services/scanner/config_scanner.py` | 🔴 Not built |
| Risk Analyzer | `backend/app/services/analyzer.py` | 🔴 Not built |
| NIST Recommender | `backend/app/services/recommender.py` | 🔴 Not built |
| CBOM Reporter | `backend/app/services/reporter.py` | 🔴 Not built |
| Scan API Router | `backend/app/routers/scans.py` | 🔴 Not built |
| Findings API Router | `backend/app/routers/findings.py` | 🔴 Not built |
| Reports API Router | `backend/app/routers/reports.py` | 🔴 Not built |
| Dashboard Page | `frontend/src/pages/Dashboard.tsx` | 🔴 Not built |
| Scan Upload Page | `frontend/src/pages/ScanUpload.tsx` | 🔴 Not built |
| CBOM Viewer Page | `frontend/src/pages/CBOMViewer.tsx` | 🔴 Not built |
| Roadmap Page | `frontend/src/pages/Roadmap.tsx` | 🔴 Not built |
| PQC Demo Page | `frontend/src/pages/PQCDemo.tsx` | 🔴 Not built |
| Report Export Page | `frontend/src/pages/Reports.tsx` | 🔴 Not built |

---

## 7. Data Model

### Scan
```
Scan
  id: UUID (PK)
  name: str
  status: enum [queued, running, completed, failed]
  created_at: datetime
  completed_at: datetime | null
  file_count: int
  finding_count: int
  overall_risk_score: float (0-100)
  scan_type: enum [source_code, certificate, config, mixed]
```

### Finding (CBOM Entry)
```
Finding
  id: UUID (PK)
  scan_id: UUID (FK → Scan)
  file_path: str
  line_number: int | null
  algorithm: str                  # e.g. "RSA-2048", "AES-128-CBC", "ECDH-P256"
  algorithm_family: str           # e.g. "RSA", "ECC", "AES", "SHA"
  key_size: int | null
  usage_context: str              # e.g. "key_exchange", "signing", "encryption", "hashing"
  quantum_status: enum [vulnerable, safe, unknown, hybrid]
  risk_score: float (0-100)
  risk_factors: JSON              # dict of factor → contribution
  nist_recommendation: str        # FK to algorithm registry or inline
  confidence: float (0-1)        # detection confidence
  raw_snippet: str | null         # code snippet (sanitized)
```

### MigrationItem
```
MigrationItem
  id: UUID (PK)
  scan_id: UUID (FK → Scan)
  finding_id: UUID (FK → Finding)
  priority: int                   # 1 = highest
  effort_estimate: enum [low, medium, high]
  replacement_algorithm: str
  nist_standard: str              # e.g. "FIPS 203", "FIPS 204"
  migration_notes: str
  status: enum [pending, in_progress, completed]
```

### AlgorithmRegistry (static reference table, seeded)
```
AlgorithmRegistry
  id: str (PK)                    # e.g. "RSA"
  quantum_safe: bool
  nist_status: str                # "deprecated", "approved", "candidate"
  base_risk_weight: float
  recommended_replacement: str
  nist_reference: str
```

---

## 8. API Plan

All endpoints prefixed with `/api/v1`.

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/scans/` | Create & start scan (multipart file upload) |
| GET | `/scans/` | List all scans |
| GET | `/scans/{scan_id}` | Get scan details + status |
| DELETE | `/scans/{scan_id}` | Delete scan and findings |
| GET | `/scans/{scan_id}/findings` | List findings (CBOM) for a scan |
| GET | `/scans/{scan_id}/findings/{finding_id}` | Single finding detail |
| GET | `/scans/{scan_id}/roadmap` | Prioritized migration roadmap |
| GET | `/scans/{scan_id}/report` | Full CBOM report (JSON) |
| GET | `/scans/{scan_id}/report/pdf` | *(Phase 5)* PDF report download |
| GET | `/algorithms/` | Algorithm registry list |
| GET | `/algorithms/{algo_id}` | Algorithm detail + NIST info |

---

## 9. MVP Definition

The MVP is considered **complete** when a user can:
1. Upload one or more source code files (Python, Java, JS/TS).
2. See a scan run and complete (real detection, not mocked).
3. View a CBOM listing all cryptographic findings with risk scores.
4. Read a migration roadmap with NIST-aligned recommendations.
5. View a dashboard with aggregate risk metrics and charts.
6. Export the CBOM as JSON.

PQC demo (Kyber/ML-KEM key exchange demonstration) is a **bonus** feature included if time permits.

---

## 10. Technical Accuracy Rules

| Rule | Detail |
|------|--------|
| Algorithm Classification | Based on NIST IR 8547 and SP 800-131A classifications |
| Quantum-Vulnerable Algorithms | RSA (all key sizes), DSA, ECDSA, ECDH, DH, ElGamal — all classical asymmetric |
| Quantum-Safe Algorithms (NIST PQC) | ML-KEM (FIPS 203), ML-DSA (FIPS 204), SLH-DSA (FIPS 205), FN-DSA (FIPS 206) |
| Symmetric Keys | AES-256, ChaCha20 considered quantum-safe (Grover's halves keyspace — upgrade if <256-bit) |
| Hash Functions | SHA-256 = borderline safe; SHA-384/SHA-512 = safe; SHA-1/MD5 = deprecated |
| Risk Score Formula | `base_weight(algo) × key_size_factor × exposure_factor × usage_factor` — all configurable |
| Confidence Scoring | Regex match = 0.7; AST match = 0.9; cert parse = 1.0 |
| Demo Data Labeling | All seeded/demo data displayed with a yellow "DEMO DATA" badge in UI |
| No Hallucinated CVEs | Never reference specific CVEs without verified data |

---

*End of Project Context*

# QShield — Build Plan

> Checkbox legend: `[ ]` = todo · `[/]` = in progress · `[x]` = complete  
> Each phase must pass its verification step before the next phase begins.

---

## Phase 0 — Foundation & Project Structure ✅

- [x] Inspect existing repository
- [x] Confirm runtime availability (Node v24, Python 3.14, npm 11.8)
- [x] Create `PROJECT_CONTEXT.md` (source of truth)
- [x] Create `BUILD_PLAN.md` (this file)
- [x] Scaffold backend directory structure (`backend/app/...`)
- [x] Create `backend/requirements.txt`
- [x] Create `backend/.env.example`
- [x] Create `backend/app/main.py` (minimal FastAPI app — health endpoint only)
- [x] Create `backend/app/config.py`
- [x] Create `backend/app/database.py` (SQLAlchemy + SQLite)
- [x] Create `backend/app/models/__init__.py` (empty placeholder)
- [x] Create `backend/app/routers/health.py`
- [x] Scaffold frontend with Vite + React + TypeScript + Tailwind
- [x] Verify backend starts: `GET /health → 200 OK`
- [x] Verify frontend builds / dev server starts
- [x] Create `README.md`

---

## Phase 1 — Backend + Database Foundation ✅

- [x] Organization, Project, Application, Asset, Scan, CryptoFinding, RiskAssessment, MigrationRecommendation, RoadmapItem, Report ORM models
- [x] Application business context fields: criticality, environment, internet exposure, data sensitivity, confidentiality horizon, data_lifetime_years
- [x] Pydantic v2 schemas (create/update/response) for all entities
- [x] REST API: `/api/organizations`, `/api/projects`, `/api/applications`, `/api/scans`, `/api/scans/{id}/status`, `/api/findings`
- [x] CRUD with pagination, 404 handling, structured errors, correct HTTP status codes
- [x] Stub endpoints: `/api/risk`, `/api/roadmap`, `/api/pqc-lab`, `/api/reports`
- [x] CORS, env config, `.env.example`, no committed secrets
- [x] Frontend API client (`services/api.ts`, `services/projectsApi.ts`)
- [x] Onboarding flow: Landing → `/scan` → Org+Project+App creation → `/upload`
- [x] 26 passing pytest tests (health + Phase 1 CRUD)
- [x] **Verification:** `pytest tests/` — 47 passed; `npm run build` — clean

---

## Phase B — Secure File Ingestion ✅

- [x] `app/services/ingestion.py` — secure ingestion service
  - [x] Extension allowlist (`.py .js .ts .java .cs .json .yaml .yml .xml .properties .conf .config .pem .crt .cer`)
  - [x] ZIP extraction with path-traversal prevention (ZIP-slip, `../`, absolute paths)
  - [x] Reject malformed ZIP, empty archives
  - [x] Configurable max upload size; reject oversized uploads
  - [x] Filename sanitization (strip directory components)
  - [x] Temp dir cleanup in all exit paths (success and error)
  - [x] No file execution, no sensitive content logging
- [x] `POST /api/scans/upload` — multipart upload endpoint
  - [x] Validates application_id reference
  - [x] Creates Scan record (running → completed | failed)
  - [x] Returns structured scan metadata (id, status, file_count, upload_name, upload_type)
  - [x] `GET /api/scans/{id}/status` returns upload metadata
- [x] Scan model extended: `upload_name`, `upload_type` fields
- [x] `UploadPage.tsx` — drag-drop + file select, progress bar, success/error states
  - [x] Shows file_count, scan_id, upload_type after success
  - [x] "Files securely processed and ready for cryptographic analysis" — no fake results
- [x] App.tsx wired: `/scan` → OnboardingPage → `/upload` → UploadPage
- [x] 21 security tests (unit + HTTP): traversal, absolute path, oversized, empty, malformed, cleanup, invalid app ref
- [x] **Verification:** `pytest tests/` — 47 passed; `npm run build` — clean

---


- [ ] Design scanner plugin interface (`BaseScanner`)
- [ ] Build **Source Code Scanner** (`source_scanner.py`)
  - [ ] Python: regex + `ast` module detection
  - [ ] JavaScript/TypeScript: regex patterns
  - [ ] Java: regex patterns
  - [ ] Generic: common crypto string patterns (any language)
  - [ ] Return structured `Finding` objects with file + line + snippet + confidence
- [ ] Build **Certificate Scanner** (`cert_scanner.py`)
  - [ ] Parse X.509 PEM/DER using `cryptography` library
  - [ ] Extract algorithm, key size, validity, subject
  - [ ] Confidence = 1.0 (parsed from cert, not guessed)
- [ ] Build **Config File Scanner** (`config_scanner.py`)
  - [ ] Detect cipher suite strings in YAML/JSON/TOML/.conf/.ini/.env
  - [ ] Detect TLS version settings
- [ ] Unit tests for each scanner with real sample inputs
- [ ] **Verification:** All scanner tests pass with correct detections

---

## Phase 3 — Scan API Endpoints (DISCOVER → INVENTORY)

- [ ] Implement `POST /api/v1/scans/` — multipart file upload, creates Scan record, triggers scanner
  - [ ] File type validation (allowlist)
  - [ ] File size limit (configurable, default 10MB per file)
  - [ ] Run scanner in background (FastAPI BackgroundTasks)
  - [ ] Save findings to DB
- [ ] Implement `GET /api/v1/scans/` — paginated scan list
- [ ] Implement `GET /api/v1/scans/{scan_id}` — scan detail + status
- [ ] Implement `DELETE /api/v1/scans/{scan_id}`
- [ ] Implement `GET /api/v1/scans/{scan_id}/findings` — paginated CBOM
- [ ] Implement `GET /api/v1/scans/{scan_id}/findings/{finding_id}`
- [ ] Integration tests for scan lifecycle
- [ ] **Verification:** End-to-end test: upload sample file → get findings

---

## Phase 4 — Risk Analyzer & Recommender (ANALYZE + PRIORITIZE + MIGRATE)

- [ ] Implement `analyzer.py`
  - [ ] Risk score formula: `base_weight × key_size_factor × exposure_factor × usage_factor`
  - [ ] Per-finding risk score calculation
  - [ ] Aggregate scan risk score
  - [ ] Explainable output (risk_factors dict per finding)
- [ ] Implement `recommender.py`
  - [ ] Map each quantum-vulnerable algorithm to NIST PQC replacement
  - [ ] Generate `MigrationItem` records
  - [ ] Prioritize by risk score + usage context
- [ ] Implement `GET /api/v1/scans/{scan_id}/roadmap`
- [ ] Unit tests for risk scoring with known inputs
- [ ] **Verification:** RSA-2048 key exchange scores high risk; AES-256 scores low

---

## Phase 5 — Frontend Core (Dashboard + Upload + CBOM Viewer)

- [ ] Set up React Router with routes: `/`, `/scan`, `/scans/:id`, `/scans/:id/cbom`, `/scans/:id/roadmap`, `/reports`
- [ ] Create reusable UI components
  - [ ] `Layout` (sidebar nav + header)
  - [ ] `RiskBadge` (color-coded risk level chip)
  - [ ] `AlgorithmBadge` (quantum-safe / vulnerable / unknown)
  - [ ] `DemoDataBanner` (yellow banner for demo data)
  - [ ] `StatusIndicator` (scan status with polling)
- [ ] Build **Dashboard page** (`/`)
  - [ ] Aggregate risk donut chart
  - [ ] Findings by algorithm family bar chart
  - [ ] Recent scans table
- [ ] Build **Scan Upload page** (`/scan`)
  - [ ] Drag-and-drop file upload (multiple files)
  - [ ] File type indicators
  - [ ] Scan progress indicator (polling)
- [ ] Build **CBOM Viewer page** (`/scans/:id/cbom`)
  - [ ] Sortable, filterable findings table
  - [ ] Risk score column with color coding
  - [ ] Click-through to finding detail
- [ ] **Verification:** Frontend connects to backend; real scan data displayed

---

## Phase 6 — Migration Roadmap & Reports (VALIDATE + REPORT)

- [ ] Build **Roadmap page** (`/scans/:id/roadmap`)
  - [ ] Prioritized migration cards
  - [ ] NIST standard badges
  - [ ] Effort indicators
- [ ] Build **Reports page** (`/reports`)
  - [ ] JSON CBOM export (`GET /api/v1/scans/{scan_id}/report`)
  - [ ] Report metadata display
- [ ] Implement `reporter.py`
  - [ ] Assemble full CBOM JSON (OWASP CycloneDX-compatible format where feasible)
  - [ ] Scan summary statistics
- [ ] **Verification:** JSON report downloads correctly; roadmap shows ordered items

---

## Phase 7 — PQC Demo (VALIDATE — Bonus)

- [ ] Research liboqs-python availability for Python 3.14
- [ ] If liboqs unavailable: use `cryptography` lib for available PQC primitives
- [ ] Implement `/api/v1/demo/pqc`
  - [ ] ML-KEM key generation + encapsulation demo (or available equivalent)
  - [ ] Compare with classical RSA for timing
- [ ] Build **PQC Demo page** (`/demo`)
  - [ ] Side-by-side: classical vs. PQC
  - [ ] Clear "DEMO" label on all demo operations
- [ ] **Verification:** Demo runs without error; clearly labeled as demonstration

---

## Phase 8 — Polish & Hackathon Readiness

- [ ] Responsive design audit (works on 1080p + laptops)
- [ ] Error handling audit (API errors shown properly in UI)
- [ ] Loading states for all async operations
- [ ] Seed database with a complete demo scan (labeled as DEMO DATA)
- [ ] Write `README.md` with setup instructions
- [ ] Record demo walkthrough video or screenshots
- [ ] Final end-to-end test: fresh clone → `pip install` → `npm install` → both services start → upload file → get CBOM
- [ ] **Verification:** Judges can run the project from README instructions alone

---

## Current Status

| Phase | Status | Notes |
|-------|--------|-------|
| Phase 0 | ✅ Complete | Foundation established |
| Phase 1 | ⏳ Next | Database models + algorithm registry |
| Phase 2 | 🔴 Pending | Scanner engine |
| Phase 3 | 🔴 Pending | Scan API |
| Phase 4 | 🔴 Pending | Risk + recommendations |
| Phase 5 | 🔴 Pending | Frontend |
| Phase 6 | 🔴 Pending | Roadmap + Reports |
| Phase 7 | 🔴 Pending | PQC demo (bonus) |
| Phase 8 | 🔴 Pending | Polish |

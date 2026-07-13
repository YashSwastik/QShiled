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

- [x] **Phase C — Crypto Discovery Engine** ✅
  - [x] `app/services/scanner/rules.py` — rule registry (RSA, ECC, ECDSA, ECDH, DH, DSA, AES, ChaCha20, SHA-2, SHA-3, SHA-1, MD5, DES, RC4, ML-KEM, ML-DSA, SLH-DSA, FN-DSA, TLS)
  - [x] `app/services/scanner/source_scanner.py` — multi-language regex + Python AST scanner
  - [x] `app/services/scanner/cert_scanner.py` — X.509 cert + PEM key parser (cryptography lib, confidence=1.0)
  - [x] `app/services/scanner/engine.py` — orchestrator (cert → source fallback)
  - [x] `app/services/ingestion.py` — extended: `file_contents` dict returned alongside metadata
  - [x] `app/routers/upload.py` — full pipeline: ingest → scan → persist findings → return finding_count
  - [x] `app/models/finding.py` — added `FindingCategory` enum + `category` column
  - [x] Correct quantum classification: RSA/ECDSA/DH = vulnerable; AES-256/SHA-512 = safe; MD5/SHA-1 = legacy_deprecated (NOT quantum-vulnerable)
  - [x] Evidence masking (PEM body, hex literals, line length limit)
  - [x] 107 passing tests (107/107)

- [x] **Phase D — CBOM Inventory UI** ✅
  - [x] `GET /api/findings` — extended: category, search, sort_by, sort_dir filters
  - [x] `GET /api/findings/summary` — aggregate counts by category, quantum_status, algorithm_family
  - [x] `GET /api/findings/{id}` — full finding detail
  - [x] `frontend/src/services/inventoryApi.ts` — typed API client
  - [x] `frontend/src/components/FindingBadges.tsx` — CategoryBadge, QuantumBadge, ConfidenceBar, DetectionMethodLabel
  - [x] `frontend/src/pages/InventoryPage.tsx` — CBOM table: search, filter, sort, paginate; summary cards; empty/loading/error states
  - [x] `frontend/src/pages/FindingDetailPage.tsx` — per-finding deep-dive: classification, source location, masked evidence, detection method, quantum explanation (separate from legacy warning)
  - [x] UploadPage success → navigate to `/inventory/:scanId` with finding_count
  - [x] `App.tsx` routes: `/inventory/:scanId` and `/inventory/:scanId/finding/:findingId`
  - [x] `npm run build` — clean (0 errors, 107 backend tests pass)

---

- [x] **Phase E — Quantum Migration Risk Engine** ✅
  - [x] `app/services/analyzer.py` — QShield Explainable Migration Prioritization Methodology
    - [x] 6-factor deterministic weighted scoring (no LLM): crypto_vulnerability (30%), confidentiality (20%), business_criticality (20%), external_exposure (15%), migration_complexity (10%), compliance_sensitivity (5%)
    - [x] Crypto-vulnerability gate: quantum-safe (AES-256, ML-KEM) and classical/legacy (MD5, SHA-1) algorithms suppressed from inflating quantum migration priority; explained in API response
    - [x] Strict separation: Quantum Migration Risk vs Classical/Legacy Security Risk (two separate fields)
    - [x] Full explainability: `raw_weighted_sum`, `crypto_vulnerability_gate`, `quantum_migration_score` all exposed
    - [x] Human-readable factor labels, per-factor rationale, deterministic explanation string
    - [x] Gate note appended to explanation when suppression > 10 points
    - [x] FACTOR_LABELS dict for UI rendering
    - [x] Severity bands: Low (0–34) / Moderate (35–54) / High (55–74) / Critical (75–100)
    - [x] Migration priority: immediate / near_term / long_term / low
    - [x] Empty-scan safe: returns score=0.0, severity=Low, summary text
    - [x] Missing business context: documented neutral defaults, `context_defaulted=True` flag in response
  - [x] `app/models/risk_assessment.py` — extended: overall_severity, legacy_count, per_finding_scores, top_priority_finding_ids, methodology_version
  - [x] `app/database.py` — `_safe_migrate_sqlite()`: idempotent ADD COLUMN for new nullable columns (existing DBs never broken)
  - [x] `app/schemas/risk.py` — FactorScoreSchema (with label), FindingRiskSchema (with raw_weighted_sum, gate), ScanRiskResponse (with methodology, disclaimer, context_defaulted)
  - [x] `app/routers/risk.py` — real `GET /api/risk?scan_id=` (replaces stub): loads findings + app context, runs analyzer, persists RiskAssessment, returns full response
  - [x] `app/routers/upload.py` — integrates risk analysis step 6 after scan completion: findings → analyzer → persist RiskAssessment automatically
  - [x] `app/main.py` — stub `risk_router` replaced with `risk_router_module.router`
  - [x] `frontend/src/services/riskApi.ts` — typed API client for risk endpoint
  - [x] `frontend/src/pages/RiskPage.tsx` — Risk Analysis page: score gauge, factor breakdown bars, quantum vs classical/legacy separation, gate transparency panel, per-finding expandable cards, NIST recommendations, app context display, loading/error/empty states
  - [x] `frontend/src/pages/InventoryPage.tsx` — "Risk Analysis" CTA button in header → `/risk/:scanId`
  - [x] `frontend/src/App.tsx` — route `/risk/:scanId` wired
  - [x] `tests/test_analyzer.py` — 54 new tests across 10 test classes
  - [x] **Verification:** `pytest tests/` — **161/161 passed**; `npm run build` — clean (0 errors)

---

## Current Status

| Phase | Status | Notes |
|-------|--------|-------|
| Phase 0 | ✅ Complete | Foundation |
| Phase 1 | ✅ Complete | Backend + Database |
| Phase B | ✅ Complete | Secure File Ingestion |
| Phase C | ✅ Complete | Crypto Discovery Engine (107 tests) |
| Phase D | ✅ Complete | CBOM Inventory UI + API |
| Phase E | ✅ Complete | Quantum Migration Risk Engine (161 tests) |
| Phase 5 | 🟡 Partial | Dashboard (placeholder), Upload+Inventory done |
| Phase 6 | 🔴 Pending | Migration Recommendations + Roadmap |
| Phase 7 | 🔴 Pending | Reports |
| Phase 8 | 🔴 Pending | PQC demo (bonus) |
| Phase 9 | 🔴 Pending | Polish |

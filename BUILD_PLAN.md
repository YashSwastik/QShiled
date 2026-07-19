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

- [x] **Phase F — Migration Recommendation Engine** ✅
  - [x] `app/services/kb/knowledge_base.py` — versioned, curated Migration Knowledge Base (v1.0)
    - [x] Covers: RSA (key-establishment + signature), ECDSA, ECDH, ECC, DH, DSA, AES, ChaCha20, SHA-2, SHA-3, MD5, SHA-1, ML-KEM, ML-DSA, SLH-DSA, FN-DSA
    - [x] Each entry: quantum_threat, recommended_target_category, recommended_algorithms, nist_standards, effort_estimate, prerequisites, migration_steps, testing_requirements, interoperability_notes, validation_checklist, timeline_guidance, technical_notes
    - [x] NIST technically accurate: ML-KEM (FIPS 203) → key establishment only; ML-DSA (FIPS 204) / SLH-DSA (FIPS 205) / FN-DSA (FIPS 206) → digital signatures only
    - [x] Symmetric/hash algorithms explicitly NOT treated as Shor-vulnerable
  - [x] `app/services/kb/purpose_classifier.py` — deterministic cryptographic-purpose classifier
    - [x] Unambiguous families (ECDSA, ECDH, DSA, DH, AES, ChaCha20, SHA-2, SHA-3, MD5, SHA-1, all PQC) classified by definition alone
    - [x] RSA ambiguity resolved: signing contexts → digital_signature; encryption/key-transport contexts → key_establishment; no context → PURPOSE_UNKNOWN + manual review flag
    - [x] RSA `usage_context="encryption"` correctly identified as asymmetric key-transport (not symmetric cipher), mapped to key_establishment migration path
    - [x] ECC ambiguity resolved: ECDH via context → key_establishment; ECDSA via context → digital_signature; no context → PURPOSE_UNKNOWN
    - [x] Evidence keyword hints as low-confidence fallback for RSA/ECC
    - [x] Never invents purpose when evidence is insufficient
  - [x] `app/services/recommender.py` — deterministic recommendation engine
    - [x] Per-finding: classify purpose → look up KB → build structured MigrationRecommendation
    - [x] Consumes Part 7 migration_priority and quantum_migration_score (never recalculates)
    - [x] Unknown purpose → manual review, empty recommended_algorithms, no invented target
    - [x] Scan-level aggregation: sorted by Part 7 priority, then by quantum_migration_score
    - [x] No LLM. No second risk methodology. Fully deterministic.
  - [x] `app/schemas/recommendation.py` — Pydantic v2 API schemas
  - [x] `app/routers/recommendations.py` — `GET /api/recommendations?scan_id=`
    - [x] Loads completed scan + findings from DB
    - [x] Reads persisted Part 7 per-finding scores from RiskAssessment (no recalculation)
    - [x] Returns ScanRecommendationResponse
  - [x] `app/main.py` — recommendations router registered at `/api/recommendations`
  - [x] `tests/test_recommender.py` — 49 comprehensive tests
    - [x] Purpose classifier: ECDSA, ECDH, AES, SHA-2, MD5, SHA-1, DH, DSA, RSA signing, RSA key-exchange, RSA encryption, RSA no-context (unknown), ECC no-context (unknown), ML-KEM, ML-DSA
    - [x] Recommender: RSA→KEM, RSA→sig (never ML-KEM), ECDSA→sig (never ML-KEM), AES not quantum-vulnerable, ChaCha20 not quantum-vulnerable, unknown→manual review+empty algorithms, unknown→no invented target, determinism (×2), RSA-sig ML-KEM strict, RSA-KEM no signature category, ECDSA never ML-KEM, symmetric not Shor-labelled, ECDH, DH, DSA, MD5, SHA-1, PQC already safe, Part 7 priority passthrough, no-priority returns None
    - [x] Scan-level: mixed findings, empty scan, priority sort, determinism, KB version in summary
  - [x] `frontend/src/services/recommendationsApi.ts` — typed API client
  - [x] `frontend/src/pages/RecommendationsPage.tsx` — Migration recommendations UI
    - [x] Sidebar (matches RiskPage), summary strip, filter tabs (All / Quantum / Safe / Review)
    - [x] Expandable rows: purpose, confidence, current state, quantum threat, purpose reasoning, target + algorithms, prerequisites, migration steps, testing requirements, interoperability notes, timeline, technical notes, validation checklist, KB provenance, link to finding detail
    - [x] Light enterprise SaaS design: white/off-white surfaces, subtle borders, semantic colours, restrained purple accent
  - [x] `frontend/src/App.tsx` — route `/recommendations/:scanId` wired
  - [x] `frontend/src/pages/RiskPage.tsx` — Migration sidebar link enabled; "Migration Plan →" CTA button in header
  - [x] **Verification:** `pytest tests/` — **210/210 passed** (161 baseline + 49 new); `npm run build` — clean (0 errors)

---

- [x] **Phase G — Migration Roadmap Engine** ✅
  - [x] `app/services/roadmap_engine.py` — deterministic wave-assignment engine
    - [x] Consumes Part 7 risk scores/migration_priority (never recalculates them)
    - [x] Consumes Part 8 recommendation engine (purpose + KB effort)
    - [x] Consumes application context (internet_exposed, confidentiality_requirement, business_criticality)
    - [x] Wave 1: immediate priority OR score ≥ 65 OR (quantum + internet + long_term) → Critical
    - [x] Wave 2: near_term priority OR score 40–64 OR (quantum + high/critical criticality) → High
    - [x] Wave 3: long_term/low priority OR score < 40 → Planned
    - [x] Context elevation: internet-facing + long_term + quantum concern → always Wave 1
    - [x] Criticality elevation: critical/high business + quantum → Wave 3 → Wave 2
    - [x] Symmetric/legacy findings not elevated by internet_exposed rule (not Shor-vulnerable)
    - [x] Per-item: deterministic reason, recommended_action (from Part 8 KB), dependency detection
    - [x] Wave summaries (count + description)
    - [x] Ordered: wave ASC, then quantum_migration_score DESC
    - [x] No hardcoded roadmap items whatsoever
  - [x] `app/schemas/roadmap_schema.py` — Pydantic v2 API schemas (ScanRoadmapResponse, RoadmapItemSchema, WaveSummarySchema, RoadmapItemStatusUpdate)
  - [x] `app/routers/roadmap.py` — real roadmap API (replaces stub)
    - [x] `GET /api/roadmap?scan_id=` — generates roadmap from live data; overlays persisted user stage
    - [x] `PATCH /api/roadmap/items/{finding_id}` — forward-only stage transitions; returns 422 on invalid/backward stage
    - [x] Stage persisted to `roadmap_items` table; survives roadmap recalculation
    - [x] User progress preserved: wave recalculates from current upstream data, stage kept
    - [x] Upsert idiom: new findings get DISCOVERED; existing rows keep user stage
  - [x] `app/database.py` — `roadmap_items.stage VARCHAR(32)` added via `_safe_migrate_sqlite()`
  - [x] `app/main.py` — real roadmap router registered; stub removed
  - [x] `tests/test_roadmap.py` — 38 focused tests
    - [x] Wave 1: immediate priority, internet+long_term elevation, score ≥ 65, Immediate action prefix
    - [x] Wave 2: near_term priority, score 40–64, critical-criticality elevation, Near-term prefix
    - [x] Wave 3: low/long_term priority, Planned prefix
    - [x] Symmetric (AES-256, AES-128) and legacy (MD5, SHA-1) NOT Wave 1 even with critical internet context
    - [x] Application context sensitivity: same finding, different context → different wave
    - [x] Risk score sensitivity: score < 40 → Wave 3; score > 65 → Wave 1
    - [x] Recommendation consumed: algorithms come from Part 8 KB; manual review → correct action
    - [x] Stage transitions: advance_stage() correct 7-step lifecycle; MIGRATED → None
    - [x] Invalid stages not in VALID_STAGES
    - [x] Determinism: same input → same wave, algorithms, action (×2)
    - [x] Empty scan: 0 items, 0 per wave summary
    - [x] HTTP API: 404 unknown scan, 404 no roadmap item, 422 invalid stage
  - [x] `tests/test_phase1.py` — updated stub test: `/api/roadmap` now requires scan_id (422, not 200)
  - [x] `frontend/src/services/roadmapApi.ts` — typed API client (getRoadmap, updateRoadmapItemStage, MIGRATION_STAGES)
  - [x] `frontend/src/pages/RoadmapPage.tsx` — Migration Roadmap UI
    - [x] Wave 1/2/3 groups with semantic colour-coded borders and badges
    - [x] Expandable item cards: wave reason, recommended action, target algorithms, NIST standards, dependencies, stage timeline
    - [x] Stage selector: forward-only dropdown; optimistic update + backend PATCH; error display
    - [x] Stage lifecycle visualisation: ✓ done / current / future pills
    - [x] Wave summary strip (count + wave description)
    - [x] Sidebar (matching RiskPage/RecommendationsPage), header CTA buttons
    - [x] Loading / error / empty states
    - [x] No hardcoded wave assignments or recommendation content
  - [x] `frontend/src/App.tsx` — route `/roadmap/:scanId` wired
  - [x] `frontend/src/pages/RiskPage.tsx` — Roadmap nav item + "Roadmap" CTA header button
  - [x] `frontend/src/pages/RecommendationsPage.tsx` — Roadmap nav item + "Roadmap" CTA header button
  - [x] **Stage Persistence Bug Fix:**
    - **Root cause:** `_load_stage_overrides` returned `{finding_id: row.status}` where `row.status` is the 4-value ORM enum (`pending`/`in_progress`/`completed`/`deferred`). Those values are NOT in `VALID_STAGES` (the 7-step canonical strings). The overlay silently nooped and roadmap regeneration reset each item to `DISCOVERED`.
    - **Fix:** Added `stage: Mapped[str]` column (VARCHAR 32, default `DISCOVERED`) to `RoadmapItem` ORM model. PATCH now writes `row.stage = new_stage` (canonical string). `_load_stage_overrides` now reads `row.stage`. `_persist_roadmap_items` sets `stage="DISCOVERED"` on new rows only — never overwrites `stage` for existing rows.
    - **Test setup fix:** Helper `_create_completed_scan_with_findings` was using production `SessionLocal`; corrected to `tests.conftest.TEST_SESSION` (same DB as TestClient).
  - [x] **Regression tests (`TestStagePersistenceRegression`, 5 tests):**
    - `test_a_new_item_starts_discovered` — new item defaults to DISCOVERED
    - `test_b_patched_stage_survives_get` — PATCH ASSESSED → GET → still ASSESSED (the exact regression)
    - `test_c_recalculation_preserves_planned` — PATCH PLANNED → GET twice → still PLANNED
    - `test_d_backward_stage_rejected` — backward transition rejected with 422
    - `test_e_invalid_stage_value_422` — invalid stage value rejected with 422
  - [x] **Roadmap UI improvements:**
    - `WaveTimeline` component: horizontal NOW → NEXT → LATER cards with arrow connectors; large item-count, priority label, and time-horizon description from backend `wave_summaries`; stacks gracefully on narrow screens
    - `LifecycleBar` component: 7 connected stage nodes (DISCOVERED…MIGRATED) with bubble showing real per-stage counts from persisted roadmap items; grey when empty, coloured when items at that stage
    - `StageSelector` updated: non-optimistic — waits for backend PATCH response, updates UI from `updated.status` returned by server; shows "Saving…" while in-flight; does not falsely display a stage on failure
  - [x] **Verification:** `pytest tests/` — **253/253 passed** (210 baseline + 43 roadmap incl. 5 persistence); `npm run build` — clean (0 errors, exit 0)

---

## Phase H — Executive Dashboard ✅

### Architecture

Single aggregated backend endpoint (`GET /api/dashboard?scan_id=<id>`) derives all
dashboard metrics from real persisted DB state.  No data is fabricated or re-calculated
outside the existing engines.

#### Backend

| File | Purpose |
|------|---------|
| `app/routers/dashboard.py` | New router; aggregates findings, risk, roadmap from DB |
| `app/main.py` | Registered `dashboard_router` at `/api/dashboard` |
| `tests/test_dashboard.py` | 26 focused dashboard tests |

**Endpoints:**
- `GET /api/dashboard/scans` — list all scans with application name (for selector)
- `GET /api/dashboard?scan_id=<id>` — full aggregated dashboard summary

**Data sources (all real DB reads, no engine re-invocation):**
| Metric | Source |
|--------|--------|
| Total / vulnerable / safe findings | `crypto_findings` table |
| Algorithm distribution | `crypto_findings.algorithm_family` counts |
| Severity distribution | `risk_assessments.per_finding_scores[].quantum_migration_severity` |
| Avg risk score | `risk_assessments.per_finding_scores[].quantum_migration_score` |
| Migration progress / stage counts | `roadmap_items.stage` (canonical persisted column) |
| Wave distribution | `roadmap_items.priority` (1/2/3 set by roadmap engine) |
| Top findings | highest `quantum_migration_score` with linked `finding_id` |
| Top assets | application aggregation from findings + roadmap |
| Scan metadata | `scans` table |

#### Quantum Readiness Score

**QShield Deterministic Readiness Indicator — NOT an official NIST score or compliance certification.**

```
S_exposure = (total_findings − quantum_vulnerable_findings) / total_findings
             → 1.0 when total_findings = 0

S_risk_inv = 1 − (avg_quantum_migration_score / 100)
             → 1.0 when no per-finding risk scores exist

S_progress  = migrated_roadmap_items / total_roadmap_items
             → 1.0 when total_roadmap_items = 0

Quantum Readiness Score = round(
    60 × S_exposure
  + 25 × S_risk_inv
  + 15 × S_progress
)  clamped to [0, 100]
```

Readiness labels:

| Score | Label |
|-------|-------|
| 90–100 | High Readiness |
| 70–89  | Moderate-High Readiness |
| 50–69  | Moderate Readiness |
| 30–49  | Limited Readiness |
| 0–29   | Low Readiness |

Score is **live**: adding a vulnerable finding decreases it; advancing a roadmap item to
MIGRATED increases it; removing risk scores resets it deterministically.

#### Frontend

| File | Purpose |
|------|---------|
| `src/services/dashboardApi.ts` | Typed API client (`listDashboardScans`, `getDashboardSummary`) |
| `src/pages/Dashboard.tsx` | Full executive dashboard page |
| `src/App.tsx` | Route `/app/dashboard` wired |

**UI structure:**
1. **Readiness Hero** — SVG ring gauge, score, readiness label, expandable methodology panel (shows exact formula components per scan)
2. **Posture Summary** — compact 5-metric strip (Total / Quantum Relevant / Critical / High / Safe); scan name, completion date, status badge
3. **Security Posture Analytics** — Algorithm Distribution (ranked horizontal bars) + Risk/Severity Distribution (semantic horizontal bars); both link to Inventory / Risk Analysis
4. **Migration Status** — progress bar, 7-node lifecycle display with real per-stage counts from `roadmap_items.stage`, wave summary (Wave 1 NOW / Wave 2 NEXT / Wave 3 LATER); links to Roadmap
5. **Priority Attention** — Top Priority Assets (severity + relevant findings + wave) + Highest-Risk Findings (algorithm, file, risk score, severity — each row links to finding detail)
6. **Scan selector** — dropdown for all known scans; auto-selects most recent completed scan

**Implemented states:**
- ✅ Loading (skeleton layout matching dashboard structure)
- ✅ Empty project / no scans (onboarding state: "No security posture data yet" + Run First Scan)
- ✅ API error (contained error panel with Retry)
- ✅ Scanning in progress (compact info banner)
- ✅ Completed scan with no crypto findings (informational notice; readiness = 100 by formula)
- ✅ Multiple findings / multiple risk levels
- ✅ Responsive layout (wrapping flex, scrollable lifecycle)
- ✅ Accessible: ARIA roles on charts, progressbar roles, aria-labels on controls

**Navigation — all buttons lead to working existing pages:**
- Readiness → Risk Analysis
- Algorithm Distribution → Crypto Inventory
- Risk Distribution → Risk Analysis
- Migration Progress → Migration Roadmap
- Top Finding rows → Finding Detail (`/inventory/:scanId/finding/:id`)
- Run New Scan → `/scan` (Onboarding)

### Testing

- **Focused dashboard tests:** 26/26 passed (`tests/test_dashboard.py`)
  - Empty project (no scans)
  - Completed scan, no findings (readiness = 100)
  - Vulnerable findings reduce readiness
  - Safe findings increase readiness
  - Severity distribution from persisted RiskAssessment
  - Multiple risk levels
  - _compute_readiness formula unit tests (7 cases)
  - Readiness decreases when finding added
  - Readiness increases when roadmap stage advanced to MIGRATED
  - Stage distribution reflects persisted stages
  - Wave distribution matches roadmap priority field
  - Dashboard GET does NOT reset roadmap stages (regression guard)
  - 404 on unknown scan_id
- **Full backend suite:** 279/279 passed
- **Frontend:** `npm run build` — clean, exit 0, 0 TypeScript errors

---

## Phase I — PQC Lab ✅

### Architecture

Real post-quantum cryptographic operations using `cryptography` 49.0.0 (PyCA / OpenSSL 3.x backend).
No additional PQC library installed — the existing project dependency is sufficient.
All operations are ephemeral in-memory. No private keys, shared secrets, or sensitive material
is persisted, returned in API responses, or logged.

### Library

| Item | Detail |
|---|---|
| Library | `cryptography` (PyCA) |
| Version | 49.0.0 |
| OpenSSL backend | Yes (via rust_openssl bindings) |
| Platform | Windows 11, Python 3.14.3 |
| New dependency added | None |

### Implemented Algorithms

#### ML-KEM (FIPS 203) — Key Encapsulation Mechanism

| Parameter Set | Public Key | Ciphertext | Shared Secret | Security Level |
|---|---|---|---|---|
| ML-KEM-768 | 1184 B | 1088 B | 32 B | Level 3 (AES-192) |
| ML-KEM-1024 | 1568 B | 1568 B | 32 B | Level 5 (AES-256) |

Operations: key generation · encapsulation · decapsulation · shared-secret equality verification

**API note:** `pub_key.encapsulate()` returns `(shared_secret, ciphertext)` — shared_secret is the first element.

#### ML-DSA (FIPS 204) — Digital Signatures

| Parameter Set | Public Key | Max Signature | Security Level |
|---|---|---|---|
| ML-DSA-44 | 1312 B | 2420 B | Level 2 (AES-128) |
| ML-DSA-65 | 1952 B | 3309 B | Level 3 (AES-192) |
| ML-DSA-87 | 2592 B | 4627 B | Level 5 (AES-256) |

Operations: key generation · signing · verification · tampered-message verification failure

#### SLH-DSA (FIPS 205)

Not available in the current `cryptography` build on this platform.
Shown as explicitly unavailable in the UI. No fake controls provided.

### Measurement Methodology

- All timings: `time.perf_counter()` (Python standard library)
- Measurements are single-run or multi-iteration (5/10/25/50) — environment-specific
- Returns: avg_ms, min_ms, max_ms for benchmark mode
- Disclaimer shown in UI: results depend on hardware, OS, runtime, system load, benchmark methodology

### Backend Files

| File | Role |
|---|---|
| `app/services/pqc_lab_service.py` | Service layer — all cryptographic operations, benchmarking, capability discovery |
| `app/routers/pqc_lab.py` | API router — capabilities, KEM demo, signature demo, benchmark |
| `app/main.py` | Replaced stub `pqc_lab_router` with real `pqc_lab_router_module.router` |
| `tests/test_pqc_lab.py` | 62 focused tests |
| `tests/test_phase1.py` | Updated legacy stub assertion to verify real capabilities endpoint |

### API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `GET /api/pqc-lab/capabilities` | GET | Supported algorithms, parameter sets, environment metadata |
| `POST /api/pqc-lab/kem/demo` | POST | ML-KEM round-trip — keygen, encap, decap, shared-secret verify |
| `POST /api/pqc-lab/signature/demo` | POST | ML-DSA sign + verify + optional tamper test |
| `POST /api/pqc-lab/benchmark` | POST | Bounded multi-iteration benchmark (5/10/25/50 iterations only) |

### Frontend Files

| File | Role |
|---|---|
| `src/services/pqcLabApi.ts` | Typed API client for all four PQC Lab endpoints |
| `src/pages/DemoPage.tsx` | Full PQC Lab interactive workspace |
| `src/App.tsx` | Route `/demo` already wired |

### UI Structure (implemented)

1. **Header / Runtime Status**: real library, version, Python, platform, backend readiness from `/api/pqc-lab/capabilities`
2. **Algorithm Family Selector**: ML-KEM (supported), ML-DSA (supported), SLH-DSA (explicitly unavailable, disabled card)
3. **Parameter Set Selector**: populated from backend capabilities — never hardcoded
4. **Mode Toggle**: Interactive Demo / Benchmark
5. **Two-Column Workspace**: interactive operation (65%) + algorithm details panel (35%)
6. **ML-KEM Workflow**: Keypair → Encapsulate → Decapsulate → ✓ Shared Secret Match (step visualizer)
7. **ML-DSA Workflow**: Message input → Keypair → Sign → Verify → ✓ Signature Valid; tamper test → ✕ Signature Invalid
8. **Measured This Run**: compact metric cards (Key Gen / Encap/Sign / Decap/Verify / Ciphertext/Signature size)
9. **Object Sizes**: public key, private key (size only), ciphertext/signature byte lengths
10. **Benchmark Table**: Operation | Average | Minimum | Maximum | Runs (real backend data)
11. **Technical Details**: collapsible, library/version/platform/algo/measurement method
12. **Disclaimers**: clear statements — not FIPS certified, demo only, not production migration

### UI States (all implemented)

- ✅ Loading: "Checking PQC runtime capabilities…"
- ✅ Backend unavailable: clear error panel with Retry
- ✅ SLH-DSA unavailable: disabled card with explanation text
- ✅ Operation in-progress: button shows spinner, disabled
- ✅ KEM success: "Key Establishment Successful" green banner
- ✅ Signature valid: "Signature Valid" green banner
- ✅ Tamper test: "Signature Invalid for Modified Message" — red banner labeled "expected to fail"
- ✅ API error: contained error state
- ✅ Page refresh: route loads correctly

### Testing

- **Focused PQC Lab tests:** 62/62 passed (`tests/test_pqc_lab.py`)
  - Capabilities endpoint structure and real content
  - ML-KEM-768 and ML-KEM-1024 round-trip: success, timings ≥ 0, sizes match spec
  - ML-DSA-44/-65/-87: sign+verify success, tamper correctly fails, sizes match spec
  - No private key or shared secret in any response
  - Benchmark: statistics structure, real values, bounded iteration enforcement
  - Service-layer unit tests (direct Python, not through HTTP)
  - Invalid param set → 422; invalid iteration count → 422; empty message → 422
- **Full backend suite:** 341/341 passed
- **Frontend:** `npm run build` — clean, exit 0, 0 TypeScript errors

### Functional Verification (browser)

All the following were verified live against the running backend:
- ✅ PQC Lab page loads at `/demo`
- ✅ Runtime strip shows real `cryptography: 49.0.0 | Python: 3.14.3 | Windows | PQC Backend Ready`
- ✅ ML-KEM-768 demo executes and shows "Key Establishment Successful" with real timings
- ✅ ML-KEM-1024 demo executes
- ✅ ML-DSA-65 sign+verify shows "Signature Valid"
- ✅ Tamper test shows "Signature Invalid for Modified Message" (expected cryptographic behavior)
- ✅ Benchmark table renders with real avg/min/max values
- ✅ SLH-DSA shown as unavailable with explanation — no active controls
- ✅ PQC Lab highlighted as active in sidebar
- ✅ Page refreshes correctly at `/demo`

### Limitations

- SLH-DSA not available in `cryptography` 49.0.0 on this platform
- Measurements are environment-specific — not universal benchmarks
- No classical-vs-PQC comparison implemented (no reliable classical KEM/sig in existing deps for fair comparison)
- PQC Lab does not automatically perform migration — demonstration only

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
| Phase F | ✅ Complete | Migration KB + Recommendation Engine (210 tests) |
| Phase G | ✅ Complete | Migration Roadmap Engine (253 tests); stage persistence fix; Wave/Lifecycle UI |
| Phase H | ✅ Complete | Executive Dashboard (279 tests); Quantum Readiness Score; all UI states |
| Phase I | ✅ Complete | PQC Lab (341 tests); ML-KEM + ML-DSA real ops; benchmark; all UI states |
| Phase J | ✅ Complete | Navigation & Product Polish; shared AppSidebar; landing page sections; PQC Lab wording |
| Reports | 🔴 Pending | Placeholder only |

---

## Phase J — Navigation & Product Polish ✅

### Summary

Frontend-only pass with no backend changes. All 341 backend tests continue to pass.

### Changes Made

#### Shared Collapsible Sidebar (`frontend/src/components/AppSidebar.tsx`) — NEW

- Single shared sidebar component replacing duplicated local Sidebar implementations in every app page.
- Desktop EXPANDED: QShield branding, hamburger toggle, full labeled navigation.
- Desktop COLLAPSED (48px): **ONLY the hamburger button** — no icon-only rail, no individual nav icons.
- Main content area expands to fill full width when sidebar is collapsed.
- Mobile: overlay/drawer behavior with backdrop, Escape-to-close.
- Collapse state persisted via `localStorage` key `qshield_sidebar_open`.
- Scan-aware routing: Inventory, Risk, Migration, Roadmap links carry `scanId`; disabled when no scan available.
- Active route highlighted via `activeKey` prop.

#### Replaced local Sidebar in:
- `frontend/src/pages/Dashboard.tsx` — `activeKey="dashboard"`
- `frontend/src/pages/RiskPage.tsx` — `activeKey="risk"`
- `frontend/src/pages/RecommendationsPage.tsx` — `activeKey="migration"`
- `frontend/src/pages/RoadmapPage.tsx` — `activeKey="roadmap"`
- `frontend/src/pages/DemoPage.tsx` — `activeKey="pqclab"`

#### Navbar (`frontend/src/components/Navbar.tsx`) — REWRITTEN

Simplified landing-page header — removed dead links (Platform, Discovery, etc.):
- About QShield → smooth-scroll to `#about`
- Previous Scans → smooth-scroll to `#previous-scans`
- Open Dashboard → `/dashboard`
- Start New Scan → `/scan`

#### Landing Page (`frontend/src/pages/LandingPage.tsx`) — REWRITTEN

Preserved hero visual identity (video background, grid overlay, vignette, QShield branding).

Added sections:
1. **Hero** — Discover headline, Start New Scan (primary CTA), View Previous Scans (secondary)
2. **How QShield Works** — 6 real implemented workflow steps (Discover, Inventory, Assess, Recommend, Plan, Validate)
3. **Previous Scans** — Real data from `/api/dashboard/scans`; loading/empty/error states; reopen via Dashboard, Inventory, Risk Analysis links
4. **About QShield** — Accurate product description; purpose-aware migration guidance explanation; technical disclaimers

No fake/hardcoded scans. Smooth-scroll anchor navigation. framer-motion animations (already in project dependencies).

#### PQC Lab SLH-DSA Wording Update (`frontend/src/pages/DemoPage.tsx`)

Updated SLH-DSA unavailability message to:
> "Unavailable in the current runtime. SLH-DSA is standardized in FIPS 205, but the active cryptographic backend does not currently expose a supported implementation."

### Verification

- **Frontend build:** `npm run build` — ✅ clean, exit 0, 0 TypeScript errors
- **Backend:** No backend changes — 341/341 tests continue to pass
- **Build output:** `dist/assets/index-*.js` — 605 kB (minified) / 175 kB gzip


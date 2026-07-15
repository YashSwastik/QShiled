/**
 * roadmapApi.ts — typed client for the QShield Migration Roadmap API.
 *
 * All roadmap content is computed deterministically on the backend.
 * Wave assignments, reasons, and recommended actions are never hardcoded here.
 */

const API_BASE = import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8000';

// ── Types matching backend schemas/roadmap_schema.py ──────────────────────────

export interface WaveSummary {
  wave: number;
  label: string;
  item_count: number;
  description: string;
}

export interface RoadmapItem {
  finding_id: string;
  scan_id: string;

  application_name: string;
  application_id: string | null;

  algorithm: string;
  algorithm_family: string;
  file_path: string | null;

  wave: number;
  wave_label: string;

  migration_priority: string | null;
  quantum_migration_score: number | null;
  quantum_migration_severity: string | null;

  crypto_purpose: string;
  requires_manual_review: boolean;

  recommended_target_category: string;
  recommended_algorithms: string[];
  effort_estimate: string;
  nist_standards: string[];

  reason: string;
  recommended_action: string;
  dependencies: string[];
  status: string;           // current MIGRATION_STAGE
  migration_stage: string;  // alias

  kb_version: string;
}

export interface ScanRoadmapResult {
  scan_id: string;
  application_name: string;
  application_id: string | null;
  total_items: number;
  wave_summaries: WaveSummary[];
  items: RoadmapItem[];
  summary: string;
}

// ── Valid stages ──────────────────────────────────────────────────────────────

export const MIGRATION_STAGES = [
  'DISCOVERED', 'ASSESSED', 'PLANNED', 'PILOT', 'TRANSITION', 'VALIDATION', 'MIGRATED',
] as const;

export type MigrationStage = typeof MIGRATION_STAGES[number];

// ── API calls ─────────────────────────────────────────────────────────────────

export async function getRoadmap(scanId: string): Promise<ScanRoadmapResult> {
  const resp = await fetch(
    `${API_BASE}/api/roadmap?scan_id=${encodeURIComponent(scanId)}`
  );
  if (!resp.ok) {
    const body = await resp.json().catch(() => ({}));
    throw new Error(body.detail ?? `Roadmap API error ${resp.status}`);
  }
  return resp.json();
}

export async function updateRoadmapItemStage(
  findingId: string,
  scanId: string,
  stage: string,
): Promise<RoadmapItem> {
  const resp = await fetch(
    `${API_BASE}/api/roadmap/items/${encodeURIComponent(findingId)}`,
    {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ scan_id: scanId, status: stage }),
    }
  );
  if (!resp.ok) {
    const body = await resp.json().catch(() => ({}));
    throw new Error(body.detail ?? `Stage update failed: ${resp.status}`);
  }
  return resp.json();
}

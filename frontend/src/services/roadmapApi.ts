/**
 * roadmapApi.ts — typed client for the QShield Migration Roadmap API.
 *
 * All roadmap content is computed deterministically on the backend.
 * Wave assignments, reasons, and recommended actions are never hardcoded here.
 */

import api from './api';

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
  const response = await api.get<ScanRoadmapResult>('/api/roadmap', { params: { scan_id: scanId } });
  return response.data;
}

export async function updateRoadmapItemStage(
  findingId: string,
  scanId: string,
  stage: string,
): Promise<RoadmapItem> {
  const response = await api.patch<RoadmapItem>(`/api/roadmap/items/${findingId}`, {
    scan_id: scanId,
    status: stage,
  });
  return response.data;
}

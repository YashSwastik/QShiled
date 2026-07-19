/**
 * recommendationsApi.ts — typed client for the QShield Recommendations API.
 *
 * All recommendation content is calculated deterministically on the backend.
 * No migration guidance is hardcoded in the frontend.
 */

import api from './api';

// ── Types matching backend schemas/recommendation.py ──────────────────────────

export interface MigrationRecommendation {
  finding_id: string;
  algorithm: string;
  algorithm_family: string;
  file_path: string | null;

  // Purpose
  crypto_purpose: string;
  purpose_confidence: number;
  purpose_reasoning: string;
  requires_manual_review: boolean;

  // Current state
  current_state_description: string;
  quantum_threat: string;
  is_quantum_concern: boolean;

  // Part 7 priority (consumed, not recalculated)
  migration_priority: string | null;
  quantum_migration_score: number | null;

  // Target
  recommended_target_category: string;
  recommended_algorithms: string[];
  nist_standards: string[];
  effort_estimate: string;

  // Guidance
  prerequisites: string[];
  migration_steps: string[];
  testing_requirements: string[];
  interoperability_notes: string[];
  validation_checklist: string[];

  timeline_guidance: string;
  technical_notes: string;

  // Provenance
  kb_version: string;
  kb_entry_key: string | null;
}

export interface ScanRecommendationResult {
  scan_id: string;
  kb_version: string;
  total_findings: number;
  recommendations: MigrationRecommendation[];
  manual_review_count: number;
  quantum_concern_count: number;
  classical_only_count: number;
  safe_count: number;
  summary: string;
}

// ── API call ──────────────────────────────────────────────────────────────────

export async function getRecommendations(scanId: string): Promise<ScanRecommendationResult> {
  const response = await api.get<ScanRecommendationResult>('/api/recommendations', {
    params: { scan_id: scanId },
  });
  return response.data;
}

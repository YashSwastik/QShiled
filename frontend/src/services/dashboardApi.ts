/**
 * dashboardApi.ts — typed client for the QShield Dashboard API.
 *
 * GET /api/dashboard?scan_id=<id>   → DashboardSummary
 * GET /api/dashboard/scans          → ScanOption[]
 *
 * All values are computed deterministically on the backend from real DB state.
 */

import api from './api';

// ── Types (mirrors backend Pydantic schemas) ──────────────────────────────────

export interface ScanOption {
  scan_id: string;
  scan_name: string;
  application_id: string;
  application_name: string;
  status: string;
  completed_at: string | null;
  finding_count: number;
}

export interface AlgorithmCount {
  family: string;
  count: number;
}

export interface SeverityCount {
  severity: string;
  count: number;
}

export interface StageCount {
  stage: string;
  count: number;
}

export interface WaveCount {
  wave: number;
  label: string;
  count: number;
}

export interface TopAsset {
  application_id: string;
  application_name: string;
  highest_severity: string;
  relevant_findings: number;
  wave: number | null;
}

export interface TopFinding {
  finding_id: string;
  scan_id: string;
  algorithm: string;
  algorithm_family: string;
  file_path: string | null;
  risk_score: number;
  severity: string;
  migration_priority: string | null;
}

export interface ReadinessMethodology {
  description: string;
  component_exposure_weight: number;
  component_risk_weight: number;
  component_progress_weight: number;
  s_exposure: number;
  s_risk_inv: number;
  s_progress: number;
  disclaimer: string;
}

export interface DashboardSummary {
  scan_id: string;
  scan_name: string;
  scan_status: string;
  application_id: string | null;
  application_name: string;
  completed_at: string | null;

  quantum_readiness_score: number;
  readiness_label: string;
  readiness_methodology: ReadinessMethodology;

  total_findings: number;
  quantum_relevant_findings: number;
  quantum_safe_findings: number;
  critical_findings: number;
  high_findings: number;
  moderate_findings: number;
  low_findings: number;

  algorithm_distribution: AlgorithmCount[];
  severity_distribution: SeverityCount[];

  total_roadmap_items: number;
  migrated_items: number;
  migration_progress_pct: number;
  stage_distribution: StageCount[];
  wave_distribution: WaveCount[];

  top_assets: TopAsset[];
  top_findings: TopFinding[];

  has_running_scan: boolean;
}

// ── API calls ─────────────────────────────────────────────────────────────────

export async function listDashboardScans(): Promise<ScanOption[]> {
  const response = await api.get<ScanOption[]>('/api/dashboard/scans');
  return response.data;
}

export async function getDashboardSummary(scanId: string): Promise<DashboardSummary> {
  const response = await api.get<DashboardSummary>('/api/dashboard', { params: { scan_id: scanId } });
  return response.data;
}

export async function deleteScan(scanId: string): Promise<void> {
  await api.delete(`/api/scans/${scanId}`);
}

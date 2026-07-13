/**
 * riskApi.ts — typed client for the QShield Risk Analysis API.
 *
 * All values are calculated on the backend.
 * No risk scores are hardcoded in the frontend.
 */

const API_BASE = import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8000';

// ── Types matching backend schemas/risk.py ────────────────────────────────────

export interface FactorScore {
  factor: string;
  label: string;                  // Human-readable factor name
  weight: number;
  raw_value: number;              // 0–1 pre-weight
  weighted_contribution: number;  // raw × weight × 100 (before gate)
  rationale: string;
}

export interface FindingRisk {
  finding_id: string;
  algorithm: string;
  algorithm_family: string;
  file_path: string | null;
  quantum_migration_score: number;         // 0–100 (after gate)
  raw_weighted_sum: number;               // before gate
  crypto_vulnerability_gate: number;      // 0–1 gate multiplier
  quantum_migration_severity: 'Low' | 'Moderate' | 'High' | 'Critical';
  classical_legacy_risk: string | null;
  classical_legacy_rationale: string | null;
  factors: FactorScore[];
  explanation: string;
  migration_priority: 'immediate' | 'near_term' | 'long_term' | 'low';
  nist_recommendation: string | null;
}

export interface ScanRiskResult {
  methodology: string;
  methodology_version: string;
  methodology_description: string;
  disclaimer: string;
  scan_id: string;
  overall_quantum_score: number;
  overall_severity: 'Low' | 'Moderate' | 'High' | 'Critical';
  vulnerable_count: number;
  safe_count: number;
  borderline_count: number;
  legacy_count: number;
  factor_summary: Record<string, number>;
  top_findings: FindingRisk[];
  summary_text: string;
  business_criticality: string;
  internet_exposed: boolean;
  confidentiality_requirement: string;
  data_sensitivity: string;
  data_lifetime_years: number;
  environment: string;
  context_defaulted: boolean;
}

// ── API call ──────────────────────────────────────────────────────────────────

export async function getRiskAnalysis(scanId: string): Promise<ScanRiskResult> {
  const resp = await fetch(`${API_BASE}/api/risk?scan_id=${encodeURIComponent(scanId)}`);
  if (!resp.ok) {
    const body = await resp.json().catch(() => ({}));
    throw new Error(body.detail ?? `Risk API error ${resp.status}`);
  }
  return resp.json();
}

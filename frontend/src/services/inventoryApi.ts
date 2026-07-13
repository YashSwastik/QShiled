/**
 * inventoryApi.ts — typed client for /api/findings and /api/scans
 *
 * All data comes from the backend; no mocked values.
 */
import api from './api';

// ── Types mirroring backend schemas ──────────────────────────────────────────

export type QuantumStatus = 'vulnerable' | 'safe' | 'borderline' | 'unknown' | 'hybrid';
export type FindingCategory =
  | 'QUANTUM_VULNERABLE_PUBLIC_KEY'
  | 'SYMMETRIC'
  | 'HASH'
  | 'LEGACY_DEPRECATED'
  | 'POST_QUANTUM'
  | 'UNKNOWN_REVIEW';
export type DetectionMethod = 'regex' | 'ast' | 'cert_parse';
export type ScanStatus = 'pending' | 'running' | 'completed' | 'failed';

export interface Finding {
  id: string;
  scan_id: string;
  file_path: string;
  line_number: number | null;
  raw_snippet: string | null;
  algorithm: string;
  algorithm_family: string;
  key_size: number | null;
  usage_context: string | null;
  quantum_status: QuantumStatus;
  category: FindingCategory;
  detection_method: DetectionMethod;
  confidence: number;
  risk_score: number | null;
  risk_factors: Record<string, unknown> | null;
  nist_recommendation: string | null;
  created_at: string;
}

export interface FindingListResponse {
  total: number;
  items: Finding[];
}

export interface FindingSummary {
  scan_id: string;
  total: number;
  by_category: Partial<Record<FindingCategory, number>>;
  by_quantum_status: Partial<Record<QuantumStatus, number>>;
  by_algorithm_family: Array<{ family: string; count: number }>;
}

export interface Scan {
  id: string;
  application_id: string;
  name: string;
  scan_type: string;
  status: ScanStatus;
  file_count: number;
  finding_count: number;
  overall_risk_score: number | null;
  started_at: string | null;
  completed_at: string | null;
  error_message: string | null;
  upload_name: string | null;
  upload_type: string | null;
  created_at: string;
  updated_at: string;
}

export interface ScanListResponse {
  total: number;
  items: Scan[];
}

// ── Query params ──────────────────────────────────────────────────────────────

export interface FindingFilters {
  scan_id?: string;
  quantum_status?: string;
  algorithm_family?: string;
  category?: string;
  search?: string;
  sort_by?: string;
  sort_dir?: 'asc' | 'desc';
  page?: number;
  page_size?: number;
}

// ── API calls ─────────────────────────────────────────────────────────────────

export async function getFindings(filters: FindingFilters = {}): Promise<FindingListResponse> {
  const params = Object.fromEntries(
    Object.entries(filters).filter(([, v]) => v !== undefined && v !== '' && v !== null)
  );
  const res = await api.get<FindingListResponse>('/api/findings', { params });
  return res.data;
}

export async function getFinding(id: string): Promise<Finding> {
  const res = await api.get<Finding>(`/api/findings/${id}`);
  return res.data;
}

export async function getFindingSummary(scanId: string): Promise<FindingSummary> {
  const res = await api.get<FindingSummary>('/api/findings/summary', {
    params: { scan_id: scanId },
  });
  return res.data;
}

export async function getScan(id: string): Promise<Scan> {
  const res = await api.get<Scan>(`/api/scans/${id}`);
  return res.data;
}

export async function listScans(params?: { application_id?: string; page?: number; page_size?: number }): Promise<ScanListResponse> {
  const res = await api.get<ScanListResponse>('/api/scans', { params });
  return res.data;
}

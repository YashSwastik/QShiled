/**
 * reportsApi.ts — QShield Reports API client (Part 12)
 *
 * Endpoints:
 *   GET /api/reports?scan_id=        → report availability metadata
 *   GET /api/reports/executive?scan_id=   → JSON preview
 *   GET /api/reports/inventory?scan_id=   → JSON preview
 *   GET /api/reports/roadmap?scan_id=     → JSON preview
 *
 * PDF/ZIP downloads are triggered as browser navigations (window.open or anchor).
 *
 * Base URL is inferred from the existing api.ts base.
 */

const BASE = 'http://127.0.0.1:8000/api/reports';

export interface ReportAvailability {
  scan_id: string | null;
  completed_scans: CompletedScan[];
  scan_ready: boolean;
  has_risk_data: boolean;
  has_roadmap_data: boolean;
  available_reports: { key: string; title: string; available: boolean }[];
  message?: string;
}

export interface CompletedScan {
  scan_id: string;
  scan_name: string;
  application_id: string;
  application_name: string;
  status: string;
  completed_at: string | null;
  finding_count: number;
}

export async function getReportAvailability(scanId?: string): Promise<ReportAvailability> {
  const url = scanId ? `${BASE}?scan_id=${scanId}` : BASE;
  const res = await fetch(url);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

export async function getExecutivePreview(scanId: string): Promise<Record<string, unknown>> {
  const res = await fetch(`${BASE}/executive?scan_id=${scanId}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

export async function getInventoryPreview(scanId: string): Promise<Record<string, unknown>> {
  const res = await fetch(`${BASE}/inventory?scan_id=${scanId}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

export async function getRoadmapPreview(scanId: string): Promise<Record<string, unknown>> {
  const res = await fetch(`${BASE}/roadmap?scan_id=${scanId}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

/** Trigger browser download of individual PDF. */
export function downloadPdf(type: 'executive' | 'inventory' | 'roadmap', scanId: string) {
  window.open(`${BASE}/${type}/pdf?scan_id=${scanId}`, '_blank');
}

/** Trigger browser download of ZIP bundle. */
export function downloadAllReports(scanId: string) {
  window.open(`${BASE}/all?scan_id=${scanId}`, '_blank');
}

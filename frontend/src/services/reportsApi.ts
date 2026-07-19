/**
 * reportsApi.ts — QShield Reports API client (Part 12)
 *
 * Endpoints:
 *   GET /api/reports?scan_id=        → report availability metadata
 *   GET /api/reports/executive?scan_id=   → JSON preview
 *   GET /api/reports/inventory?scan_id=   → JSON preview
 *   GET /api/reports/roadmap?scan_id=     → JSON preview
 *
 * PDF/ZIP downloads are fetched through the shared client and downloaded locally.
 */
import api from './api';

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
  const response = await api.get<ReportAvailability>('/api/reports', {
    params: scanId ? { scan_id: scanId } : undefined,
  });
  return response.data;
}

export async function getExecutivePreview(scanId: string): Promise<Record<string, unknown>> {
  const response = await api.get<Record<string, unknown>>('/api/reports/executive', {
    params: { scan_id: scanId },
  });
  return response.data;
}

export async function getInventoryPreview(scanId: string): Promise<Record<string, unknown>> {
  const response = await api.get<Record<string, unknown>>('/api/reports/inventory', {
    params: { scan_id: scanId },
  });
  return response.data;
}

export async function getRoadmapPreview(scanId: string): Promise<Record<string, unknown>> {
  const response = await api.get<Record<string, unknown>>('/api/reports/roadmap', {
    params: { scan_id: scanId },
  });
  return response.data;
}

function saveBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

/** Fetch and download an individual PDF through the shared API client. */
export async function downloadPdf(type: 'executive' | 'inventory' | 'roadmap', scanId: string) {
  const response = await api.get<Blob>(`/api/reports/${type}/pdf`, {
    params: { scan_id: scanId },
    responseType: 'blob',
  });
  saveBlob(response.data, `${type}-report.pdf`);
}

/** Fetch and download the report ZIP bundle through the shared API client. */
export async function downloadAllReports(scanId: string) {
  const response = await api.get<Blob>('/api/reports/all', {
    params: { scan_id: scanId },
    responseType: 'blob',
  });
  saveBlob(response.data, 'qshield-reports.zip');
}

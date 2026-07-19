/**
 * ReportsPage.tsx — QShield Part 12: Enterprise Reporting
 *
 * Three report cards:
 *   1. Executive Quantum Readiness
 *   2. Technical Cryptographic Inventory
 *   3. Migration Roadmap
 *
 * Each card provides:
 *   [Generate Preview] — loads JSON, renders an inline preview panel
 *   [Download ▼]      — opens dropdown: Download This Report | Download All Reports
 *
 * Uses shared AppSidebar, real backend data only, no fake metrics.
 *
 * Route: /reports
 */
import { useEffect, useState, useRef, useCallback } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  FileText, Download, RefreshCw, ChevronDown, ChevronRight,
  AlertCircle, CheckCircle, Loader2, Shield, BarChart2,
  Map, ClipboardList, ExternalLink, Archive,
} from 'lucide-react';
import AppSidebar from '../components/AppSidebar';
import {
  getExecutivePreview,
  getInventoryPreview,
  getRoadmapPreview,
  downloadPdf,
  downloadAllReports,
  type CompletedScan,
} from '../services/reportsApi';
import { listDashboardScans } from '../services/dashboardApi';

// ── Design tokens (match existing pages) ─────────────────────────────────────
const TEXT   = '#192837';
const ACCENT = '#7342E2';
const MUTED  = 'rgba(25,40,55,0.50)';
const MUTED2 = 'rgba(25,40,55,0.30)';
const BG     = '#f8f8f5';
const SURF   = '#ffffff';
const BORDER = '1px solid rgba(25,40,55,0.09)';

// ── Severity colours ──────────────────────────────────────────────────────────
function sevColor(sev: string): string {
  switch ((sev || '').toLowerCase()) {
    case 'critical': return '#ef4444';
    case 'high':     return '#f97316';
    case 'moderate':
    case 'medium':   return '#eab308';
    case 'low':      return '#22c55e';
    default:         return '#94a3b8';
  }
}

// ── Report card config ────────────────────────────────────────────────────────
type ReportType = 'executive' | 'inventory' | 'roadmap';

const REPORT_CFG: Record<ReportType, {
  icon: React.ReactNode;
  title: string;
  audience: string;
  desc: string;
  filename: (proj: string) => string;
}> = {
  executive: {
    icon: <Shield size={20} style={{ color: ACCENT }} />,
    title: 'Executive Quantum Readiness',
    audience: 'CISO · Security Leadership · Executive Management',
    desc: 'Quantum Readiness Score, risk summary, severity distribution, algorithm distribution, executive recommendations, and migration progress. Designed for non-technical stakeholders.',
    filename: p => `Executive_Report_${p}.pdf`,
  },
  inventory: {
    icon: <ClipboardList size={20} style={{ color: ACCENT }} />,
    title: 'Technical Cryptographic Inventory',
    audience: 'Security Engineers · Developers · Auditors',
    desc: 'Full CBOM-style cryptographic asset inventory grouped by algorithm category. Separates quantum migration risks from legacy security concerns. References actual file locations.',
    filename: p => `Technical_Inventory_Report_${p}.pdf`,
  },
  roadmap: {
    icon: <Map size={20} style={{ color: ACCENT }} />,
    title: 'Migration Roadmap',
    audience: 'Migration Teams · Project Managers · Security Architects',
    desc: 'Deterministic migration roadmap with wave assignments (NOW/NEXT/LATER), lifecycle stage distribution, priority actions, and migration progress. Reuses persisted roadmap engine output.',
    filename: p => `Migration_Roadmap_Report_${p}.pdf`,
  },
};

// ── Tiny stat pill ────────────────────────────────────────────────────────────
function Stat({ label, value, accent }: { label: string; value: string | number; accent?: boolean }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2 }}>
      <span style={{ fontSize: 18, fontWeight: 800, color: accent ? ACCENT : TEXT }}>{value}</span>
      <span style={{ fontSize: 10, color: MUTED, textTransform: 'uppercase', letterSpacing: '0.06em' }}>{label}</span>
    </div>
  );
}

// ── KV row for preview panels ─────────────────────────────────────────────────
function KVRow({ label, value }: { label: string; value: string | number | null | undefined }) {
  return (
    <div style={{
      display: 'flex', justifyContent: 'space-between', alignItems: 'baseline',
      padding: '5px 0', borderBottom: '1px solid rgba(25,40,55,0.06)', fontSize: 13,
    }}>
      <span style={{ color: MUTED, fontWeight: 500 }}>{label}</span>
      <span style={{ color: TEXT, fontWeight: 600, textAlign: 'right', maxWidth: '60%' }}>{value ?? '—'}</span>
    </div>
  );
}

// ── Section heading for preview ───────────────────────────────────────────────
function PreviewSection({ title }: { title: string }) {
  return (
    <div style={{
      fontSize: 11, fontWeight: 700, color: ACCENT, textTransform: 'uppercase',
      letterSpacing: '0.08em', marginBottom: 8, marginTop: 20, paddingBottom: 4,
      borderBottom: `2px solid ${ACCENT}30`,
    }}>
      {title}
    </div>
  );
}

// ── Download menu ─────────────────────────────────────────────────────────────
function DownloadMenu({
  reportType, scanId, projName, onClose,
}: {
  reportType: ReportType; scanId: string; projName: string; onClose: () => void;
}) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function click(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) onClose();
    }
    document.addEventListener('mousedown', click);
    return () => document.removeEventListener('mousedown', click);
  }, [onClose]);

  return (
    <div
      ref={ref}
      style={{
        position: 'absolute', top: '100%', right: 0, marginTop: 4,
        background: SURF, border: BORDER, borderRadius: 10,
        boxShadow: '0 8px 32px rgba(25,40,55,0.14)',
        zIndex: 100, minWidth: 240, overflow: 'hidden',
      }}
    >
      <div style={{ padding: '6px 0' }}>
        <button
          onClick={() => { downloadPdf(reportType, scanId); onClose(); }}
          style={{
            display: 'flex', alignItems: 'center', gap: 10,
            width: '100%', padding: '10px 16px', textAlign: 'left',
            background: 'none', border: 'none', cursor: 'pointer',
            fontSize: 13, color: TEXT,
          }}
          onMouseEnter={e => (e.currentTarget.style.background = `${ACCENT}0A`)}
          onMouseLeave={e => (e.currentTarget.style.background = 'none')}
        >
          <FileText size={14} style={{ color: ACCENT }} />
          <div>
            <div style={{ fontWeight: 600 }}>Download This Report (PDF)</div>
            <div style={{ fontSize: 11, color: MUTED }}>{REPORT_CFG[reportType].filename(projName)}</div>
          </div>
        </button>

        <div style={{ height: 1, background: 'rgba(25,40,55,0.07)', margin: '2px 0' }} />

        <button
          onClick={() => { downloadAllReports(scanId); onClose(); }}
          style={{
            display: 'flex', alignItems: 'center', gap: 10,
            width: '100%', padding: '10px 16px', textAlign: 'left',
            background: 'none', border: 'none', cursor: 'pointer',
            fontSize: 13, color: TEXT,
          }}
          onMouseEnter={e => (e.currentTarget.style.background = `${ACCENT}0A`)}
          onMouseLeave={e => (e.currentTarget.style.background = 'none')}
        >
          <Archive size={14} style={{ color: ACCENT }} />
          <div>
            <div style={{ fontWeight: 600 }}>Download All Reports (.zip)</div>
            <div style={{ fontSize: 11, color: MUTED }}>QShield_Reports_{projName}.zip</div>
          </div>
        </button>
      </div>
    </div>
  );
}

// ── Inline preview renderers ───────────────────────────────────────────────────

function ExecutivePreview({ data }: { data: Record<string, unknown> }) {
  const dash = (data.dashboard || {}) as Record<string, unknown>;
  const recs = (data.recommendations || []) as Record<string, unknown>[];
  const qrecs = recs.filter(r => r.is_quantum_concern).slice(0, 5);
  const topFindings = (dash.top_findings || []) as Record<string, unknown>[];
  const sevDist = (dash.severity_distribution || []) as Record<string, unknown>[];
  const algoDist = (dash.algorithm_distribution || []) as Record<string, unknown>[];
  const waveDist = (dash.wave_distribution || []) as Record<string, unknown>[];

  return (
    <div>
      <PreviewSection title="Quantum Readiness Score" />
      <div style={{ display: 'flex', gap: 32, flexWrap: 'wrap', marginBottom: 16, padding: '12px 0' }}>
        <Stat label="Readiness Score" value={`${dash.quantum_readiness_score}/100`} accent />
        <Stat label="Label" value={String(dash.readiness_label || '—')} />
        <Stat label="Total Findings" value={String(dash.total_findings || 0)} />
        <Stat label="Quantum-Relevant" value={String(dash.quantum_relevant_findings || 0)} />
        <Stat label="Critical" value={String(dash.critical_findings || 0)} />
        <Stat label="Migration Progress" value={`${dash.migration_progress_pct ?? 0}%`} />
      </div>

      <PreviewSection title="Risk Summary" />
      <KVRow label="Total Findings" value={String(dash.total_findings || 0)} />
      <KVRow label="Quantum-Relevant" value={String(dash.quantum_relevant_findings || 0)} />
      <KVRow label="Quantum-Safe" value={String(dash.quantum_safe_findings || 0)} />
      <KVRow label="Critical" value={String(dash.critical_findings || 0)} />
      <KVRow label="High" value={String(dash.high_findings || 0)} />
      <KVRow label="Moderate" value={String(dash.moderate_findings || 0)} />
      <KVRow label="Migration Progress" value={`${dash.migration_progress_pct ?? 0}%`} />
      <KVRow label="Migrated Items" value={`${dash.migrated_items || 0} / ${dash.total_roadmap_items || 0}`} />

      {sevDist.length > 0 && (
        <>
          <PreviewSection title="Severity Distribution" />
          {sevDist.map((s: Record<string, unknown>) => (
            <div key={String(s.severity)} style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
              <span style={{
                width: 80, fontSize: 12, fontWeight: 600,
                color: sevColor(String(s.severity)),
              }}>{String(s.severity)}</span>
              <div style={{ flex: 1, height: 6, borderRadius: 3, background: '#f0f0ec', overflow: 'hidden' }}>
                <div style={{
                  width: `${Math.min(100, ((Number(s.count) || 0) / Math.max(1, Number(dash.total_findings) || 1)) * 100)}%`,
                  height: '100%', background: sevColor(String(s.severity)), borderRadius: 3,
                }} />
              </div>
              <span style={{ fontSize: 12, color: MUTED, width: 30, textAlign: 'right' }}>{String(s.count)}</span>
            </div>
          ))}
        </>
      )}

      {algoDist.length > 0 && (
        <>
          <PreviewSection title="Algorithm Distribution" />
          {algoDist.slice(0, 8).map((a: Record<string, unknown>) => (
            <div key={String(a.family)} style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
              <span style={{ width: 100, fontSize: 12, fontWeight: 500, color: TEXT }}>{String(a.family)}</span>
              <div style={{ flex: 1, height: 6, borderRadius: 3, background: '#f0f0ec', overflow: 'hidden' }}>
                <div style={{
                  width: `${Math.min(100, ((Number(a.count) || 0) / Math.max(1, Number(dash.total_findings) || 1)) * 100)}%`,
                  height: '100%', background: ACCENT + '80', borderRadius: 3,
                }} />
              </div>
              <span style={{ fontSize: 12, color: MUTED, width: 30, textAlign: 'right' }}>{String(a.count)}</span>
            </div>
          ))}
        </>
      )}

      {topFindings.length > 0 && (
        <>
          <PreviewSection title="Top Risk Findings" />
          {topFindings.map((f: Record<string, unknown>, i: number) => (
            <div key={i} style={{
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              padding: '6px 0', borderBottom: '1px solid rgba(25,40,55,0.05)', gap: 8,
            }}>
              <span style={{ fontSize: 12, fontWeight: 600, color: TEXT, flex: 1 }}>{String(f.algorithm)}</span>
              <span style={{ fontSize: 11, color: MUTED, flex: 1 }}>{String(f.algorithm_family)}</span>
              <span style={{ fontSize: 11, color: MUTED }}>{String(f.risk_score)}</span>
              <span style={{ fontSize: 11, fontWeight: 700, color: sevColor(String(f.severity)) }}>{String(f.severity)}</span>
            </div>
          ))}
        </>
      )}

      {waveDist.length > 0 && (
        <>
          <PreviewSection title="Migration Waves" />
          {waveDist.map((w: Record<string, unknown>) => (
            <KVRow key={String(w.wave)} label={`Wave ${w.wave} — ${w.label}`} value={`${w.count} items`} />
          ))}
        </>
      )}

      {qrecs.length > 0 && (
        <>
          <PreviewSection title="Executive Recommendations (Top 5)" />
          {qrecs.map((r: Record<string, unknown>, i: number) => (
            <div key={i} style={{
              background: '#f8f8f5', border: BORDER, borderRadius: 8,
              padding: '10px 12px', marginBottom: 8,
            }}>
              <div style={{ fontSize: 13, fontWeight: 700, color: TEXT, marginBottom: 3 }}>
                {String(r.algorithm)} → {String(r.recommended_target_category || 'Manual Review')}
              </div>
              <div style={{ fontSize: 12, color: MUTED }}>{String(r.current_state_description || '')}</div>
              <div style={{ fontSize: 11, color: ACCENT, marginTop: 4, fontWeight: 600 }}>
                Priority: {String(r.migration_priority || '—').toUpperCase()}
                {r.nist_standards && (r.nist_standards as string[]).length > 0
                  ? `  |  NIST: ${(r.nist_standards as string[]).join(', ')}`
                  : ''}
              </div>
            </div>
          ))}
        </>
      )}
    </div>
  );
}

function InventoryPreview({ data }: { data: Record<string, unknown> }) {
  const findings = (data.findings || []) as Record<string, unknown>[];
  const sevMap   = (data.severity_map || {}) as Record<string, string>;

  const LEGACY_ALGOS = new Set(['md5', 'sha1', 'sha-1', 'rc4', 'des', '3des']);
  const quantum = findings.filter(f => ['vulnerable', 'borderline'].includes(String(f.quantum_status)));
  const legacy  = findings.filter(f => LEGACY_ALGOS.has(String(f.algorithm || '').toLowerCase()));

  // Group by algorithm
  const byAlgo: Record<string, number> = {};
  findings.forEach(f => { byAlgo[String(f.algorithm)] = (byAlgo[String(f.algorithm)] || 0) + 1; });
  const topAlgos = Object.entries(byAlgo).sort((a, b) => b[1] - a[1]).slice(0, 10);

  return (
    <div>
      <PreviewSection title="Inventory Statistics" />
      <div style={{ display: 'flex', gap: 32, flexWrap: 'wrap', padding: '12px 0 16px' }}>
        <Stat label="Total Findings" value={findings.length} />
        <Stat label="Quantum-Vulnerable" value={quantum.length} accent />
        <Stat label="Legacy-Only" value={legacy.length} />
      </div>

      {topAlgos.length > 0 && (
        <>
          <PreviewSection title="Algorithm Summary" />
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            {topAlgos.map(([algo, cnt]) => (
              <div key={algo} style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <span style={{ width: 120, fontSize: 12, fontWeight: 500, color: TEXT }}>{algo}</span>
                <div style={{ flex: 1, height: 5, borderRadius: 3, background: '#f0f0ec' }}>
                  <div style={{
                    width: `${(cnt / findings.length) * 100}%`,
                    height: '100%', background: ACCENT + '70', borderRadius: 3,
                  }} />
                </div>
                <span style={{ fontSize: 12, color: MUTED, width: 28, textAlign: 'right' }}>{cnt}</span>
              </div>
            ))}
          </div>
        </>
      )}

      {quantum.length > 0 && (
        <>
          <PreviewSection title="Quantum Migration Risks" />
          <div style={{ maxHeight: 300, overflowY: 'auto' }}>
            {quantum.slice(0, 20).map((f: Record<string, unknown>, i: number) => {
              const sev = sevMap[String(f.id)] || '—';
              return (
                <div key={i} style={{
                  display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8,
                  padding: '5px 0', borderBottom: '1px solid rgba(25,40,55,0.05)', fontSize: 12,
                }}>
                  <span style={{ fontWeight: 600, color: TEXT, flex: '0 0 100px' }}>{String(f.algorithm)}</span>
                  <span style={{ color: MUTED, flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {String(f.file_path || '—')}
                  </span>
                  <span style={{ fontWeight: 700, color: sevColor(sev), flex: '0 0 70px', textAlign: 'right' }}>{sev}</span>
                </div>
              );
            })}
          </div>
        </>
      )}

      {legacy.length > 0 && (
        <>
          <PreviewSection title="Legacy Security Concerns" />
          <div style={{ maxHeight: 200, overflowY: 'auto' }}>
            {legacy.slice(0, 15).map((f: Record<string, unknown>, i: number) => (
              <div key={i} style={{
                display: 'flex', alignItems: 'center', gap: 8,
                padding: '5px 0', borderBottom: '1px solid rgba(25,40,55,0.05)', fontSize: 12,
              }}>
                <span style={{ fontWeight: 600, color: '#f97316', flex: '0 0 60px' }}>{String(f.algorithm)}</span>
                <span style={{ color: MUTED, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {String(f.file_path || '—')}
                </span>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

function RoadmapPreview({ data }: { data: Record<string, unknown> }) {
  const dash    = (data.dashboard || {}) as Record<string, unknown>;
  const roadmap = (data.roadmap || {}) as Record<string, unknown>;
  const recs    = (data.recommendations || []) as Record<string, unknown>[];
  const items   = (roadmap.items || []) as Record<string, unknown>[];
  const waveSumm = (roadmap.wave_summaries || []) as Record<string, unknown>[];
  const stageDist = (dash.stage_distribution || []) as Record<string, unknown>[];
  const qrecs   = recs.filter(r => r.is_quantum_concern).slice(0, 5);

  return (
    <div>
      <PreviewSection title="Migration Overview" />
      <div style={{ display: 'flex', gap: 32, flexWrap: 'wrap', padding: '12px 0 16px' }}>
        <Stat label="Total Items" value={items.length} />
        <Stat label="Migrated" value={items.filter(i => i.stage === 'MIGRATED').length} accent />
        <Stat label="Progress" value={`${dash.migration_progress_pct ?? 0}%`} />
        <Stat label="Readiness Score" value={`${dash.quantum_readiness_score ?? 0}/100`} />
      </div>

      {waveSumm.length > 0 && (
        <>
          <PreviewSection title="Wave Summary" />
          {waveSumm.map((ws: Record<string, unknown>) => (
            <div key={String(ws.wave)} style={{
              background: '#f8f8f5', border: BORDER, borderRadius: 8,
              padding: '10px 14px', marginBottom: 8,
            }}>
              <div style={{ fontWeight: 700, color: TEXT, fontSize: 13, marginBottom: 3 }}>
                Wave {String(ws.wave)}: {String(ws.label || '')} — {String(ws.total_items || 0)} items
              </div>
              <div style={{ fontSize: 12, color: MUTED }}>{String(ws.description || '')}</div>
            </div>
          ))}
        </>
      )}

      {stageDist.length > 0 && (
        <>
          <PreviewSection title="Lifecycle Stages" />
          {stageDist.map((st: Record<string, unknown>) => (
            <KVRow key={String(st.stage)} label={String(st.stage)} value={`${st.count} items`} />
          ))}
        </>
      )}

      {items.length > 0 && (
        <>
          <PreviewSection title="Roadmap Items (top 15)" />
          <div style={{ maxHeight: 320, overflowY: 'auto' }}>
            {items.slice(0, 15).map((it: Record<string, unknown>, i: number) => (
              <div key={i} style={{
                display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8,
                padding: '5px 0', borderBottom: '1px solid rgba(25,40,55,0.05)', fontSize: 12,
              }}>
                <span style={{ fontWeight: 600, color: TEXT, flex: '0 0 100px' }}>{String(it.algorithm)}</span>
                <span style={{ color: MUTED, fontSize: 11, flex: '0 0 55px' }}>Wave {String(it.wave)}</span>
                <span style={{ color: ACCENT, fontSize: 11, flex: '0 0 90px', fontWeight: 600 }}>{String(it.stage)}</span>
                <span style={{ color: MUTED, fontSize: 11, flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {String(it.file_path || '—')}
                </span>
              </div>
            ))}
          </div>
        </>
      )}

      {qrecs.length > 0 && (
        <>
          <PreviewSection title="Priority Actions" />
          {qrecs.map((r: Record<string, unknown>, i: number) => (
            <div key={i} style={{
              background: '#f8f8f5', border: BORDER, borderRadius: 8,
              padding: '10px 12px', marginBottom: 8,
            }}>
              <div style={{ fontSize: 13, fontWeight: 700, color: TEXT, marginBottom: 3 }}>
                {String(r.algorithm)} → {String(r.recommended_target_category || 'Manual Review')}
              </div>
              <div style={{ fontSize: 12, color: MUTED }}>{String(r.quantum_threat || '')}</div>
              {Array.isArray(r.nist_standards) && (r.nist_standards as string[]).length > 0 && (
                <div style={{ fontSize: 11, color: ACCENT, marginTop: 4 }}>
                  NIST: {(r.nist_standards as string[]).join(', ')}
                </div>
              )}
            </div>
          ))}
        </>
      )}
    </div>
  );
}

// ── Report card component ─────────────────────────────────────────────────────
function ReportCard({
  type, scanId, projectName, isActive, onActivate,
}: {
  type: ReportType;
  scanId: string;
  projectName: string;
  isActive: boolean;
  onActivate: (t: ReportType) => void;
}) {
  const cfg = REPORT_CFG[type];
  const [previewData, setPreviewData] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [menuOpen, setMenuOpen] = useState(false);

  const fetchers = { executive: getExecutivePreview, inventory: getInventoryPreview, roadmap: getRoadmapPreview };

  const handleGenerate = useCallback(async () => {
    onActivate(type);
    setLoading(true);
    setError(null);
    try {
      const d = await fetchers[type](scanId);
      setPreviewData(d);
    } catch (e) {
      setError((e as Error).message || 'Failed to generate preview');
    } finally {
      setLoading(false);
    }
  }, [type, scanId]);

  const hasPreview = !!previewData;

  return (
    <div style={{
      background: SURF, border: isActive ? `1.5px solid ${ACCENT}` : BORDER,
      borderRadius: 14, padding: '22px 24px',
      boxShadow: isActive ? `0 0 0 3px ${ACCENT}14` : 'none',
      transition: 'all 0.15s',
    }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 12 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, flex: 1 }}>
          <div style={{
            width: 36, height: 36, borderRadius: 9, background: `${ACCENT}12`,
            display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
          }}>
            {cfg.icon}
          </div>
          <div>
            <div style={{ fontSize: 15, fontWeight: 700, color: TEXT }}>{cfg.title}</div>
            <div style={{ fontSize: 11, color: MUTED, marginTop: 2 }}>{cfg.audience}</div>
          </div>
        </div>
        {hasPreview && (
          <CheckCircle size={16} style={{ color: '#22c55e', flexShrink: 0, marginTop: 4 }} />
        )}
      </div>

      <p style={{ fontSize: 13, color: MUTED, marginTop: 12, marginBottom: 16, lineHeight: 1.6 }}>
        {cfg.desc}
      </p>

      {/* Actions */}
      <div style={{ display: 'flex', gap: 8, alignItems: 'center', position: 'relative' }}>
        <button
          onClick={handleGenerate}
          disabled={loading}
          style={{
            display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, fontWeight: 600,
            padding: '8px 16px', borderRadius: 8, border: 'none', cursor: loading ? 'not-allowed' : 'pointer',
            background: ACCENT, color: '#fff',
            opacity: loading ? 0.7 : 1, transition: 'opacity 0.15s',
          }}
        >
          {loading ? <Loader2 size={13} style={{ animation: 'spin 1s linear infinite' }} /> : <BarChart2 size={13} />}
          {loading ? 'Generating…' : 'Generate Preview'}
        </button>

        <div style={{ position: 'relative' }}>
          <button
            onClick={() => setMenuOpen(v => !v)}
            disabled={!hasPreview}
            style={{
              display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, fontWeight: 600,
              padding: '8px 14px', borderRadius: 8, cursor: hasPreview ? 'pointer' : 'not-allowed',
              border: `1px solid ${ACCENT}30`, background: `${ACCENT}08`, color: hasPreview ? ACCENT : MUTED2,
            }}
          >
            <Download size={13} /> Download <ChevronDown size={11} />
          </button>
          {menuOpen && hasPreview && (
            <DownloadMenu
              reportType={type}
              scanId={scanId}
              projName={projectName.replace(/[^\w\-]/g, '_').slice(0, 40)}
              onClose={() => setMenuOpen(false)}
            />
          )}
        </div>
      </div>

      {/* Error */}
      {error && (
        <div style={{
          marginTop: 12, background: '#fef2f2', border: '1px solid #fecaca',
          borderRadius: 8, padding: '9px 12px', fontSize: 12, color: '#b91c1c',
          display: 'flex', alignItems: 'center', gap: 8,
        }}>
          <AlertCircle size={14} style={{ flexShrink: 0 }} />
          {error}
          <button
            onClick={handleGenerate}
            style={{ marginLeft: 'auto', fontSize: 11, color: '#b91c1c', background: 'none', border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4 }}
          >
            <RefreshCw size={11} /> Retry
          </button>
        </div>
      )}
    </div>
  );
}

// ── Main page ──────────────────────────────────────────────────────────────────
export default function ReportsPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const urlScanId = searchParams.get('scan_id') ?? '';

  const [scans, setScans] = useState<CompletedScan[]>([]);
  const [selectedScanId, setSelectedScanId] = useState<string>(urlScanId);
  const [scansLoading, setScansLoading] = useState(true);
  const [scansError, setScansError] = useState<string | null>(null);
  const [activeReport, setActiveReport] = useState<ReportType | null>(null);

  // Preview state per report type
  const [previews, setPreviews] = useState<Record<ReportType, Record<string, unknown> | null>>({
    executive: null, inventory: null, roadmap: null,
  });
  const [previewLoading, setPreviewLoading] = useState<ReportType | null>(null);
  const [previewError, setPreviewError] = useState<Record<ReportType, string | null>>({
    executive: null, inventory: null, roadmap: null,
  });

  // Load scan list
  useEffect(() => {
    setScansLoading(true);
    listDashboardScans()
      .then(all => {
        const completed = all.filter((s: { status: string }) => s.status === 'completed');
        setScans(completed as CompletedScan[]);
        // prefer URL param, then first completed
        if (!selectedScanId && completed.length > 0) {
          setSelectedScanId(urlScanId || completed[0].scan_id);
        }
      })
      .catch(e => setScansError(e.message || 'Failed to load scans'))
      .finally(() => setScansLoading(false));
  }, []);

  // Active scan info
  const selectedScan = scans.find(s => s.scan_id === selectedScanId);
  const projectName  = selectedScan?.application_name || 'project';

  // Generate a specific preview
  const generatePreview = useCallback(async (type: ReportType) => {
    if (!selectedScanId) return;
    setActiveReport(type);
    setPreviewLoading(type);
    setPreviewError(prev => ({ ...prev, [type]: null }));
    const fetchers = { executive: getExecutivePreview, inventory: getInventoryPreview, roadmap: getRoadmapPreview };
    try {
      const d = await fetchers[type](selectedScanId);
      setPreviews(prev => ({ ...prev, [type]: d }));
    } catch (e) {
      setPreviewError(prev => ({ ...prev, [type]: (e as Error).message || 'Failed to generate preview' }));
    } finally {
      setPreviewLoading(null);
    }
  }, [selectedScanId]);

  return (
    <div style={{ display: 'flex', minHeight: '100dvh', background: BG, fontFamily: 'var(--font-body)', color: TEXT }}>
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      <AppSidebar activeKey="reports" scanId={selectedScanId || undefined} />

      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>

        {/* ── Header ── */}
        <div style={{
          background: SURF, borderBottom: BORDER, padding: '0 28px',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          height: 56, position: 'sticky', top: 0, zIndex: 10,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <FileText size={18} style={{ color: ACCENT }} />
            <span style={{ fontSize: 16, fontWeight: 700, fontFamily: 'var(--font-heading)', color: TEXT }}>
              Reports
            </span>
          </div>
          <button
            onClick={() => navigate('/dashboard')}
            style={{ display: 'flex', alignItems: 'center', gap: 5, fontSize: 12, color: MUTED, background: 'none', border: 'none', cursor: 'pointer' }}
          >
            Dashboard <ExternalLink size={12} />
          </button>
        </div>

        <div style={{ padding: '24px 28px', display: 'flex', flexDirection: 'column', gap: 24 }}>

          {/* ── Scan selector ── */}
          <div style={{ background: SURF, border: BORDER, borderRadius: 12, padding: '18px 20px' }}>
            <div style={{ fontSize: 12, fontWeight: 700, color: MUTED2, textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 10 }}>
              Select Scan
            </div>
            {scansLoading ? (
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: MUTED, fontSize: 13 }}>
                <Loader2 size={14} style={{ animation: 'spin 1s linear infinite' }} /> Loading scans…
              </div>
            ) : scansError ? (
              <div style={{ color: '#b91c1c', fontSize: 13, display: 'flex', alignItems: 'center', gap: 6 }}>
                <AlertCircle size={14} /> {scansError}
              </div>
            ) : scans.length === 0 ? (
              <div style={{
                textAlign: 'center', padding: '32px 24px',
                border: `2px dashed ${MUTED2}`, borderRadius: 10,
              }}>
                <Shield size={32} style={{ color: MUTED2, marginBottom: 12 }} />
                <div style={{ fontSize: 15, fontWeight: 600, marginBottom: 6 }}>No completed scans available for reporting.</div>
                <div style={{ fontSize: 13, color: MUTED, marginBottom: 16 }}>
                  Run a new scan and complete it first, then return here to generate reports.
                </div>
                <button
                  onClick={() => navigate('/scan')}
                  style={{ background: ACCENT, color: '#fff', border: 'none', borderRadius: 8, padding: '9px 20px', fontSize: 13, fontWeight: 600, cursor: 'pointer' }}
                >
                  Start New Scan
                </button>
              </div>
            ) : (
              <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
                <select
                  value={selectedScanId}
                  onChange={e => { setSelectedScanId(e.target.value); setPreviews({ executive: null, inventory: null, roadmap: null }); setActiveReport(null); }}
                  style={{
                    fontSize: 13, fontWeight: 500, color: TEXT,
                    background: BG, border: `1px solid rgba(25,40,55,0.15)`,
                    borderRadius: 8, padding: '8px 12px', cursor: 'pointer',
                    minWidth: 280,
                  }}
                >
                  {scans.map(s => (
                    <option key={s.scan_id} value={s.scan_id}>
                      {s.scan_name || s.application_name} — {s.application_name} ({s.finding_count} findings)
                    </option>
                  ))}
                </select>
                {selectedScan && (
                  <span style={{ fontSize: 12, color: MUTED }}>
                    Completed {selectedScan.completed_at ? new Date(selectedScan.completed_at).toLocaleDateString() : '—'}
                  </span>
                )}

                {selectedScanId && (
                  <button
                    onClick={() => downloadAllReports(selectedScanId)}
                    style={{
                      marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 6,
                      fontSize: 12, fontWeight: 600, padding: '7px 14px', borderRadius: 8,
                      background: `${ACCENT}10`, border: `1px solid ${ACCENT}30`, color: ACCENT, cursor: 'pointer',
                    }}
                  >
                    <Archive size={13} /> Download All Reports (.zip)
                  </button>
                )}
              </div>
            )}
          </div>

          {/* ── Report cards ── */}
          {selectedScanId && scans.length > 0 && (
            <>
              <div style={{
                display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
                gap: 16,
              }}>
                {(['executive', 'inventory', 'roadmap'] as ReportType[]).map(type => (
                  <ReportCard
                    key={type}
                    type={type}
                    scanId={selectedScanId}
                    projectName={projectName}
                    isActive={activeReport === type}
                    onActivate={t => generatePreview(t)}
                  />
                ))}
              </div>

              {/* ── Preview panel ── */}
              {(activeReport || previewLoading) && (
                <div style={{
                  background: SURF, border: BORDER, borderRadius: 14,
                  overflow: 'hidden',
                }}>
                  {/* Preview tab bar */}
                  <div style={{
                    display: 'flex', borderBottom: BORDER, background: BG,
                  }}>
                    {(['executive', 'inventory', 'roadmap'] as ReportType[]).map(type => {
                      const isActive = activeReport === type;
                      const hasData  = !!previews[type];
                      return (
                        <button
                          key={type}
                          onClick={() => hasData && setActiveReport(type)}
                          style={{
                            display: 'flex', alignItems: 'center', gap: 6,
                            padding: '12px 18px', fontSize: 12, fontWeight: 600,
                            color: isActive ? ACCENT : hasData ? TEXT : MUTED2,
                            background: isActive ? SURF : 'transparent',
                            border: 'none', cursor: hasData ? 'pointer' : 'default',
                            borderBottom: isActive ? `2px solid ${ACCENT}` : '2px solid transparent',
                          }}
                        >
                          {previewLoading === type
                            ? <Loader2 size={12} style={{ animation: 'spin 1s linear infinite' }} />
                            : hasData ? <CheckCircle size={12} style={{ color: '#22c55e' }} /> : <ChevronRight size={12} />
                          }
                          {REPORT_CFG[type].title.split(' ').slice(0, 2).join(' ')}
                        </button>
                      );
                    })}
                  </div>

                  {/* Preview content */}
                  <div style={{ padding: '24px 28px' }}>
                    {activeReport && previewLoading === activeReport && (
                      <div style={{ textAlign: 'center', padding: '48px 0', color: MUTED }}>
                        <Loader2 size={28} style={{ animation: 'spin 1s linear infinite', color: ACCENT, marginBottom: 12 }} />
                        <div style={{ fontSize: 14 }}>Generating {REPORT_CFG[activeReport].title} preview…</div>
                      </div>
                    )}

                    {activeReport && previewError[activeReport] && (
                      <div style={{
                        background: '#fef2f2', border: '1px solid #fecaca', borderRadius: 10,
                        padding: '20px 24px', color: '#b91c1c', fontSize: 13,
                        display: 'flex', alignItems: 'center', gap: 10,
                      }}>
                        <AlertCircle size={18} />
                        <div>
                          <div style={{ fontWeight: 600, marginBottom: 4 }}>Preview generation failed</div>
                          <div>{previewError[activeReport]}</div>
                        </div>
                        <button
                          onClick={() => generatePreview(activeReport)}
                          style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 4, fontSize: 12, color: '#b91c1c', background: 'none', border: '1px solid #fecaca', borderRadius: 6, padding: '5px 10px', cursor: 'pointer' }}
                        >
                          <RefreshCw size={11} /> Retry
                        </button>
                      </div>
                    )}

                    {activeReport && previews[activeReport] && !previewLoading && (
                      <>
                        <div style={{
                          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                          marginBottom: 20, paddingBottom: 12, borderBottom: BORDER,
                        }}>
                          <div>
                            <div style={{ fontSize: 16, fontWeight: 700, color: TEXT }}>{REPORT_CFG[activeReport].title}</div>
                            <div style={{ fontSize: 12, color: MUTED, marginTop: 2 }}>Preview — {REPORT_CFG[activeReport].audience}</div>
                          </div>
                          <button
                            onClick={() => downloadPdf(activeReport, selectedScanId)}
                            style={{
                              display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, fontWeight: 600,
                              padding: '7px 14px', borderRadius: 8, background: ACCENT, color: '#fff',
                              border: 'none', cursor: 'pointer',
                            }}
                          >
                            <Download size={13} /> Download PDF
                          </button>
                        </div>

                        {activeReport === 'executive' && <ExecutivePreview data={previews.executive!} />}
                        {activeReport === 'inventory' && <InventoryPreview data={previews.inventory!} />}
                        {activeReport === 'roadmap'   && <RoadmapPreview   data={previews.roadmap!} />}

                        <div style={{
                          marginTop: 24, padding: '12px 16px', borderRadius: 9,
                          background: `${ACCENT}08`, border: `1px solid ${ACCENT}20`,
                          fontSize: 11, color: MUTED, lineHeight: 1.6,
                        }}>
                          <strong>Disclaimer:</strong> QShield Quantum Readiness Scores are internal
                          deterministic prioritization metrics — not official NIST scores or compliance
                          certifications. Certificate private key material is never included in reports.
                          Findings are based on static analysis at the time of scan.
                        </div>
                      </>
                    )}

                    {!activeReport && (
                      <div style={{ textAlign: 'center', padding: '48px 0', color: MUTED }}>
                        <FileText size={36} style={{ color: MUTED2, marginBottom: 12 }} />
                        <div style={{ fontSize: 14 }}>Click "Generate Preview" on a report card to view the data preview here.</div>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

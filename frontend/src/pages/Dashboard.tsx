/**
 * DashboardPage.tsx — QShield Executive Overview
 *
 * Information hierarchy:
 *   LEVEL 1 — Quantum Readiness Score (readiness ring + posture summary)
 *   LEVEL 2 — Algorithm distribution + Risk/Severity distribution
 *   LEVEL 3 — Migration Status (lifecycle bar + wave summary)
 *   LEVEL 4 — Priority Attention (top assets + highest-risk findings)
 *
 * All values from /api/dashboard — nothing hardcoded.
 * Route: /dashboard
 *        /dashboard?scan_id=<id>  (deep-link for specific scan)
 */
import { useEffect, useState, useCallback } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import {
  RefreshCw, AlertTriangle, ChevronRight, Shield, Info,
  Upload, Activity, ArrowRight,
} from 'lucide-react';
import AppSidebar from '../components/AppSidebar';
import {
  listDashboardScans,
  getDashboardSummary,
} from '../services/dashboardApi';
import type {
  DashboardSummary,
  ScanOption,
  AlgorithmCount,
  SeverityCount,
  StageCount,
  WaveCount,
  TopFinding,
  TopAsset,
} from '../services/dashboardApi';

// ── Design tokens ─────────────────────────────────────────────────────────────

const BORDER  = '1px solid rgba(25,40,55,0.09)';
const BORDER2 = '1px solid rgba(25,40,55,0.06)';
const TEXT    = '#192837';
const MUTED   = 'rgba(25,40,55,0.45)';
const MUTED2  = 'rgba(25,40,55,0.30)';
const BG_PAGE = '#f8f8f5';
const BG_SURF = '#ffffff';
const ACCENT  = '#7342E2';

// Semantic colors
const SEV_COLOR: Record<string, { bg: string; text: string; border: string; bar: string }> = {
  Critical: { bg: '#fef2f2', text: '#b91c1c', border: '#fecaca', bar: '#ef4444' },
  High:     { bg: '#fff7ed', text: '#c2410c', border: '#fed7aa', bar: '#f97316' },
  Moderate: { bg: '#fffbeb', text: '#92400e', border: '#fde68a', bar: '#f59e0b' },
  Low:      { bg: '#eff6ff', text: '#1e40af', border: '#bfdbfe', bar: '#3b82f6' },
  Safe:     { bg: '#f0fdf4', text: '#15803d', border: '#bbf7d0', bar: '#22c55e' },
};
const sevColor = (s: string) => SEV_COLOR[s] ?? SEV_COLOR.Low;

const STAGE_COLOR: Record<string, string> = {
  DISCOVERED: '#94a3b8',
  ASSESSED:   '#3b82f6',
  PLANNED:    '#8b5cf6',
  PILOT:      '#f59e0b',
  TRANSITION: '#f97316',
  VALIDATION: '#ef4444',
  MIGRATED:   '#22c55e',
};

// Stage order is supplied by the backend stage_distribution array.

// ── Sidebar handled by shared AppSidebar component ───────────────────────────

// ── Readiness Ring (SVG) ──────────────────────────────────────────────────────

function ReadinessRing({ score, label }: { score: number; label: string }) {
  const radius = 52;
  const stroke = 7;
  const circ = 2 * Math.PI * radius;
  const arc = circ * 0.75;   // 270° sweep
  const filled = arc * (score / 100);
  const empty = arc - filled;
  const offset_start = circ * 0.125; // start at 135°

  const ringColor =
    score >= 70 ? '#22c55e' :
    score >= 50 ? '#f59e0b' :
    score >= 30 ? '#f97316' :
    '#ef4444';

  const size = (radius + stroke) * 2 + 4;
  const cx = size / 2;
  const cy = size / 2;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8 }}>
      <svg width={size} height={size} role="img" aria-label={`Quantum readiness score: ${score} out of 100. ${label}.`}>
        {/* Track */}
        <circle
          cx={cx} cy={cy} r={radius}
          fill="none" stroke="#e5e7eb" strokeWidth={stroke}
          strokeDasharray={`${arc} ${circ - arc}`}
          strokeDashoffset={-offset_start}
          strokeLinecap="round"
          style={{ transform: `rotate(-90deg)`, transformOrigin: `${cx}px ${cy}px` }}
        />
        {/* Filled arc */}
        <circle
          cx={cx} cy={cy} r={radius}
          fill="none" stroke={ringColor} strokeWidth={stroke}
          strokeDasharray={`${filled} ${empty + circ - arc}`}
          strokeDashoffset={-offset_start}
          strokeLinecap="round"
          style={{ transform: `rotate(-90deg)`, transformOrigin: `${cx}px ${cy}px` }}
        />
        {/* Score text */}
        <text x={cx} y={cy - 6} textAnchor="middle" fill={TEXT}
              fontSize="24" fontWeight="700" fontFamily="var(--font-heading)">
          {score}
        </text>
        <text x={cx} y={cy + 14} textAnchor="middle" fill={MUTED}
              fontSize="10" fontWeight="500">
          / 100
        </text>
      </svg>
      <span style={{ fontSize: 13, fontWeight: 600, color: ringColor }}>{label}</span>
    </div>
  );
}

// ── Skeleton loaders ──────────────────────────────────────────────────────────

function Skeleton({ w = '100%', h = 16, radius = 6 }: { w?: string | number; h?: number; radius?: number }) {
  return (
    <div style={{
      width: w, height: h, borderRadius: radius,
      background: 'linear-gradient(90deg, #f0f0ee 25%, #e8e8e6 50%, #f0f0ee 75%)',
      backgroundSize: '200% 100%',
      animation: 'shimmer 1.4s infinite',
    }} />
  );
}

// ── Horizontal bar chart ──────────────────────────────────────────────────────

function HBar({ label, count, maxCount, color, barColor }: {
  label: string; count: number; maxCount: number; color: string; barColor: string;
}) {
  const pct = maxCount > 0 ? (count / maxCount) * 100 : 0;
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 5 }}>
      <div style={{ width: 80, fontSize: 11, fontWeight: 500, color: TEXT, textAlign: 'right', flexShrink: 0 }}>
        {label}
      </div>
      <div style={{ flex: 1, background: '#f1f5f9', borderRadius: 4, height: 10, overflow: 'hidden' }}
           role="progressbar" aria-valuenow={count} aria-valuemax={maxCount} aria-label={`${label}: ${count}`}>
        <div style={{
          width: `${pct}%`, height: '100%',
          background: barColor, borderRadius: 4,
          transition: 'width 0.4s ease',
        }} />
      </div>
      <div style={{ width: 28, fontSize: 11, fontWeight: 600, color, flexShrink: 0, textAlign: 'right' }}>
        {count}
      </div>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function DashboardPage() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const urlScanId = searchParams.get('scan_id') ?? undefined;

  const [scans, setScans] = useState<ScanOption[]>([]);
  const [selectedScanId, setSelectedScanId] = useState<string | undefined>(urlScanId);
  const [data, setData] = useState<DashboardSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [scansLoading, setScansLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showMethodology, setShowMethodology] = useState(false);

  // Load scan list on mount
  useEffect(() => {
    setScansLoading(true);
    listDashboardScans()
      .then(list => {
        setScans(list);
        // Auto-select most recent completed scan if none specified
        if (!selectedScanId) {
          const completed = list.find(s => s.status === 'completed');
          if (completed) {
            setSelectedScanId(completed.scan_id);
          }
        }
      })
      .catch(err => setError(err.message))
      .finally(() => setScansLoading(false));
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Load dashboard data when scan changes
  const loadDashboard = useCallback(async (scanId: string) => {
    setLoading(true);
    setError(null);
    try {
      const result = await getDashboardSummary(scanId);
      setData(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load dashboard');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (selectedScanId) {
      loadDashboard(selectedScanId);
      setSearchParams({ scan_id: selectedScanId }, { replace: true });
    }
  }, [selectedScanId, loadDashboard, setSearchParams]);

  const handleScanChange = (scanId: string) => {
    setSelectedScanId(scanId);
  };

  // ── No scan at all — onboarding empty state ───────────────────────────────
  if (!scansLoading && scans.length === 0 && !selectedScanId) {
    return (
      <div style={{ display: 'flex', minHeight: '100dvh', background: BG_PAGE }}>
        <AppSidebar activeKey="dashboard" />
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
          <PageHeader
            appName={null} scanId={undefined} scans={[]}
            selectedScanId={undefined} onScanChange={handleScanChange}
            onRefresh={() => {}} navigate={navigate}
          />
          <div style={{
            flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center',
            justifyContent: 'center', padding: '40px 28px', gap: 20, textAlign: 'center',
          }}>
            <Shield size={48} style={{ color: ACCENT, opacity: 0.5 }} />
            <div>
              <div style={{ fontSize: 20, fontWeight: 700, color: TEXT, marginBottom: 6, fontFamily: 'var(--font-heading)' }}>
                No security posture data yet
              </div>
              <div style={{ fontSize: 13, color: MUTED, maxWidth: 380 }}>
                Run a scan to discover cryptographic usage and calculate quantum migration readiness.
              </div>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, color: MUTED2, marginTop: 4 }}>
              <span>Discovery</span><ArrowRight size={12} />
              <span>Risk Analysis</span><ArrowRight size={12} />
              <span>Recommendations</span><ArrowRight size={12} />
              <span>Roadmap</span>
            </div>
            <Link to="/scan" style={{
              display: 'inline-flex', alignItems: 'center', gap: 6,
              padding: '9px 20px', borderRadius: 8, background: ACCENT,
              color: '#fff', fontWeight: 600, fontSize: 13, textDecoration: 'none',
            }}>
              <Upload size={14} /> Run First Scan
            </Link>
          </div>
        </div>
      </div>
    );
  }

  // ── Loading skeletons ─────────────────────────────────────────────────────
  if (loading || (scansLoading && !data)) {
    return (
      <div style={{ display: 'flex', minHeight: '100dvh', background: BG_PAGE }}>
        <AppSidebar activeKey="dashboard" scanId={selectedScanId} />
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
          <PageHeader
            appName={null} scanId={selectedScanId} scans={scans}
            selectedScanId={selectedScanId} onScanChange={handleScanChange}
            onRefresh={() => selectedScanId && loadDashboard(selectedScanId)} navigate={navigate}
          />
          <style>{`@keyframes shimmer { 0%{background-position:200% 0} 100%{background-position:-200% 0} }`}</style>
          <div style={{ padding: '24px 28px', display: 'flex', flexDirection: 'column', gap: 18 }}>
            {/* Readiness hero skeleton */}
            <div style={{ display: 'flex', gap: 18 }}>
              <div style={{ flex: '0 0 300px', background: BG_SURF, border: BORDER, borderRadius: 12, padding: 24, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 16 }}>
                <Skeleton w={120} h={120} radius={60} />
                <Skeleton w={140} h={14} />
                <Skeleton w={200} h={12} />
              </div>
              <div style={{ flex: 1, background: BG_SURF, border: BORDER, borderRadius: 12, padding: 24, display: 'flex', flexDirection: 'column', gap: 14 }}>
                <div style={{ display: 'flex', gap: 16 }}>
                  {[1,2,3,4].map(i => <div key={i} style={{ flex: 1 }}><Skeleton h={40} /><Skeleton w="60%" h={12} /></div>)}
                </div>
                <Skeleton w={200} h={12} />
              </div>
            </div>
            {/* Charts skeleton */}
            <div style={{ display: 'flex', gap: 18 }}>
              {[1,2].map(i => (
                <div key={i} style={{ flex: 1, background: BG_SURF, border: BORDER, borderRadius: 12, padding: 24, display: 'flex', flexDirection: 'column', gap: 10 }}>
                  <Skeleton w="50%" h={14} />
                  {[1,2,3,4].map(j => <Skeleton key={j} h={12} />)}
                </div>
              ))}
            </div>
            {/* Migration skeleton */}
            <div style={{ background: BG_SURF, border: BORDER, borderRadius: 12, padding: 24 }}>
              <Skeleton w="30%" h={14} />
              <div style={{ marginTop: 16, display: 'flex', gap: 8 }}>
                {[1,2,3,4,5,6,7].map(i => <div key={i} style={{ flex: 1 }}><Skeleton h={28} radius={14} /><Skeleton w="80%" h={10} /></div>)}
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // ── Error state ───────────────────────────────────────────────────────────
  if (error && !data) {
    return (
      <div style={{ display: 'flex', minHeight: '100dvh', background: BG_PAGE }}>
        <AppSidebar activeKey="dashboard" scanId={selectedScanId} />
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
          <PageHeader
            appName={null} scanId={selectedScanId} scans={scans}
            selectedScanId={selectedScanId} onScanChange={handleScanChange}
            onRefresh={() => selectedScanId && loadDashboard(selectedScanId)} navigate={navigate}
          />
          <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 40 }}>
            <div style={{ background: BG_SURF, border: '1px solid #fecaca', borderRadius: 12, padding: '32px 40px', textAlign: 'center', maxWidth: 440 }}>
              <AlertTriangle size={32} style={{ color: '#ef4444', marginBottom: 12 }} />
              <div style={{ fontSize: 15, fontWeight: 600, color: TEXT, marginBottom: 6 }}>Dashboard Failed</div>
              <div style={{ fontSize: 13, color: MUTED, marginBottom: 20 }}>{error}</div>
              <button
                onClick={() => selectedScanId && loadDashboard(selectedScanId)}
                style={{ display: 'inline-flex', alignItems: 'center', gap: 6, padding: '7px 16px', borderRadius: 7, border: BORDER, background: BG_SURF, fontSize: 13, cursor: 'pointer', color: TEXT }}
              >
                <RefreshCw size={13} /> Retry
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (!data) return null;

  // ── No findings state ────────────────────────────────────────────────────
  const noFindings = data.total_findings === 0;

  // Compute max for chart scales
  const maxAlgo = Math.max(...data.algorithm_distribution.map(a => a.count), 1);
  const maxSev  = Math.max(...data.severity_distribution.map(s => s.count), 1);

  return (
    <div style={{ display: 'flex', minHeight: '100dvh', background: BG_PAGE, fontFamily: 'var(--font-body)', color: TEXT }}>
      <style>{`@keyframes shimmer { 0%{background-position:200% 0} 100%{background-position:-200% 0} }`}</style>
      <AppSidebar activeKey="dashboard" scanId={selectedScanId} />

      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
        <PageHeader
          appName={data.application_name} scanId={selectedScanId}
          scans={scans} selectedScanId={selectedScanId}
          onScanChange={handleScanChange}
          onRefresh={() => selectedScanId && loadDashboard(selectedScanId)}
          navigate={navigate}
        />

        {/* ── Body ── */}
        <div style={{ padding: '24px 28px', display: 'flex', flexDirection: 'column', gap: 18 }}>

          {/* Scanning banner */}
          {data.has_running_scan && (
            <div style={{
              display: 'flex', alignItems: 'center', gap: 10,
              background: '#eff6ff', border: '1px solid #bfdbfe',
              borderRadius: 8, padding: '10px 14px', fontSize: 12, color: '#1e40af',
            }}>
              <Activity size={14} style={{ flexShrink: 0 }} />
              Scan in progress — dashboard data will update when analysis completes.
            </div>
          )}

          {/* No findings info banner */}
          {noFindings && (
            <div style={{
              display: 'flex', alignItems: 'flex-start', gap: 10,
              background: '#f0fdf4', border: '1px solid #bbf7d0',
              borderRadius: 8, padding: '10px 14px', fontSize: 12, color: '#15803d',
            }}>
              <Info size={14} style={{ flexShrink: 0, marginTop: 1 }} />
              <span>
                <strong>No cryptographic usage was detected in the scanned scope.</strong>{' '}
                This may indicate a clean codebase or an incomplete scan. The readiness score
                defaults to 100 when there is no measured exposure.
              </span>
            </div>
          )}

          {/* ══ SECTION 1 — READINESS HERO ══ */}
          <div style={{ display: 'flex', gap: 18, flexWrap: 'wrap' }}>

            {/* Readiness ring card */}
            <div style={{
              flex: '0 0 280px', background: BG_SURF, border: BORDER, borderRadius: 12,
              padding: '24px 20px', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 12,
            }}>
              <div style={{ fontSize: 11, fontWeight: 600, color: MUTED2, textTransform: 'uppercase', letterSpacing: '0.07em', alignSelf: 'flex-start' }}>
                Quantum Readiness
              </div>
              <ReadinessRing score={data.quantum_readiness_score} label={data.readiness_label} />
              <div style={{ fontSize: 11, color: MUTED, textAlign: 'center', lineHeight: 1.5 }}>
                Deterministic QShield score.
              </div>
              <button
                onClick={() => setShowMethodology(m => !m)}
                style={{
                  fontSize: 11, color: ACCENT, background: 'transparent',
                  border: 'none', cursor: 'pointer', textDecoration: 'underline', padding: 0,
                }}
                aria-expanded={showMethodology}
              >
                {showMethodology ? 'Hide' : 'How is this calculated?'}
              </button>
              {showMethodology && (
                <div style={{
                  background: '#f5f3ff', border: '1px solid #ede9fe',
                  borderRadius: 8, padding: '10px 12px', fontSize: 11, color: '#4c1d95',
                  lineHeight: 1.55, maxHeight: 180, overflowY: 'auto',
                }}>
                  <strong>Formula:</strong>{' '}
                  {data.readiness_methodology.description}
                  <br /><br />
                  <strong>Components this scan:</strong><br />
                  Exposure: {(data.readiness_methodology.s_exposure * 100).toFixed(1)}% ×60%<br />
                  Risk Inv: {(data.readiness_methodology.s_risk_inv * 100).toFixed(1)}% ×25%<br />
                  Progress: {(data.readiness_methodology.s_progress * 100).toFixed(1)}% ×15%<br />
                  <br />
                  <em style={{ color: '#6d28d9', fontSize: 10 }}>{data.readiness_methodology.disclaimer}</em>
                </div>
              )}
            </div>

            {/* Posture summary card */}
            <div style={{
              flex: 1, minWidth: 260,
              background: BG_SURF, border: BORDER, borderRadius: 12,
              padding: '20px 24px', display: 'flex', flexDirection: 'column', gap: 14,
            }}>
              <div style={{ fontSize: 11, fontWeight: 600, color: MUTED2, textTransform: 'uppercase', letterSpacing: '0.07em' }}>
                Posture Summary
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 0 }}>
                {[
                  { label: 'Total Findings', value: data.total_findings, color: TEXT },
                  { label: 'Quantum Relevant', value: data.quantum_relevant_findings, color: '#c2410c' },
                  { label: 'Critical', value: data.critical_findings, color: '#b91c1c' },
                  { label: 'High', value: data.high_findings, color: '#c2410c' },
                  { label: 'Quantum Safe', value: data.quantum_safe_findings, color: '#15803d' },
                ].map((m, i, arr) => (
                  <div key={m.label} style={{
                    flex: '1 1 80px', padding: '10px 14px',
                    borderRight: i < arr.length - 1 ? BORDER2 : 'none',
                    display: 'flex', flexDirection: 'column', gap: 3,
                  }}>
                    <div style={{ fontSize: 24, fontWeight: 700, color: m.color, fontFamily: 'var(--font-heading)', lineHeight: 1 }}>
                      {m.value}
                    </div>
                    <div style={{ fontSize: 10, color: MUTED, fontWeight: 500 }}>{m.label}</div>
                  </div>
                ))}
              </div>

              {/* Last scan info */}
              <div style={{ borderTop: BORDER2, paddingTop: 10, display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
                <span style={{ fontSize: 11, color: MUTED }}>
                  Scan: <strong style={{ color: TEXT }}>{data.scan_name}</strong>
                </span>
                {data.completed_at && (
                  <span style={{ fontSize: 11, color: MUTED }}>
                    Completed: {new Date(data.completed_at).toLocaleDateString()}
                  </span>
                )}
                <StatusBadge status={data.scan_status} />
              </div>

              {/* Quick actions */}
              <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
                {selectedScanId && (
                  <>
                    <Link to={`/risk/${selectedScanId}`} style={{ fontSize: 12, color: ACCENT, textDecoration: 'none', display: 'flex', alignItems: 'center', gap: 4 }}>
                      Risk Analysis <ChevronRight size={11} />
                    </Link>
                    <Link to={`/inventory/${selectedScanId}`} style={{ fontSize: 12, color: ACCENT, textDecoration: 'none', display: 'flex', alignItems: 'center', gap: 4 }}>
                      Crypto Inventory <ChevronRight size={11} />
                    </Link>
                  </>
                )}
              </div>
            </div>
          </div>

          {/* ══ SECTION 2 — SECURITY POSTURE ANALYTICS ══ */}
          {!noFindings && (
            <div style={{ display: 'flex', gap: 18, flexWrap: 'wrap' }}>

              {/* Algorithm Distribution */}
              <div style={{ flex: 1, minWidth: 240, background: BG_SURF, border: BORDER, borderRadius: 12, padding: '20px 24px', display: 'flex', flexDirection: 'column', gap: 12 }}>
                <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
                  <div style={{ fontSize: 11, fontWeight: 600, color: MUTED2, textTransform: 'uppercase', letterSpacing: '0.07em' }}>
                    Algorithm Distribution
                  </div>
                  {selectedScanId && (
                    <Link to={`/inventory/${selectedScanId}`} style={{ fontSize: 11, color: ACCENT, textDecoration: 'none' }}>
                      View Inventory →
                    </Link>
                  )}
                </div>
                <div role="list" aria-label="Algorithm family distribution">
                  {data.algorithm_distribution.length === 0 && (
                    <div style={{ fontSize: 12, color: MUTED }}>No algorithm data available.</div>
                  )}
                  {data.algorithm_distribution.map((a: AlgorithmCount) => (
                    <div key={a.family} role="listitem">
                      <HBar
                        label={a.family} count={a.count} maxCount={maxAlgo}
                        color={TEXT} barColor={ACCENT}
                      />
                    </div>
                  ))}
                </div>
              </div>

              {/* Risk / Severity Distribution */}
              <div style={{ flex: 1, minWidth: 240, background: BG_SURF, border: BORDER, borderRadius: 12, padding: '20px 24px', display: 'flex', flexDirection: 'column', gap: 12 }}>
                <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between' }}>
                  <div style={{ fontSize: 11, fontWeight: 600, color: MUTED2, textTransform: 'uppercase', letterSpacing: '0.07em' }}>
                    Risk / Severity Distribution
                  </div>
                  {selectedScanId && (
                    <Link to={`/risk/${selectedScanId}`} style={{ fontSize: 11, color: ACCENT, textDecoration: 'none' }}>
                      View Risk →
                    </Link>
                  )}
                </div>
                <div role="list" aria-label="Severity distribution">
                  {data.severity_distribution.map((s: SeverityCount) => {
                    const cfg = sevColor(s.severity);
                    return (
                      <div key={s.severity} role="listitem">
                        <HBar
                          label={s.severity} count={s.count} maxCount={maxSev}
                          color={cfg.text} barColor={cfg.bar}
                        />
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          )}

          {/* ══ SECTION 3 — MIGRATION STATUS ══ */}
          <div style={{ background: BG_SURF, border: BORDER, borderRadius: 12, padding: '20px 24px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 16, flexWrap: 'wrap', gap: 8 }}>
              <div>
                <div style={{ fontSize: 11, fontWeight: 600, color: MUTED2, textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: 4 }}>
                  Migration Status
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  <span style={{ fontSize: 20, fontWeight: 700, color: TEXT, fontFamily: 'var(--font-heading)' }}>
                    {data.migration_progress_pct.toFixed(0)}%
                  </span>
                  <span style={{ fontSize: 12, color: MUTED }}>
                    migration progress · {data.migrated_items}/{data.total_roadmap_items} items migrated
                  </span>
                </div>
              </div>
              {selectedScanId && (
                <Link to={`/roadmap/${selectedScanId}`} style={{
                  display: 'inline-flex', alignItems: 'center', gap: 5,
                  fontSize: 12, color: ACCENT, textDecoration: 'none',
                  padding: '5px 12px', border: `1px solid ${ACCENT}30`,
                  borderRadius: 7, fontWeight: 500,
                }}>
                  Open Migration Roadmap <ChevronRight size={12} />
                </Link>
              )}
            </div>

            {/* Overall progress bar */}
            {data.total_roadmap_items > 0 && (
              <div style={{ marginBottom: 18 }}>
                <div style={{
                  height: 8, background: '#f1f5f9', borderRadius: 4, overflow: 'hidden',
                }} role="progressbar" aria-valuenow={data.migration_progress_pct} aria-valuemax={100}
                   aria-label={`Migration progress: ${data.migration_progress_pct.toFixed(0)}%`}>
                  <div style={{
                    width: `${data.migration_progress_pct}%`, height: '100%',
                    background: 'linear-gradient(to right, #8b5cf6, #22c55e)',
                    borderRadius: 4, transition: 'width 0.5s ease',
                  }} />
                </div>
              </div>
            )}

            {/* Lifecycle stage nodes */}
            <div style={{ fontSize: 10, fontWeight: 600, color: MUTED2, textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 8 }}>
              Lifecycle Stage Distribution
            </div>
            <div style={{
              display: 'flex', alignItems: 'center',
              overflowX: 'auto', paddingBottom: 4,
              gap: 0,
            }} role="list" aria-label="Migration lifecycle stages">
              {data.stage_distribution.map((s: StageCount, idx: number) => {
                const isLast = idx === data.stage_distribution.length - 1;
                const hasItems = s.count > 0;
                const stageColor = STAGE_COLOR[s.stage] ?? '#94a3b8';
                return (
                  <div key={s.stage} style={{ display: 'flex', alignItems: 'center', flexShrink: 0 }} role="listitem">
                    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}>
                      <div style={{
                        width: 30, height: 30, borderRadius: '50%',
                        background: hasItems ? `${stageColor}20` : '#f1f5f9',
                        border: `2px solid ${hasItems ? stageColor : '#e2e8f0'}`,
                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                        fontSize: 11, fontWeight: 700,
                        color: hasItems ? stageColor : MUTED2,
                      }} aria-label={`${s.stage}: ${s.count} items`}>
                        {s.count}
                      </div>
                      <div style={{
                        fontSize: 9, fontWeight: hasItems ? 700 : 400,
                        color: hasItems ? stageColor : MUTED2,
                        textTransform: 'uppercase', letterSpacing: '0.04em',
                        textAlign: 'center', maxWidth: 56, lineHeight: 1.2,
                      }}>
                        {s.stage}
                      </div>
                    </div>
                    {!isLast && (
                      <div style={{
                        width: 20, height: 2, flexShrink: 0,
                        background: hasItems ? `${stageColor}50` : '#e2e8f0',
                        marginBottom: 18,
                      }} />
                    )}
                  </div>
                );
              })}
            </div>

            {/* Wave summary */}
            {data.total_roadmap_items > 0 && (
              <div style={{ marginTop: 14, borderTop: BORDER2, paddingTop: 14 }}>
                <div style={{ fontSize: 10, fontWeight: 600, color: MUTED2, textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 10 }}>
                  Wave Distribution
                </div>
                <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
                  {data.wave_distribution.map((w: WaveCount) => {
                    const wCfg = w.wave === 1
                      ? { border: '#ef4444', bg: '#fef2f2', text: '#b91c1c' }
                      : w.wave === 2
                        ? { border: '#f97316', bg: '#fff7ed', text: '#c2410c' }
                        : { border: '#a3e635', bg: '#f7fee7', text: '#3f6212' };
                    return (
                      <div key={w.wave} style={{
                        display: 'flex', alignItems: 'center', gap: 10,
                        background: wCfg.bg, border: `1.5px solid ${wCfg.border}`,
                        borderRadius: 8, padding: '8px 14px', minWidth: 120,
                      }}>
                        <div>
                          <div style={{ fontSize: 10, fontWeight: 700, color: wCfg.text, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                            Wave {w.wave} — {w.label}
                          </div>
                          <div style={{ fontSize: 20, fontWeight: 700, color: wCfg.text, fontFamily: 'var(--font-heading)', lineHeight: 1.1 }}>
                            {w.count}
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {data.total_roadmap_items === 0 && (
              <div style={{ fontSize: 12, color: MUTED, marginTop: 8 }}>
                No roadmap items yet.{' '}
                {selectedScanId && (
                  <Link to={`/risk/${selectedScanId}`} style={{ color: ACCENT }}>Run risk analysis</Link>
                )}{' '}
                to generate them.
              </div>
            )}
          </div>

          {/* ══ SECTION 4 — PRIORITY ATTENTION ══ */}
          {!noFindings && (
            <div style={{ display: 'flex', gap: 18, flexWrap: 'wrap' }}>

              {/* Top Priority Assets */}
              <div style={{ flex: 1, minWidth: 240, background: BG_SURF, border: BORDER, borderRadius: 12, padding: '20px 24px', display: 'flex', flexDirection: 'column', gap: 10 }}>
                <div style={{ fontSize: 11, fontWeight: 600, color: MUTED2, textTransform: 'uppercase', letterSpacing: '0.07em' }}>
                  Top Priority Assets
                </div>
                {data.top_assets.length === 0 && (
                  <div style={{ fontSize: 12, color: MUTED }}>No application data available.</div>
                )}
                {data.top_assets.map((a: TopAsset) => {
                  const sc = sevColor(a.highest_severity);
                  return (
                    <div key={a.application_id} style={{
                      display: 'flex', alignItems: 'center', gap: 10,
                      padding: '8px 0', borderBottom: BORDER2,
                    }}>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ fontSize: 13, fontWeight: 600, color: TEXT, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {a.application_name}
                        </div>
                        <div style={{ fontSize: 11, color: MUTED, marginTop: 2 }}>
                          {a.relevant_findings} quantum-relevant finding{a.relevant_findings !== 1 ? 's' : ''}
                        </div>
                      </div>
                      <span style={{
                        fontSize: 10, fontWeight: 700,
                        background: sc.bg, color: sc.text, border: `1px solid ${sc.border}`,
                        borderRadius: 5, padding: '2px 7px',
                      }}>
                        {a.highest_severity}
                      </span>
                      {a.wave != null && (
                        <span style={{ fontSize: 10, fontWeight: 600, color: MUTED2, background: '#f8f8f8', border: BORDER, borderRadius: 5, padding: '2px 6px' }}>
                          W{a.wave}
                        </span>
                      )}
                    </div>
                  );
                })}
                <Link to="/scan" style={{ fontSize: 12, color: ACCENT, textDecoration: 'none', display: 'flex', alignItems: 'center', gap: 4, marginTop: 4 }}>
                  <ChevronRight size={12} /> View Applications
                </Link>
              </div>

              {/* Highest-Risk Findings */}
              <div style={{ flex: 1, minWidth: 240, background: BG_SURF, border: BORDER, borderRadius: 12, padding: '20px 24px', display: 'flex', flexDirection: 'column', gap: 10 }}>
                <div style={{ fontSize: 11, fontWeight: 600, color: MUTED2, textTransform: 'uppercase', letterSpacing: '0.07em' }}>
                  Highest-Risk Findings
                </div>
                {data.top_findings.length === 0 && (
                  <div style={{ fontSize: 12, color: MUTED }}>No findings with risk scores yet.</div>
                )}
                {data.top_findings.map((f: TopFinding) => {
                  const sc = sevColor(f.severity);
                  return (
                    <Link
                      key={f.finding_id}
                      to={`/inventory/${f.scan_id}/finding/${f.finding_id}`}
                      style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '8px 0', borderBottom: BORDER2, textDecoration: 'none' }}
                    >
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                          <span style={{ fontSize: 13, fontWeight: 600, color: TEXT }}>{f.algorithm}</span>
                          <span style={{ fontSize: 10, color: MUTED, background: 'rgba(25,40,55,0.06)', padding: '1px 5px', borderRadius: 4 }}>{f.algorithm_family}</span>
                        </div>
                        {f.file_path && (
                          <div style={{ fontSize: 10, color: MUTED2, fontFamily: 'monospace', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', marginTop: 1 }}>
                            {f.file_path}
                          </div>
                        )}
                      </div>
                      <div style={{ textAlign: 'right', flexShrink: 0 }}>
                        <div style={{ fontSize: 14, fontWeight: 700, color: sc.text }}>
                          {f.risk_score.toFixed(0)}
                        </div>
                        <span style={{
                          fontSize: 9, fontWeight: 700,
                          background: sc.bg, color: sc.text, border: `1px solid ${sc.border}`,
                          borderRadius: 4, padding: '1px 5px',
                        }}>
                          {f.severity}
                        </span>
                      </div>
                    </Link>
                  );
                })}
                {selectedScanId && (
                  <Link to={`/inventory/${selectedScanId}`} style={{ fontSize: 12, color: ACCENT, textDecoration: 'none', display: 'flex', alignItems: 'center', gap: 4, marginTop: 4 }}>
                    <ChevronRight size={12} /> View All Findings
                  </Link>
                )}
              </div>
            </div>
          )}

          {/* Footer */}
          <div style={{ fontSize: 11, color: MUTED2, textAlign: 'center', paddingBottom: 12 }}>
            QShield Dashboard · All metrics derived from actual scan data · Readiness score is not an official NIST certification
          </div>

        </div>
      </div>
    </div>
  );
}

// ── Sub-components ────────────────────────────────────────────────────────────

function PageHeader({
  appName, scanId: _scanId, scans, selectedScanId, onScanChange, onRefresh, navigate,
}: {
  appName: string | null;
  scanId?: string;
  scans: ScanOption[];
  selectedScanId?: string;
  onScanChange: (id: string) => void;
  onRefresh: () => void;
  navigate: ReturnType<typeof useNavigate>;
}) {
  return (
    <div style={{
      background: BG_SURF, borderBottom: BORDER, padding: '0 28px',
      display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      height: 56, position: 'sticky', top: 0, zIndex: 10, gap: 12, flexShrink: 0,
    }}>
      <div>
        <div style={{ fontSize: 16, fontWeight: 700, fontFamily: 'var(--font-heading)', color: TEXT }}>Overview</div>
        <div style={{ fontSize: 11, color: MUTED }}>Quantum security posture and migration readiness</div>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexShrink: 0 }}>
        {scans.length > 0 && (
          <select
            value={selectedScanId ?? ''}
            onChange={e => onScanChange(e.target.value)}
            aria-label="Select scan"
            style={{
              fontSize: 12, padding: '4px 8px', borderRadius: 7,
              border: BORDER, background: BG_SURF, color: TEXT,
              cursor: 'pointer', maxWidth: 220,
            }}
          >
            {scans.map(s => (
              <option key={s.scan_id} value={s.scan_id}>
                {s.application_name} — {s.scan_name}
              </option>
            ))}
          </select>
        )}
        {appName && (
          <span style={{ fontSize: 12, color: MUTED, display: 'flex', alignItems: 'center', gap: 4 }}>
            <span style={{ color: MUTED2 }}>·</span> {appName}
          </span>
        )}
        <button onClick={onRefresh} style={{
          display: 'flex', alignItems: 'center', gap: 5,
          padding: '5px 10px', borderRadius: 7, border: BORDER,
          background: 'transparent', fontSize: 12, cursor: 'pointer', color: MUTED,
        }} aria-label="Refresh dashboard">
          <RefreshCw size={12} />
        </button>
        <button onClick={() => navigate('/scan')} style={{
          display: 'flex', alignItems: 'center', gap: 5,
          padding: '6px 14px', borderRadius: 7, border: 'none',
          background: ACCENT, fontSize: 12, cursor: 'pointer',
          color: '#fff', fontWeight: 600,
        }}>
          <Upload size={12} /> Run New Scan
        </button>
      </div>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const cfg =
    status === 'completed' ? { bg: '#f0fdf4', text: '#15803d', border: '#bbf7d0' } :
    status === 'running'   ? { bg: '#eff6ff', text: '#1e40af', border: '#bfdbfe' } :
    status === 'failed'    ? { bg: '#fef2f2', text: '#b91c1c', border: '#fecaca' } :
                             { bg: '#f9fafb', text: '#374151', border: '#e5e7eb' };
  return (
    <span style={{
      fontSize: 9, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em',
      background: cfg.bg, color: cfg.text, border: `1px solid ${cfg.border}`,
      borderRadius: 5, padding: '2px 7px',
    }}>
      {status}
    </span>
  );
}

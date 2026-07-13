/**
 * RiskPage.tsx — QShield Quantum Migration Risk Analysis
 *
 * Enterprise light-theme redesign:
 *   - Persistent left sidebar navigation
 *   - Tab bar (Overview / Factor Breakdown / Priority Findings / App Context)
 *   - Compact horizontal summary strip
 *   - Clean score panel (no neon gauge)
 *   - Compact factor breakdown with progress bars
 *   - Expandable finding rows
 *   - Application context panel
 *
 * ALL values come from /api/risk — nothing is hardcoded.
 */

import { useEffect, useState, useCallback, useRef } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import {
  Shield, AlertTriangle, ArrowLeft, Info,
  ChevronDown, ChevronUp, RefreshCw,
  Home, BookOpen, BarChart2, Map, FlaskConical, FileText,
  AlertCircle, CheckCircle, HelpCircle, ChevronRight,
} from 'lucide-react';
import { getRiskAnalysis } from '../services/riskApi';
import type { ScanRiskResult, FindingRisk, FactorScore } from '../services/riskApi';
import QShieldLogo from '../components/QShieldLogo';

// ── Design tokens (matching InventoryPage / FindingBadges) ────────────────────

const BORDER  = '1px solid rgba(25,40,55,0.09)';
const BORDER2 = '1px solid rgba(25,40,55,0.06)';
const TEXT    = '#192837';
const MUTED   = 'rgba(25,40,55,0.45)';
const MUTED2  = 'rgba(25,40,55,0.30)';
const BG_PAGE = '#f8f8f5';
const BG_SURF = '#ffffff';
const ACCENT  = '#7342E2';

// ── Severity config ───────────────────────────────────────────────────────────

interface SevCfg { bg: string; text: string; border: string; dot: string }
const SEV: Record<string, SevCfg> = {
  Low:      { bg: '#f0fdf4', text: '#15803d', border: '#bbf7d0', dot: '#22c55e' },
  Moderate: { bg: '#fffbeb', text: '#92400e', border: '#fde68a', dot: '#f59e0b' },
  High:     { bg: '#fff7ed', text: '#c2410c', border: '#fed7aa', dot: '#f97316' },
  Critical: { bg: '#fef2f2', text: '#b91c1c', border: '#fecaca', dot: '#ef4444' },
};
const getSev = (s: string): SevCfg => SEV[s] ?? SEV.Low;

// ── Priority config ───────────────────────────────────────────────────────────

const PRI: Record<string, { label: string; color: string }> = {
  immediate: { label: 'Immediate',    color: '#b91c1c' },
  near_term: { label: 'Near Term',    color: '#c2410c' },
  long_term: { label: 'Long Term',    color: '#a16207' },
  low:       { label: 'Low Priority', color: '#15803d' },
};
const getPri = (p: string) => PRI[p] ?? PRI.low;

// ── Factor weights (display only, mirrors backend) ────────────────────────────
const FACTOR_WEIGHTS: Record<string, number> = {
  crypto_vulnerability:   0.30,
  confidentiality:        0.20,
  business_criticality:   0.20,
  external_exposure:      0.15,
  migration_complexity:   0.10,
  compliance_sensitivity: 0.05,
};

// ── Sidebar nav items ─────────────────────────────────────────────────────────

interface NavItem { label: string; icon: React.ReactNode; to: string; key: string }
function buildNav(scanId?: string): NavItem[] {
  return [
    { key: 'overview',   label: 'Overview',        icon: <Home size={15} />,         to: '/app/dashboard' },
    { key: 'inventory',  label: 'Crypto Inventory', icon: <BookOpen size={15} />,     to: scanId ? `/inventory/${scanId}` : '/upload' },
    { key: 'risk',       label: 'Risk Analysis',    icon: <BarChart2 size={15} />,    to: scanId ? `/risk/${scanId}` : '#' },
    { key: 'migration',  label: 'Migration',        icon: <Map size={15} />,          to: scanId ? `/recommendations/${scanId}` : '#' },
    { key: 'pqclab',     label: 'PQC Lab',          icon: <FlaskConical size={15} />, to: '/demo' },
    { key: 'reports',    label: 'Reports',          icon: <FileText size={15} />,     to: '#' },
  ];
}

// ── Sidebar ───────────────────────────────────────────────────────────────────

function Sidebar({ scanId }: { scanId?: string }) {
  const nav = buildNav(scanId);
  return (
    <aside style={{
      width: 220,
      flexShrink: 0,
      background: BG_SURF,
      borderRight: BORDER,
      display: 'flex',
      flexDirection: 'column',
      minHeight: '100vh',
      position: 'sticky',
      top: 0,
      alignSelf: 'flex-start',
    }}>
      {/* Brand */}
      <div style={{ padding: '18px 20px 16px', borderBottom: BORDER, display: 'flex', alignItems: 'center', gap: 10 }}>
        <QShieldLogo size={20} color={TEXT} />
        <span style={{ fontSize: 15, fontWeight: 700, fontFamily: 'var(--font-heading)', color: TEXT, letterSpacing: '-0.01em' }}>
          QShield
        </span>
      </div>

      {/* Nav */}
      <nav style={{ padding: '10px 10px', flex: 1 }}>
        {nav.map(item => {
          const isActive = item.key === 'risk';
          const isDisabled = item.to === '#';
          return (
            <Link
              key={item.key}
              to={item.to}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 10,
                padding: '7px 12px',
                borderRadius: 7,
                marginBottom: 1,
                fontSize: 13,
                fontWeight: isActive ? 600 : 400,
                color: isActive ? ACCENT : isDisabled ? MUTED2 : TEXT,
                background: isActive ? `${ACCENT}10` : 'transparent',
                textDecoration: 'none',
                opacity: isDisabled ? 0.5 : 1,
                cursor: isDisabled ? 'default' : 'pointer',
                pointerEvents: isDisabled ? 'none' : 'auto',
                transition: 'background 0.12s',
              }}
              onMouseEnter={e => { if (!isActive && !isDisabled) (e.currentTarget as HTMLElement).style.background = 'rgba(25,40,55,0.04)'; }}
              onMouseLeave={e => { if (!isActive && !isDisabled) (e.currentTarget as HTMLElement).style.background = 'transparent'; }}
            >
              <span style={{ color: isActive ? ACCENT : MUTED, flexShrink: 0 }}>{item.icon}</span>
              {item.label}
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div style={{ padding: '14px 20px', borderTop: BORDER }}>
        <span style={{ fontSize: 11, color: MUTED2 }}>QShield · Risk Engine v1.0</span>
      </div>
    </aside>
  );
}

// ── Score badge (inline, no gauge) ────────────────────────────────────────────

function ScoreBadge({ score, severity }: { score: number; severity: string }) {
  const cfg = getSev(severity);
  return (
    <div style={{ display: 'inline-flex', alignItems: 'baseline', gap: 8 }}>
      <span style={{
        fontFamily: 'var(--font-heading)',
        fontSize: 48,
        fontWeight: 700,
        lineHeight: 1,
        color: cfg.text,
        letterSpacing: '-0.03em',
      }}>
        {Math.round(score)}
      </span>
      <span style={{ fontSize: 18, color: MUTED, fontWeight: 400 }}>/100</span>
    </div>
  );
}

// ── Severity badge inline ─────────────────────────────────────────────────────

function SevBadge({ severity, size = 'md' }: { severity: string; size?: 'sm' | 'md' }) {
  const cfg = getSev(severity);
  const fs = size === 'sm' ? 10 : 11;
  const px = size === 'sm' ? 6 : 8;
  const py = size === 'sm' ? 2 : 3;
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 5,
      background: cfg.bg, color: cfg.text,
      border: `1px solid ${cfg.border}`,
      borderRadius: 6,
      fontSize: fs, fontWeight: 600,
      padding: `${py}px ${px}px`,
      whiteSpace: 'nowrap',
    }}>
      <span style={{ width: 6, height: 6, borderRadius: '50%', background: cfg.dot, flexShrink: 0 }} />
      {severity}
    </span>
  );
}

// ── Summary strip ─────────────────────────────────────────────────────────────

function SummaryStrip({ data }: { data: ScanRiskResult }) {
  const cfg = getSev(data.overall_severity);
  const items = [
    {
      label: 'Risk Score',
      value: `${Math.round(data.overall_quantum_score)}/100`,
      sub: data.overall_severity,
      color: cfg.text,
    },
    {
      label: 'Quantum Vulnerable',
      value: String(data.vulnerable_count),
      sub: 'need migration',
      color: '#b91c1c',
      icon: <AlertCircle size={13} />,
    },
    {
      label: 'Already Safe',
      value: String(data.safe_count),
      sub: 'quantum-safe',
      color: '#15803d',
      icon: <CheckCircle size={13} />,
    },
    {
      label: 'Classical / Legacy',
      value: String(data.legacy_count),
      sub: 'separate concern',
      color: '#c2410c',
      icon: <AlertTriangle size={13} />,
    },
    {
      label: 'Borderline / Review',
      value: String(data.borderline_count),
      sub: 'needs assessment',
      color: '#a16207',
      icon: <HelpCircle size={13} />,
    },
  ];

  return (
    <div style={{
      background: BG_SURF,
      border: BORDER,
      borderRadius: 10,
      display: 'flex',
      alignItems: 'stretch',
      overflow: 'hidden',
    }}>
      {items.map((item, i) => (
        <div key={item.label} style={{
          flex: 1,
          padding: '12px 18px',
          borderRight: i < items.length - 1 ? BORDER : 'none',
          display: 'flex',
          flexDirection: 'column',
          gap: 2,
          minWidth: 0,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
            {item.icon && <span style={{ color: item.color }}>{item.icon}</span>}
            <span style={{ fontSize: 11, color: MUTED, fontWeight: 500, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              {item.label}
            </span>
          </div>
          <div style={{ fontSize: 22, fontWeight: 700, color: item.color, fontFamily: 'var(--font-heading)', lineHeight: 1.1 }}>
            {item.value}
          </div>
          <div style={{ fontSize: 11, color: MUTED2 }}>{item.sub}</div>
        </div>
      ))}
    </div>
  );
}

// ── Factor bar row ────────────────────────────────────────────────────────────

function FactorRow({ factor, isLast }: { factor: FactorScore; isLast: boolean }) {
  const pct = Math.min(100, (factor.raw_value) * 100);
  const barColor = factor.raw_value >= 0.7 ? '#ef4444'
    : factor.raw_value >= 0.4 ? '#f59e0b'
    : '#22c55e';
  const weight = FACTOR_WEIGHTS[factor.factor] ?? factor.weight;

  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: '200px 1fr 80px 64px',
      alignItems: 'center',
      gap: 16,
      padding: '9px 16px',
      borderBottom: isLast ? 'none' : BORDER2,
      fontSize: 13,
    }}>
      {/* Label */}
      <span style={{ color: TEXT, fontWeight: 500, minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
        {factor.label}
      </span>

      {/* Bar */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <div style={{ flex: 1, height: 5, borderRadius: 3, background: 'rgba(25,40,55,0.08)', overflow: 'hidden' }}>
          <div style={{
            width: `${pct}%`, height: '100%', borderRadius: 3,
            background: barColor,
            transition: 'width 0.5s ease',
          }} />
        </div>
        <span style={{ fontSize: 11, color: MUTED, minWidth: 28, textAlign: 'right' }}>
          {Math.round(pct)}%
        </span>
      </div>

      {/* Contribution */}
      <span style={{ fontSize: 12, color: TEXT, textAlign: 'right', fontVariantNumeric: 'tabular-nums' }}>
        {factor.weighted_contribution.toFixed(1)}
        <span style={{ color: MUTED2, fontSize: 10 }}> pts</span>
      </span>

      {/* Weight */}
      <span style={{ fontSize: 11, color: MUTED2, textAlign: 'right' }}>
        {Math.round(weight * 100)}% wt
      </span>
    </div>
  );
}

// ── Finding row (expandable) ──────────────────────────────────────────────────

function FindingRow({ finding, scanId, isLast }: { finding: FindingRisk; scanId: string; isLast: boolean }) {
  const [open, setOpen] = useState(false);
  const sev = getSev(finding.quantum_migration_severity);
  const pri = getPri(finding.migration_priority);
  const gateReduced = finding.raw_weighted_sum - finding.quantum_migration_score > 5;

  return (
    <>
      {/* Summary row */}
      <div
        onClick={() => setOpen(o => !o)}
        style={{
          display: 'grid',
          gridTemplateColumns: '48px 1fr 1fr 110px 90px 28px',
          alignItems: 'center',
          gap: 12,
          padding: '10px 16px',
          borderBottom: (!open && !isLast) ? BORDER2 : open ? 'none' : 'none',
          cursor: 'pointer',
          fontSize: 13,
          transition: 'background 0.1s',
        }}
        onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = 'rgba(25,40,55,0.02)'; }}
        onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = 'transparent'; }}
      >
        {/* Score */}
        <div style={{
          width: 40, height: 40,
          borderRadius: 8,
          background: sev.bg,
          border: `1px solid ${sev.border}`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          flexShrink: 0,
        }}>
          <span style={{ fontSize: 13, fontWeight: 700, color: sev.text }}>
            {Math.round(finding.quantum_migration_score)}
          </span>
        </div>

        {/* Algorithm + file */}
        <div style={{ minWidth: 0 }}>
          <div style={{ fontWeight: 600, color: TEXT, display: 'flex', alignItems: 'center', gap: 6 }}>
            {finding.algorithm}
            <span style={{ fontWeight: 400, fontSize: 11, color: MUTED, background: 'rgba(25,40,55,0.06)', padding: '1px 6px', borderRadius: 4 }}>
              {finding.algorithm_family}
            </span>
          </div>
          {finding.file_path && (
            <div style={{ fontSize: 11, color: MUTED, fontFamily: 'monospace', marginTop: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {finding.file_path}
            </div>
          )}
        </div>

        {/* Explanation preview */}
        <div style={{ fontSize: 12, color: MUTED, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', minWidth: 0 }}>
          {finding.explanation.split('.')[0]}
        </div>

        {/* Priority */}
        <span style={{ fontSize: 11, fontWeight: 600, color: pri.color, whiteSpace: 'nowrap' }}>
          {pri.label}
        </span>

        {/* Severity */}
        <SevBadge severity={finding.quantum_migration_severity} size="sm" />

        {/* Chevron */}
        <span style={{ color: MUTED2, flexShrink: 0 }}>
          {open ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        </span>
      </div>

      {/* Expanded detail */}
      {open && (
        <div style={{
          padding: '0 16px 14px 78px',
          borderBottom: isLast ? 'none' : BORDER2,
          background: 'rgba(25,40,55,0.012)',
        }}>
          {/* Full explanation */}
          <div style={{
            background: BG_SURF,
            border: BORDER,
            borderRadius: 8,
            padding: '10px 14px',
            fontSize: 12,
            color: TEXT,
            lineHeight: 1.6,
            marginBottom: 10,
          }}>
            {finding.explanation}
          </div>

          {/* Gate transparency */}
          {gateReduced && (
            <div style={{
              display: 'flex', gap: 8, alignItems: 'flex-start',
              background: '#f5f3ff', border: '1px solid #e9d5ff',
              borderRadius: 7, padding: '8px 12px',
              fontSize: 12, color: '#6b21a8',
              marginBottom: 10,
            }}>
              <Info size={13} style={{ flexShrink: 0, marginTop: 1 }} />
              <span>
                <strong>Gate applied:</strong> Raw weighted sum {finding.raw_weighted_sum.toFixed(1)}/100 →
                reduced to {finding.quantum_migration_score.toFixed(1)}/100 by the
                crypto-vulnerability gate ({(finding.crypto_vulnerability_gate * 100).toFixed(0)}%).
                This algorithm has low quantum relevance; business context factors are suppressed.
              </span>
            </div>
          )}

          {/* Classical risk */}
          {finding.classical_legacy_risk && finding.classical_legacy_rationale && (
            <div style={{
              display: 'flex', gap: 8, alignItems: 'flex-start',
              background: '#fff7ed', border: '1px solid #fed7aa',
              borderRadius: 7, padding: '8px 12px',
              fontSize: 12, color: '#92400e',
              marginBottom: 10,
            }}>
              <AlertTriangle size={13} style={{ flexShrink: 0, marginTop: 1 }} />
              <div>
                <strong>Classical / Legacy Risk ({finding.classical_legacy_risk}) — separate concern</strong>
                <div style={{ marginTop: 2, opacity: 0.8 }}>{finding.classical_legacy_rationale}</div>
              </div>
            </div>
          )}

          {/* Factor mini-table */}
          <div style={{ marginBottom: 10 }}>
            <div style={{ fontSize: 10, fontWeight: 600, color: MUTED2, textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 6 }}>
              Factor Breakdown
            </div>
            <div style={{ background: BG_SURF, border: BORDER, borderRadius: 8, overflow: 'hidden' }}>
              {finding.factors.map((f, i) => (
                <div key={f.factor} style={{
                  display: 'flex', alignItems: 'center', gap: 12,
                  padding: '6px 12px',
                  borderBottom: i < finding.factors.length - 1 ? BORDER2 : 'none',
                  fontSize: 12,
                }}>
                  <span style={{ flex: '0 0 170px', color: TEXT, fontWeight: 500 }}>{f.label}</span>
                  <div style={{ flex: 1, height: 4, borderRadius: 2, background: 'rgba(25,40,55,0.08)', overflow: 'hidden' }}>
                    <div style={{
                      width: `${Math.min(100, f.raw_value * 100)}%`,
                      height: '100%',
                      borderRadius: 2,
                      background: f.raw_value >= 0.7 ? '#ef4444' : f.raw_value >= 0.4 ? '#f59e0b' : '#22c55e',
                    }} />
                  </div>
                  <span style={{ flex: '0 0 56px', textAlign: 'right', color: MUTED, fontVariantNumeric: 'tabular-nums' }}>
                    {f.weighted_contribution.toFixed(1)} pts
                  </span>
                  <span style={{ flex: '0 0 40px', textAlign: 'right', color: MUTED2, fontSize: 11 }}>
                    {Math.round(f.weight * 100)}%
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* NIST recommendation */}
          {finding.nist_recommendation && (
            <div style={{
              display: 'flex', gap: 8, alignItems: 'flex-start',
              background: '#eff6ff', border: '1px solid #bfdbfe',
              borderRadius: 7, padding: '8px 12px',
              fontSize: 12, color: '#1e40af',
              marginBottom: 10,
            }}>
              <Shield size={13} style={{ flexShrink: 0, marginTop: 1 }} />
              <span><strong>NIST Recommendation:</strong> {finding.nist_recommendation}</span>
            </div>
          )}

          <Link
            to={`/inventory/${scanId}/finding/${finding.finding_id}`}
            style={{ display: 'inline-flex', alignItems: 'center', gap: 4, fontSize: 12, color: ACCENT, textDecoration: 'none' }}
            onMouseEnter={e => { (e.currentTarget as HTMLElement).style.textDecoration = 'underline'; }}
            onMouseLeave={e => { (e.currentTarget as HTMLElement).style.textDecoration = 'none'; }}
          >
            View full finding detail <ChevronRight size={12} />
          </Link>
        </div>
      )}
    </>
  );
}

// ── Section card ──────────────────────────────────────────────────────────────

function Card({ children, style }: { children: React.ReactNode; style?: React.CSSProperties }) {
  return (
    <div style={{
      background: BG_SURF,
      border: BORDER,
      borderRadius: 10,
      overflow: 'hidden',
      ...style,
    }}>
      {children}
    </div>
  );
}

function CardHeader({ title, sub }: { title: string; sub?: string }) {
  return (
    <div style={{
      padding: '12px 16px 11px',
      borderBottom: BORDER,
      display: 'flex', alignItems: 'baseline', gap: 10,
    }}>
      <span style={{ fontSize: 13, fontWeight: 600, color: TEXT }}>{title}</span>
      {sub && <span style={{ fontSize: 12, color: MUTED }}>{sub}</span>}
    </div>
  );
}

// ── Tab bar ───────────────────────────────────────────────────────────────────

const TABS = [
  { id: 'overview',   label: 'Overview' },
  { id: 'factors',    label: 'Factor Breakdown' },
  { id: 'findings',   label: 'Priority Findings' },
  { id: 'context',    label: 'Application Context' },
];

// ── Context row helper ────────────────────────────────────────────────────────

function CtxRow({ label, value, highlight }: { label: string; value: string; highlight?: boolean }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'center',
      padding: '8px 16px',
      borderBottom: BORDER2,
      fontSize: 13,
      gap: 16,
    }}>
      <span style={{ flex: '0 0 190px', color: MUTED, fontWeight: 500 }}>{label}</span>
      <span style={{ color: highlight ? TEXT : TEXT, fontWeight: highlight ? 600 : 400 }}>
        {value}
      </span>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function RiskPage() {
  const { scanId } = useParams<{ scanId: string }>();
  const navigate = useNavigate();

  const [data, setData] = useState<ScanRiskResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState('overview');
  const [showMethodology, setShowMethodology] = useState(false);

  // Section refs for tab scroll
  const overviewRef  = useRef<HTMLDivElement>(null);
  const factorsRef   = useRef<HTMLDivElement>(null);
  const findingsRef  = useRef<HTMLDivElement>(null);
  const contextRef   = useRef<HTMLDivElement>(null);

  const refs: Record<string, React.RefObject<HTMLDivElement | null>> = {
    overview:  overviewRef,
    factors:   factorsRef,
    findings:  findingsRef,
    context:   contextRef,
  };

  const load = useCallback(async () => {
    if (!scanId) return;
    setLoading(true);
    setError(null);
    try {
      const result = await getRiskAnalysis(scanId);
      setData(result);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to load risk analysis');
    } finally {
      setLoading(false);
    }
  }, [scanId]);

  useEffect(() => { load(); }, [load]);

  function handleTabClick(tabId: string) {
    setActiveTab(tabId);
    refs[tabId]?.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  // ── Loading ───────────────────────────────────────────────────────────────
  if (loading) {
    return (
      <div style={{ display: 'flex', minHeight: '100dvh', background: BG_PAGE }}>
        <Sidebar scanId={scanId} />
        <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column', gap: 14 }}>
          <div style={{
            width: 36, height: 36, borderRadius: '50%',
            border: `2px solid ${ACCENT}30`,
            borderTopColor: ACCENT,
            animation: 'spin 0.8s linear infinite',
          }} />
          <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
          <span style={{ fontSize: 13, color: MUTED }}>Running risk analysis…</span>
        </div>
      </div>
    );
  }

  // ── Error ─────────────────────────────────────────────────────────────────
  if (error) {
    return (
      <div style={{ display: 'flex', minHeight: '100dvh', background: BG_PAGE }}>
        <Sidebar scanId={scanId} />
        <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 32 }}>
          <div style={{
            background: BG_SURF, border: '1px solid #fecaca', borderRadius: 12,
            padding: 32, maxWidth: 420, width: '100%', textAlign: 'center',
          }}>
            <AlertTriangle size={32} style={{ color: '#ef4444', marginBottom: 12 }} />
            <div style={{ fontSize: 15, fontWeight: 600, color: TEXT, marginBottom: 8 }}>Risk Analysis Failed</div>
            <div style={{ fontSize: 13, color: MUTED, marginBottom: 20 }}>{error}</div>
            <div style={{ display: 'flex', gap: 10, justifyContent: 'center' }}>
              <button onClick={load} style={{
                display: 'flex', alignItems: 'center', gap: 6,
                padding: '7px 16px', borderRadius: 7,
                border: BORDER, background: BG_SURF,
                fontSize: 13, cursor: 'pointer', color: TEXT,
              }}>
                <RefreshCw size={13} /> Retry
              </button>
              <button onClick={() => navigate(`/inventory/${scanId}`)} style={{
                display: 'flex', alignItems: 'center', gap: 6,
                padding: '7px 16px', borderRadius: 7,
                border: 'none', background: ACCENT,
                fontSize: 13, cursor: 'pointer', color: 'white', fontWeight: 600,
              }}>
                <ArrowLeft size={13} /> Back to Inventory
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (!data) return null;

  const sevCfg = getSev(data.overall_severity);
  const factorEntries = Object.entries(data.factor_summary).sort((a, b) => b[1] - a[1]);
  // Build factor label map from first top finding (or fall back to key)
  const labelMap: Record<string, string> = {};
  data.top_findings[0]?.factors.forEach(f => { labelMap[f.factor] = f.label; });

  return (
    <div style={{ display: 'flex', minHeight: '100dvh', background: BG_PAGE, fontFamily: 'var(--font-body)', color: TEXT }}>
      <Sidebar scanId={scanId} />

      {/* ── Main content ── */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>

        {/* ── Top header ── */}
        <div style={{
          background: BG_SURF,
          borderBottom: BORDER,
          padding: '0 28px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          height: 56,
          position: 'sticky',
          top: 0,
          zIndex: 10,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ fontSize: 16, fontWeight: 700, fontFamily: 'var(--font-heading)', color: TEXT }}>
              Risk Analysis
            </span>
            {scanId && (
              <>
                <span style={{ color: MUTED2, fontSize: 16 }}>/</span>
                <span style={{ fontSize: 12, color: MUTED, fontFamily: 'monospace', maxWidth: 240, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {scanId}
                </span>
              </>
            )}
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <button
              onClick={load}
              title="Recalculate"
              style={{
                display: 'flex', alignItems: 'center', gap: 5,
                padding: '5px 10px', borderRadius: 7,
                border: BORDER, background: 'transparent',
                fontSize: 12, cursor: 'pointer', color: MUTED,
              }}
            >
              <RefreshCw size={12} /> Recalculate
            </button>
            <button
              onClick={() => navigate(`/inventory/${scanId}`)}
              style={{
                display: 'flex', alignItems: 'center', gap: 5,
                padding: '5px 12px', borderRadius: 7,
                border: BORDER, background: 'transparent',
                fontSize: 13, cursor: 'pointer', color: TEXT, fontWeight: 500,
              }}
            >
              <ArrowLeft size={13} /> Inventory
            </button>
            {scanId && (
              <button
                onClick={() => navigate(`/recommendations/${scanId}`)}
                style={{
                  display: 'flex', alignItems: 'center', gap: 5,
                  padding: '5px 14px', borderRadius: 7,
                  border: 'none', background: ACCENT,
                  fontSize: 13, cursor: 'pointer', color: 'white', fontWeight: 600,
                }}
              >
                <Map size={13} /> Migration Plan
              </button>
            )}
          </div>
        </div>

        {/* ── Tab bar ── */}
        <div style={{
          background: BG_SURF,
          borderBottom: BORDER,
          padding: '0 28px',
          display: 'flex',
          gap: 0,
          position: 'sticky',
          top: 56,
          zIndex: 9,
        }}>
          {TABS.map(tab => (
            <button
              key={tab.id}
              onClick={() => handleTabClick(tab.id)}
              style={{
                padding: '10px 18px',
                fontSize: 13,
                fontWeight: activeTab === tab.id ? 600 : 400,
                color: activeTab === tab.id ? ACCENT : MUTED,
                background: 'none',
                border: 'none',
                borderBottom: activeTab === tab.id ? `2px solid ${ACCENT}` : '2px solid transparent',
                cursor: 'pointer',
                marginBottom: -1,
                transition: 'color 0.12s',
              }}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* ── Page body ── */}
        <div style={{ padding: '24px 28px', display: 'flex', flexDirection: 'column', gap: 20 }}>

          {/* Context defaulted warning */}
          {data.context_defaulted && (
            <div style={{
              display: 'flex', gap: 10, alignItems: 'flex-start',
              background: '#fffbeb', border: '1px solid #fde68a',
              borderRadius: 8, padding: '10px 14px',
              fontSize: 12, color: '#92400e',
            }}>
              <HelpCircle size={14} style={{ flexShrink: 0, marginTop: 1 }} />
              <span>
                Business context was unavailable for this application.
                Neutral defaults were applied (medium criticality, internal, medium-term).
                Scores may not reflect actual migration urgency.
              </span>
            </div>
          )}

          {/* Summary strip */}
          <SummaryStrip data={data} />

          {/* ── Overview section ── */}
          <div ref={overviewRef} style={{ scrollMarginTop: 120 }}>
            <Card>
              <CardHeader title="Quantum Migration Overview" sub={`${data.methodology} v${data.methodology_version}`} />
              <div style={{ padding: '20px 20px', display: 'flex', gap: 32, flexWrap: 'wrap', alignItems: 'flex-start' }}>

                {/* Score block */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: 10, flexShrink: 0 }}>
                  <ScoreBadge score={data.overall_quantum_score} severity={data.overall_severity} />
                  <SevBadge severity={data.overall_severity} />
                </div>

                {/* Divider */}
                <div style={{ width: 1, background: 'rgba(25,40,55,0.08)', alignSelf: 'stretch', flexShrink: 0 }} />

                {/* Summary text + methodology */}
                <div style={{ flex: 1, minWidth: 240, display: 'flex', flexDirection: 'column', gap: 14 }}>
                  <div style={{ fontSize: 14, color: TEXT, lineHeight: 1.6 }}>
                    {data.summary_text}
                  </div>

                  {/* Methodology toggle */}
                  <div>
                    <button
                      onClick={() => setShowMethodology(m => !m)}
                      style={{
                        display: 'inline-flex', alignItems: 'center', gap: 5,
                        fontSize: 12, color: MUTED, background: 'none',
                        border: 'none', cursor: 'pointer', padding: 0,
                        textDecoration: 'underline', textDecorationStyle: 'dotted',
                        textUnderlineOffset: 3,
                      }}
                    >
                      <Info size={12} />
                      {showMethodology ? 'Hide methodology' : 'How is this scored?'}
                    </button>

                    {showMethodology && (
                      <div style={{
                        marginTop: 10,
                        background: '#f5f3ff',
                        border: '1px solid #ede9fe',
                        borderRadius: 8,
                        padding: '12px 14px',
                        fontSize: 12,
                        color: '#4c1d95',
                        lineHeight: 1.65,
                      }}>
                        <div style={{ fontWeight: 600, marginBottom: 4, display: 'flex', alignItems: 'center', gap: 6 }}>
                          <Shield size={13} />
                          {data.methodology}
                        </div>
                        <p style={{ margin: '0 0 8px' }}>{data.methodology_description}</p>
                        <p style={{ margin: 0, opacity: 0.7, fontStyle: 'italic' }}>{data.disclaimer}</p>
                      </div>
                    )}
                  </div>

                  {/* Disclaimer always visible */}
                  {!showMethodology && (
                    <div style={{
                      fontSize: 11, color: MUTED2,
                      borderTop: BORDER2, paddingTop: 10, lineHeight: 1.5,
                    }}>
                      <Info size={11} style={{ display: 'inline', verticalAlign: 'middle', marginRight: 4 }} />
                      {data.disclaimer}
                    </div>
                  )}
                </div>
              </div>
            </Card>
          </div>

          {/* ── Factor Breakdown section ── */}
          <div ref={factorsRef} style={{ scrollMarginTop: 120 }}>
            <Card>
              <CardHeader
                title="Factor Breakdown"
                sub="Average weighted contribution before crypto-vulnerability gate"
              />

              {/* Column headers */}
              <div style={{
                display: 'grid',
                gridTemplateColumns: '200px 1fr 80px 64px',
                gap: 16,
                padding: '7px 16px',
                borderBottom: BORDER,
                fontSize: 10,
                fontWeight: 600,
                color: MUTED2,
                textTransform: 'uppercase',
                letterSpacing: '0.06em',
              }}>
                <span>Factor</span>
                <span>Raw Score</span>
                <span style={{ textAlign: 'right' }}>Contribution</span>
                <span style={{ textAlign: 'right' }}>Weight</span>
              </div>

              {/* Factor rows from factor_summary — use first finding's factors for labels+raw */}
              {data.top_findings.length > 0
                ? data.top_findings[0].factors.map((f, i) => (
                    <FactorRow
                      key={f.factor}
                      factor={{
                        ...f,
                        weighted_contribution: factorEntries.find(([k]) => k === f.factor)?.[1] ?? f.weighted_contribution,
                      }}
                      isLast={i === data.top_findings[0].factors.length - 1}
                    />
                  ))
                : factorEntries.map(([factor, contrib], i) => (
                    <FactorRow
                      key={factor}
                      factor={{
                        factor,
                        label: labelMap[factor] ?? factor.replace(/_/g, ' '),
                        weight: FACTOR_WEIGHTS[factor] ?? 0,
                        raw_value: contrib / ((FACTOR_WEIGHTS[factor] ?? 0.1) * 100),
                        weighted_contribution: contrib,
                        rationale: '',
                      }}
                      isLast={i === factorEntries.length - 1}
                    />
                  ))
              }

              {/* Totals row */}
              <div style={{
                display: 'flex', justifyContent: 'flex-end',
                padding: '8px 16px',
                borderTop: BORDER,
                fontSize: 12,
                color: MUTED,
                gap: 8,
              }}>
                <span>Overall score after gate:</span>
                <span style={{ fontWeight: 700, color: sevCfg.text, fontVariantNumeric: 'tabular-nums' }}>
                  {data.overall_quantum_score.toFixed(1)}/100
                </span>
              </div>
            </Card>
          </div>

          {/* ── Priority Findings section ── */}
          <div ref={findingsRef} style={{ scrollMarginTop: 120 }}>
            <Card>
              <div style={{
                padding: '12px 16px 11px',
                borderBottom: BORDER,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
              }}>
                <div style={{ display: 'flex', alignItems: 'baseline', gap: 10 }}>
                  <span style={{ fontSize: 13, fontWeight: 600, color: TEXT }}>Priority Findings</span>
                  <span style={{ fontSize: 12, color: MUTED }}>
                    {data.top_findings.length} highest-priority (click to expand)
                  </span>
                </div>
                <Link
                  to={`/inventory/${scanId}`}
                  style={{ fontSize: 12, color: ACCENT, textDecoration: 'none', display: 'flex', alignItems: 'center', gap: 3 }}
                >
                  View all <ChevronRight size={12} />
                </Link>
              </div>

              {/* Column headers */}
              {data.top_findings.length > 0 && (
                <div style={{
                  display: 'grid',
                  gridTemplateColumns: '48px 1fr 1fr 110px 90px 28px',
                  gap: 12,
                  padding: '6px 16px',
                  borderBottom: BORDER,
                  fontSize: 10,
                  fontWeight: 600,
                  color: MUTED2,
                  textTransform: 'uppercase',
                  letterSpacing: '0.06em',
                }}>
                  <span>Score</span>
                  <span>Algorithm</span>
                  <span>Explanation</span>
                  <span>Priority</span>
                  <span>Severity</span>
                  <span />
                </div>
              )}

              {data.top_findings.length === 0 ? (
                <div style={{ padding: '40px 20px', textAlign: 'center' }}>
                  <CheckCircle size={32} style={{ color: '#22c55e', margin: '0 auto 12px', display: 'block' }} />
                  <div style={{ fontSize: 14, fontWeight: 600, color: TEXT, marginBottom: 6 }}>No Quantum Migration Required</div>
                  <div style={{ fontSize: 13, color: MUTED }}>
                    {data.summary_text || 'No quantum-vulnerable cryptography was detected.'}
                  </div>
                </div>
              ) : (
                data.top_findings.map((f, i) => (
                  <FindingRow
                    key={f.finding_id}
                    finding={f}
                    scanId={scanId!}
                    isLast={i === data.top_findings.length - 1}
                  />
                ))
              )}
            </Card>
          </div>

          {/* ── Application Context section ── */}
          <div ref={contextRef} style={{ scrollMarginTop: 120 }}>
            <Card>
              <CardHeader title="Application Context Used for Scoring" />
              <div style={{ borderBottom: BORDER2 }}>
                <CtxRow label="Business Criticality"    value={data.business_criticality}                             highlight={['high','critical'].includes(data.business_criticality)} />
                <CtxRow label="Environment"             value={data.environment} />
                <CtxRow label="Internet Exposed"        value={data.internet_exposed ? 'Yes' : 'No'}                  highlight={data.internet_exposed} />
                <CtxRow label="Confidentiality"         value={data.confidentiality_requirement.replace(/_/g, ' ')} />
                <CtxRow label="Data Sensitivity"        value={data.data_sensitivity}                                  highlight={['restricted','top_secret'].includes(data.data_sensitivity)} />
                <CtxRow label="Data Lifetime (years)"   value={String(data.data_lifetime_years)}                      highlight={data.data_lifetime_years >= 10} />
                <div style={{ padding: '8px 16px', fontSize: 12, color: MUTED2, display: 'flex', alignItems: 'center', gap: 6 }}>
                  <Info size={12} />
                  Context source: {data.context_defaulted ? 'default fallback — application context unavailable' : 'application record'}
                </div>
              </div>
            </Card>
          </div>

          {/* Page footer */}
          <div style={{ fontSize: 11, color: MUTED2, textAlign: 'center', paddingBottom: 16, lineHeight: 1.5 }}>
            {data.disclaimer}
          </div>
        </div>
      </div>
    </div>
  );
}

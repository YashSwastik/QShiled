/**
 * RoadmapPage.tsx — QShield Migration Roadmap
 *
 * Information hierarchy:
 *   1. Three-Wave Timeline  (NOW → NEXT → LATER) — horizontal, backend data
 *   2. Stage Lifecycle Bar  (DISCOVERED → … → MIGRATED) — real persisted counts
 *   3. Detailed Wave Groups — existing expandable item cards
 *
 * Route: /roadmap/:scanId
 * Design: Light enterprise SaaS — matches RiskPage and RecommendationsPage.
 * All content from /api/roadmap — nothing hardcoded.
 */
import { useEffect, useState, useCallback } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import {
  AlertTriangle, RefreshCw, CheckCircle, Info, ChevronDown, ChevronUp,
  Home, BookOpen, BarChart2, Map, FlaskConical, FileText, Shield,
  ArrowRight, Clock, ChevronRight,
} from 'lucide-react';
import QShieldLogo from '../components/QShieldLogo';
import {
  getRoadmap, updateRoadmapItemStage, MIGRATION_STAGES,
} from '../services/roadmapApi';
import type { ScanRoadmapResult, RoadmapItem, WaveSummary } from '../services/roadmapApi';

// ── Design tokens ─────────────────────────────────────────────────────────────

const BORDER  = '1px solid rgba(25,40,55,0.09)';
const BORDER2 = '1px solid rgba(25,40,55,0.06)';
const TEXT    = '#192837';
const MUTED   = 'rgba(25,40,55,0.45)';
const MUTED2  = 'rgba(25,40,55,0.30)';
const BG_PAGE = '#f8f8f5';
const BG_SURF = '#ffffff';
const ACCENT  = '#7342E2';

// ── Wave config ───────────────────────────────────────────────────────────────

const WAVE_CFG = {
  1: {
    border: '#ef4444', bg: '#fef2f2', badge: '#fecaca', text: '#b91c1c',
    label: 'Critical', timeLabel: 'NOW', timeDesc: 'Immediate quantum migration priorities',
    connectorColor: '#ef4444',
  },
  2: {
    border: '#f97316', bg: '#fff7ed', badge: '#fed7aa', text: '#c2410c',
    label: 'High', timeLabel: 'NEXT', timeDesc: 'Important planned migration work',
    connectorColor: '#f97316',
  },
  3: {
    border: '#a3e635', bg: '#f7fee7', badge: '#d9f99d', text: '#3f6212',
    label: 'Planned', timeLabel: 'LATER', timeDesc: 'Lower-priority modernization',
    connectorColor: '#a3e635',
  },
} as Record<number, {
  border: string; bg: string; badge: string; text: string;
  label: string; timeLabel: string; timeDesc: string; connectorColor: string;
}>;
const wc = (w: number) => WAVE_CFG[w] ?? WAVE_CFG[3];

// ── Stage config ──────────────────────────────────────────────────────────────

const STAGE_CFG: Record<string, { bg: string; text: string; border: string }> = {
  DISCOVERED:  { bg: '#f9fafb', text: '#374151',  border: '#e5e7eb' },
  ASSESSED:    { bg: '#eff6ff', text: '#1e40af',  border: '#bfdbfe' },
  PLANNED:     { bg: '#f5f3ff', text: '#5b21b6',  border: '#ddd6fe' },
  PILOT:       { bg: '#fffbeb', text: '#92400e',  border: '#fde68a' },
  TRANSITION:  { bg: '#fff7ed', text: '#c2410c',  border: '#fed7aa' },
  VALIDATION:  { bg: '#fef2f2', text: '#b91c1c',  border: '#fecaca' },
  MIGRATED:    { bg: '#f0fdf4', text: '#15803d',  border: '#bbf7d0' },
};
const sc = (s: string) => STAGE_CFG[s] ?? STAGE_CFG.DISCOVERED;

const EFFORT_CFG: Record<string, { bg: string; text: string; border: string }> = {
  low:      { bg: '#f0fdf4', text: '#15803d', border: '#bbf7d0' },
  medium:   { bg: '#fffbeb', text: '#92400e', border: '#fde68a' },
  high:     { bg: '#fff7ed', text: '#c2410c', border: '#fed7aa' },
  very_high:{ bg: '#fef2f2', text: '#b91c1c', border: '#fecaca' },
  unknown:  { bg: '#f9fafb', text: '#374151', border: '#e5e7eb' },
};
const ec = (e: string) => EFFORT_CFG[e] ?? EFFORT_CFG.unknown;

// ── Sidebar ───────────────────────────────────────────────────────────────────

function Sidebar({ scanId }: { scanId?: string }) {
  const navItems = [
    { key: 'overview',  label: 'Dashboard',        Icon: Home,         to: '/dashboard' },
    { key: 'inventory', label: 'Crypto Inventory',  Icon: BookOpen,     to: scanId ? `/inventory/${scanId}` : '/upload' },
    { key: 'risk',      label: 'Risk Analysis',     Icon: BarChart2,    to: scanId ? `/risk/${scanId}` : '#' },
    { key: 'migration', label: 'Migration',         Icon: Map,          to: scanId ? `/recommendations/${scanId}` : '#' },
    { key: 'roadmap',   label: 'Roadmap',           Icon: Clock,        to: scanId ? `/roadmap/${scanId}` : '#', active: true },
    { key: 'pqclab',    label: 'PQC Lab',           Icon: FlaskConical, to: '/demo' },
    { key: 'reports',   label: 'Reports',           Icon: FileText,     to: '#' },
  ];
  return (
    <aside style={{
      width: 220, flexShrink: 0, background: BG_SURF, borderRight: BORDER,
      display: 'flex', flexDirection: 'column', minHeight: '100vh',
      position: 'sticky', top: 0, alignSelf: 'flex-start',
    }}>
      <div style={{ padding: '18px 20px 16px', borderBottom: BORDER, display: 'flex', alignItems: 'center', gap: 10 }}>
        <QShieldLogo size={20} color={TEXT} />
        <span style={{ fontSize: 15, fontWeight: 700, fontFamily: 'var(--font-heading)', color: TEXT, letterSpacing: '-0.01em' }}>
          QShield
        </span>
      </div>
      <nav style={{ padding: '10px 10px', flex: 1 }}>
        {navItems.map(({ key, label, Icon, to, active }) => {
          const disabled = to === '#';
          return (
            <Link key={key} to={to} style={{
              display: 'flex', alignItems: 'center', gap: 10,
              padding: '7px 12px', borderRadius: 7, marginBottom: 1,
              fontSize: 13, fontWeight: active ? 600 : 400,
              color: active ? ACCENT : disabled ? MUTED2 : TEXT,
              background: active ? `${ACCENT}10` : 'transparent',
              textDecoration: 'none', opacity: disabled ? 0.5 : 1,
              cursor: disabled ? 'default' : 'pointer',
              pointerEvents: disabled ? 'none' : 'auto',
            }}
              onMouseEnter={e => { if (!active && !disabled) (e.currentTarget as HTMLAnchorElement).style.background = 'rgba(25,40,55,0.04)'; }}
              onMouseLeave={e => { if (!active && !disabled) (e.currentTarget as HTMLAnchorElement).style.background = 'transparent'; }}
            >
              <span style={{ color: active ? ACCENT : MUTED, flexShrink: 0 }}><Icon size={15} /></span>
              {label}
            </Link>
          );
        })}
      </nav>
      <div style={{ padding: '14px 20px', borderTop: BORDER }}>
        <span style={{ fontSize: 11, color: MUTED2 }}>QShield · Roadmap Engine</span>
      </div>
    </aside>
  );
}

// ── Wave Timeline (NOW → NEXT → LATER) ───────────────────────────────────────
// Horizontal on desktop, stacked on narrow screens.
// All counts and descriptions come from backend wave_summaries.

function WaveTimeline({ summaries }: { summaries: WaveSummary[] }) {
  return (
    <div style={{
      background: BG_SURF, border: BORDER, borderRadius: 12,
      padding: '20px 24px',
    }}>
      {/* Section title */}
      <div style={{ fontSize: 11, fontWeight: 600, color: MUTED2, textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: 16 }}>
        Migration Timeline
      </div>

      {/* Timeline row */}
      <div style={{
        display: 'flex',
        alignItems: 'stretch',
        gap: 0,
        flexWrap: 'wrap',
      }}>
        {summaries.map((ws, idx) => {
          const cfg = wc(ws.wave);
          const isLast = idx === summaries.length - 1;
          return (
            <div key={ws.wave} style={{ display: 'flex', alignItems: 'center', flex: '1 1 0', minWidth: 160 }}>
              {/* Wave card */}
              <div style={{
                flex: 1,
                background: ws.item_count > 0 ? cfg.bg : '#fafafa',
                border: `1.5px solid ${ws.item_count > 0 ? cfg.border : '#e5e7eb'}`,
                borderRadius: 10,
                padding: '16px 18px',
                position: 'relative',
                opacity: ws.item_count === 0 ? 0.65 : 1,
              }}>
                {/* Top row: WAVE N label + time label */}
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
                  <span style={{
                    fontSize: 10, fontWeight: 700,
                    color: cfg.text,
                    background: BG_SURF, border: `1px solid ${cfg.badge}`,
                    borderRadius: 4, padding: '2px 8px',
                    textTransform: 'uppercase', letterSpacing: '0.07em',
                  }}>
                    Wave {ws.wave}
                  </span>
                  <span style={{
                    fontSize: 11, fontWeight: 700, color: cfg.text,
                    textTransform: 'uppercase', letterSpacing: '0.12em',
                  }}>
                    {cfg.timeLabel}
                  </span>
                </div>

                {/* Item count — large */}
                <div style={{
                  fontSize: 36, fontWeight: 800, color: cfg.text,
                  fontFamily: 'var(--font-heading)', lineHeight: 1, marginBottom: 6,
                }}>
                  {ws.item_count}
                  <span style={{ fontSize: 13, fontWeight: 400, color: cfg.text, opacity: 0.6, marginLeft: 4 }}>
                    {ws.item_count === 1 ? 'item' : 'items'}
                  </span>
                </div>

                {/* Priority label */}
                <div style={{
                  display: 'inline-flex', alignItems: 'center',
                  fontSize: 11, fontWeight: 600, color: cfg.text,
                  marginBottom: 8,
                }}>
                  {cfg.label}
                </div>

                {/* Description */}
                <div style={{ fontSize: 11, color: MUTED, lineHeight: 1.5 }}>
                  {cfg.timeDesc}
                </div>
              </div>

              {/* Arrow connector between waves */}
              {!isLast && (
                <div style={{
                  display: 'flex', flexDirection: 'column', alignItems: 'center',
                  padding: '0 10px', flexShrink: 0,
                }}>
                  <div style={{ height: 1, width: 20, background: '#e5e7eb', marginBottom: 4 }} />
                  <ArrowRight size={16} style={{ color: cfg.connectorColor, opacity: 0.7 }} />
                  <div style={{ height: 1, width: 20, background: '#e5e7eb', marginTop: 4 }} />
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── Lifecycle Bar (DISCOVERED → … → MIGRATED) ─────────────────────────────────
// Shows the 7-stage migration lifecycle with counts from actual persisted items.

function LifecycleBar({ items }: { items: RoadmapItem[] }) {
  // Count items by stage
  const stageCounts: Record<string, number> = {};
  for (const stage of MIGRATION_STAGES) stageCounts[stage] = 0;
  for (const item of items) {
    const s = item.status || 'DISCOVERED';
    if (s in stageCounts) stageCounts[s]++;
  }

  const total = items.length;

  return (
    <div style={{ background: BG_SURF, border: BORDER, borderRadius: 12, padding: '16px 24px' }}>
      <div style={{ fontSize: 11, fontWeight: 600, color: MUTED2, textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: 14 }}>
        Migration Lifecycle — {total} item{total !== 1 ? 's' : ''}
      </div>

      {/* Stage nodes with connectors */}
      <div style={{
        display: 'flex', alignItems: 'center',
        overflowX: 'auto', paddingBottom: 4,
        gap: 0,
      }}>
        {MIGRATION_STAGES.map((stage, idx) => {
          const count = stageCounts[stage];
          const cfg = sc(stage);
          const isLast = idx === MIGRATION_STAGES.length - 1;
          const hasItems = count > 0;

          return (
            <div key={stage} style={{ display: 'flex', alignItems: 'center', flexShrink: 0 }}>
              {/* Stage node */}
              <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}>
                {/* Count bubble */}
                <div style={{
                  width: 28, height: 28, borderRadius: '50%',
                  background: hasItems ? cfg.bg : '#f1f5f9',
                  border: `2px solid ${hasItems ? cfg.border : '#e2e8f0'}`,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: 11, fontWeight: 700,
                  color: hasItems ? cfg.text : MUTED2,
                }}>
                  {count}
                </div>
                {/* Stage label */}
                <div style={{
                  fontSize: 9, fontWeight: hasItems ? 700 : 400,
                  color: hasItems ? cfg.text : MUTED2,
                  textTransform: 'uppercase', letterSpacing: '0.05em',
                  textAlign: 'center', maxWidth: 60,
                  lineHeight: 1.2,
                }}>
                  {stage}
                </div>
              </div>

              {/* Connector line */}
              {!isLast && (
                <div style={{
                  height: 2, width: 24, flexShrink: 0,
                  background: hasItems ? `${cfg.border}80` : '#e2e8f0',
                  marginBottom: 18, // align with circle center
                }} />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── Stage pill ────────────────────────────────────────────────────────────────

function StagePill({ stage }: { stage: string }) {
  const cfg = sc(stage);
  return (
    <span style={{
      fontSize: 10, fontWeight: 600,
      background: cfg.bg, color: cfg.text, border: `1px solid ${cfg.border}`,
      borderRadius: 5, padding: '2px 8px', whiteSpace: 'nowrap',
      textTransform: 'uppercase', letterSpacing: '0.05em',
    }}>
      {stage}
    </span>
  );
}

// ── Stage selector ────────────────────────────────────────────────────────────
// Non-optimistic: waits for backend PATCH response, updates from it.

function StageSelector({
  current, findingId, scanId, onUpdated, disabled,
}: {
  current: string;
  findingId: string;
  scanId: string;
  onUpdated: (newStage: string) => void;
  disabled?: boolean;
}) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const currentIdx = MIGRATION_STAGES.indexOf(current as typeof MIGRATION_STAGES[number]);

  const handleChange = async (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newStage = e.target.value;
    if (newStage === current) return;
    setLoading(true);
    setError(null);
    try {
      // Wait for confirmed backend response; update from it (non-optimistic)
      const updated = await updateRoadmapItemStage(findingId, scanId, newStage);
      onUpdated(updated.status);         // use backend-confirmed stage
    } catch (err) {
      setError(err instanceof Error ? err.message.slice(0, 120) : 'Update failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      <select
        value={current}
        onChange={handleChange}
        disabled={disabled || loading || current === 'MIGRATED'}
        style={{
          fontSize: 11, padding: '3px 6px', borderRadius: 5,
          border: BORDER, background: BG_SURF, color: TEXT,
          cursor: loading ? 'wait' : 'pointer',
          opacity: disabled ? 0.5 : 1,
        }}
      >
        {MIGRATION_STAGES.map((s, i) => (
          <option
            key={s}
            value={s}
            disabled={i < currentIdx} // forward-only
          >
            {s}
          </option>
        ))}
      </select>
      {loading && <span style={{ fontSize: 10, color: MUTED }}>Saving…</span>}
      {error && <span style={{ fontSize: 10, color: '#b91c1c' }}>{error}</span>}
    </div>
  );
}

// ── Roadmap item card (expandable) ────────────────────────────────────────────

function RoadmapItemCard({
  item, scanId, isLast, onStageUpdated,
}: {
  item: RoadmapItem;
  scanId: string;
  isLast: boolean;
  onStageUpdated: (findingId: string, newStage: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const cfg = wc(item.wave);
  const eCfg = ec(item.effort_estimate);

  return (
    <>
      {/* Summary row */}
      <div
        onClick={() => setOpen(o => !o)}
        style={{
          display: 'grid',
          gridTemplateColumns: '4px 1fr 130px 110px 80px 90px 28px',
          alignItems: 'center',
          cursor: 'pointer',
          borderBottom: !open && !isLast ? BORDER2 : 'none',
        }}
        onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = 'rgba(25,40,55,0.02)'; }}
        onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = 'transparent'; }}
      >
        {/* Wave accent bar */}
        <div style={{ alignSelf: 'stretch', background: cfg.border }} />

        {/* Algorithm + purpose */}
        <div style={{ padding: '10px 14px', minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
            <span style={{ fontWeight: 600, color: TEXT, fontSize: 13 }}>{item.algorithm}</span>
            <span style={{ fontSize: 11, color: MUTED, background: 'rgba(25,40,55,0.06)', padding: '1px 6px', borderRadius: 4 }}>
              {item.algorithm_family}
            </span>
            {item.requires_manual_review && (
              <span style={{ fontSize: 10, fontWeight: 600, color: '#92400e', background: '#fffbeb', border: '1px solid #fde68a', padding: '1px 6px', borderRadius: 4 }}>
                MANUAL REVIEW
              </span>
            )}
          </div>
          <div style={{ fontSize: 11, color: MUTED, marginTop: 2 }}>
            {item.crypto_purpose.replace(/_/g, ' ')}
            {item.file_path && (
              <> &nbsp;·&nbsp; <span style={{ fontFamily: 'monospace' }}>{item.file_path}</span></>
            )}
          </div>
        </div>

        {/* Target */}
        <div style={{ padding: '10px 8px', fontSize: 11, color: TEXT, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {item.recommended_target_category}
        </div>

        {/* Stage pill */}
        <div style={{ padding: '10px 8px' }}>
          <StagePill stage={item.status} />
        </div>

        {/* Effort */}
        <div style={{ padding: '10px 8px' }}>
          <span style={{
            fontSize: 10, fontWeight: 600,
            background: eCfg.bg, color: eCfg.text, border: `1px solid ${eCfg.border}`,
            borderRadius: 5, padding: '2px 6px',
          }}>
            {item.effort_estimate.replace(/_/g, '-')}
          </span>
        </div>

        {/* Stage selector — stop click propagation so expand doesn't toggle */}
        <div style={{ padding: '10px 8px' }} onClick={e => e.stopPropagation()}>
          <StageSelector
            current={item.status}
            findingId={item.finding_id}
            scanId={scanId}
            onUpdated={stage => onStageUpdated(item.finding_id, stage)}
          />
        </div>

        {/* Chevron */}
        <div style={{ padding: '10px 8px', color: MUTED2 }}>
          {open ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        </div>
      </div>

      {/* Expanded detail */}
      {open && (
        <div style={{
          padding: '0 20px 16px 20px',
          borderBottom: isLast ? 'none' : BORDER2,
          background: 'rgba(25,40,55,0.012)',
        }}>
          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', paddingTop: 10, marginBottom: 14 }}>
            {item.quantum_migration_score != null && (
              <InfoPill label="Risk Score (Part 7)" value={`${item.quantum_migration_score.toFixed(1)}/100`} accent={TEXT} />
            )}
            {item.migration_priority && (
              <InfoPill label="Migration Priority" value={item.migration_priority.replace(/_/g, ' ')} accent={ACCENT} />
            )}
            {item.quantum_migration_severity && (
              <InfoPill label="Severity" value={item.quantum_migration_severity} accent={TEXT} />
            )}
            <InfoPill label="Effort" value={item.effort_estimate.replace(/_/g, ' ')} accent={TEXT} />
          </div>

          {/* Reason */}
          <DetailSection title="Wave Assignment Reason">
            <div style={{ fontSize: 12, color: MUTED, lineHeight: 1.65 }}>{item.reason}</div>
          </DetailSection>

          {/* Recommended action */}
          <DetailSection title="Recommended Action">
            <div style={{
              fontSize: 12, color: cfg.text, background: cfg.bg,
              border: `1px solid ${cfg.badge}`,
              borderRadius: 7, padding: '10px 14px', lineHeight: 1.65,
              display: 'flex', gap: 8, alignItems: 'flex-start',
            }}>
              <ArrowRight size={14} style={{ flexShrink: 0, marginTop: 1 }} />
              {item.recommended_action}
            </div>
          </DetailSection>

          {/* Target algorithms */}
          {item.recommended_algorithms.length > 0 && (
            <DetailSection title="Target Algorithms">
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                {item.recommended_algorithms.map((a, i) => (
                  <span key={i} style={{
                    fontSize: 12, background: BG_SURF, border: BORDER, borderRadius: 6,
                    padding: '4px 10px', display: 'flex', alignItems: 'center', gap: 6,
                  }}>
                    <Shield size={11} style={{ color: ACCENT }} /> {a}
                  </span>
                ))}
              </div>
              {item.nist_standards.length > 0 && (
                <div style={{ fontSize: 11, color: MUTED2, marginTop: 6 }}>
                  NIST: {item.nist_standards.join(' · ')}
                </div>
              )}
            </DetailSection>
          )}

          {/* Dependencies */}
          {item.dependencies.length > 0 && (
            <DetailSection title="Dependencies">
              <div style={{ fontSize: 12, color: TEXT }}>
                {item.dependencies.length} upstream finding(s) must be migrated first.
                <span style={{ color: MUTED }}> (finding IDs: {item.dependencies.join(', ')})</span>
              </div>
            </DetailSection>
          )}

          {/* Stage timeline (per-item) */}
          <DetailSection title="Migration Stage Progress">
            <div style={{ display: 'flex', gap: 4, alignItems: 'center', flexWrap: 'wrap' }}>
              {MIGRATION_STAGES.map((s, i) => {
                const currentIdx = MIGRATION_STAGES.indexOf(item.status as typeof MIGRATION_STAGES[number]);
                const isDone = i < currentIdx;
                const isCurrent = i === currentIdx;
                const sCfg = sc(s);
                return (
                  <div key={s} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                    <span style={{
                      fontSize: 10, fontWeight: isCurrent ? 700 : 400,
                      background: isCurrent ? sCfg.bg : isDone ? '#f0fdf4' : '#f9fafb',
                      color: isCurrent ? sCfg.text : isDone ? '#15803d' : MUTED2,
                      border: `1px solid ${isCurrent ? sCfg.border : isDone ? '#bbf7d0' : '#e5e7eb'}`,
                      borderRadius: 5, padding: '2px 7px',
                    }}>
                      {isDone && '✓ '}{s}
                    </span>
                    {i < MIGRATION_STAGES.length - 1 && (
                      <ChevronRight size={10} style={{ color: MUTED2, flexShrink: 0 }} />
                    )}
                  </div>
                );
              })}
            </div>
          </DetailSection>

          {/* Links */}
          <div style={{ display: 'flex', gap: 16, marginTop: 10, alignItems: 'center' }}>
            <Link
              to={`/inventory/${scanId}/finding/${item.finding_id}`}
              style={{ fontSize: 12, color: ACCENT, textDecoration: 'none', display: 'flex', alignItems: 'center', gap: 4 }}
            >
              Finding detail <ChevronRight size={12} />
            </Link>
            <Link
              to={`/recommendations/${scanId}`}
              style={{ fontSize: 12, color: ACCENT, textDecoration: 'none', display: 'flex', alignItems: 'center', gap: 4 }}
            >
              Full recommendations <ChevronRight size={12} />
            </Link>
            <span style={{ fontSize: 11, color: MUTED2, marginLeft: 'auto' }}>
              KB {item.kb_version}
            </span>
          </div>
        </div>
      )}
    </>
  );
}

function InfoPill({ label, value, accent }: { label: string; value: string; accent: string }) {
  return (
    <div style={{ background: BG_SURF, border: BORDER, borderRadius: 7, padding: '5px 12px', display: 'flex', flexDirection: 'column', gap: 1 }}>
      <span style={{ fontSize: 10, color: MUTED2, textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 600 }}>{label}</span>
      <span style={{ fontSize: 12, fontWeight: 600, color: accent }}>{value}</span>
    </div>
  );
}

function DetailSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={{ marginBottom: 12 }}>
      <div style={{ fontSize: 10, fontWeight: 600, color: MUTED2, textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 5 }}>
        {title}
      </div>
      {children}
    </div>
  );
}

// ── Wave group ────────────────────────────────────────────────────────────────

function WaveGroup({
  wave, items, scanId, onStageUpdated,
}: {
  wave: number;
  items: RoadmapItem[];
  scanId: string;
  onStageUpdated: (findingId: string, newStage: string) => void;
}) {
  const [collapsed, setCollapsed] = useState(false);
  if (items.length === 0) return null;
  const cfg = wc(wave);

  return (
    <div style={{ background: BG_SURF, border: BORDER, borderRadius: 10, overflow: 'hidden', marginBottom: 12 }}>
      {/* Wave header */}
      <div
        onClick={() => setCollapsed(c => !c)}
        style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '11px 16px', cursor: 'pointer',
          background: cfg.bg, borderBottom: collapsed ? 'none' : BORDER,
          borderLeft: `4px solid ${cfg.border}`,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <span style={{
            fontSize: 11, fontWeight: 700, color: cfg.text,
            textTransform: 'uppercase', letterSpacing: '0.06em',
          }}>
            Wave {wave} — {cfg.label}
          </span>
          <span style={{
            fontSize: 11, fontWeight: 500, color: cfg.text,
          }}>
            {cfg.timeLabel}
          </span>
          <span style={{
            fontSize: 12, fontWeight: 600, color: cfg.text,
            background: BG_SURF, border: `1px solid ${cfg.badge}`,
            borderRadius: 100, padding: '1px 9px',
          }}>
            {items.length} item{items.length !== 1 ? 's' : ''}
          </span>
        </div>
        <div style={{ color: cfg.text }}>{collapsed ? <ChevronDown size={14} /> : <ChevronUp size={14} />}</div>
      </div>

      {/* Column headers + items */}
      {!collapsed && (
        <>
          <div style={{
            display: 'grid',
            gridTemplateColumns: '4px 1fr 130px 110px 80px 90px 28px',
            padding: '5px 0', borderBottom: BORDER,
            fontSize: 10, fontWeight: 600, color: MUTED2,
            textTransform: 'uppercase', letterSpacing: '0.06em',
          }}>
            <div />
            <div style={{ padding: '0 14px' }}>Algorithm / Purpose</div>
            <div style={{ padding: '0 8px' }}>Target</div>
            <div style={{ padding: '0 8px' }}>Stage</div>
            <div style={{ padding: '0 8px' }}>Effort</div>
            <div style={{ padding: '0 8px' }}>Advance</div>
            <div />
          </div>
          {items.map((item, i) => (
            <RoadmapItemCard
              key={item.finding_id}
              item={item}
              scanId={scanId}
              isLast={i === items.length - 1}
              onStageUpdated={onStageUpdated}
            />
          ))}
        </>
      )}
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function RoadmapPage() {
  const { scanId } = useParams<{ scanId: string }>();
  const navigate = useNavigate();

  const [data, setData] = useState<ScanRoadmapResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Per-item stage overrides — updated from backend PATCH response (not optimistic)
  const [stageOverrides, setStageOverrides] = useState<Record<string, string>>({});

  const load = useCallback(async () => {
    if (!scanId) return;
    setLoading(true);
    setError(null);
    try {
      const result = await getRoadmap(scanId);
      setData(result);
      setStageOverrides({});  // clear local overrides; backend has the truth
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load roadmap');
    } finally {
      setLoading(false);
    }
  }, [scanId]);

  useEffect(() => { load(); }, [load]);

  // Stage updated handler — receives backend-confirmed stage from PATCH response
  const handleStageUpdated = useCallback((findingId: string, confirmedStage: string) => {
    setStageOverrides(prev => ({ ...prev, [findingId]: confirmedStage }));
  }, []);

  // Merge backend data with confirmed server stage overrides
  const displayItems = data?.items.map(item => ({
    ...item,
    status: stageOverrides[item.finding_id] ?? item.status,
    migration_stage: stageOverrides[item.finding_id] ?? item.migration_stage,
  })) ?? [];

  const wave1 = displayItems.filter(i => i.wave === 1);
  const wave2 = displayItems.filter(i => i.wave === 2);
  const wave3 = displayItems.filter(i => i.wave === 3);

  // ── Loading ─────────────────────────────────────────────────────────────
  if (loading) {
    return (
      <div style={{ display: 'flex', minHeight: '100dvh', background: BG_PAGE }}>
        <Sidebar scanId={scanId} />
        <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column', gap: 14 }}>
          <div style={{
            width: 36, height: 36, borderRadius: '50%',
            border: `2px solid ${ACCENT}30`, borderTopColor: ACCENT,
            animation: 'spin 0.8s linear infinite',
          }} />
          <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
          <span style={{ fontSize: 13, color: MUTED }}>Building migration roadmap…</span>
        </div>
      </div>
    );
  }

  // ── Error ────────────────────────────────────────────────────────────────
  if (error) {
    return (
      <div style={{ display: 'flex', minHeight: '100dvh', background: BG_PAGE }}>
        <Sidebar scanId={scanId} />
        <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 32 }}>
          <div style={{ background: BG_SURF, border: '1px solid #fecaca', borderRadius: 12, padding: 32, maxWidth: 440, textAlign: 'center' }}>
            <AlertTriangle size={32} style={{ color: '#ef4444', margin: '0 auto 12px', display: 'block' }} />
            <div style={{ fontSize: 15, fontWeight: 600, color: TEXT, marginBottom: 8 }}>Roadmap Failed</div>
            <div style={{ fontSize: 13, color: MUTED, marginBottom: 20 }}>{error}</div>
            <div style={{ display: 'flex', gap: 10, justifyContent: 'center' }}>
              <button onClick={load} style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '7px 16px', borderRadius: 7, border: BORDER, background: BG_SURF, fontSize: 13, cursor: 'pointer', color: TEXT }}>
                <RefreshCw size={13} /> Retry
              </button>
              <button onClick={() => navigate(`/risk/${scanId}`)} style={{ padding: '7px 16px', borderRadius: 7, border: 'none', background: ACCENT, fontSize: 13, cursor: 'pointer', color: 'white', fontWeight: 600 }}>
                Risk Analysis
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (!data) return null;

  return (
    <div style={{ display: 'flex', minHeight: '100dvh', background: BG_PAGE, fontFamily: 'var(--font-body)', color: TEXT }}>
      <Sidebar scanId={scanId} />

      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>

        {/* ── Top header ── */}
        <div style={{
          background: BG_SURF, borderBottom: BORDER, padding: '0 28px',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          height: 56, position: 'sticky', top: 0, zIndex: 10,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ fontSize: 16, fontWeight: 700, fontFamily: 'var(--font-heading)', color: TEXT }}>
              Migration Roadmap
            </span>
            {data.application_name && (
              <>
                <span style={{ color: MUTED2, fontSize: 16 }}>/</span>
                <span style={{ fontSize: 12, color: MUTED, maxWidth: 220, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {data.application_name}
                </span>
              </>
            )}
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <button onClick={load} style={{ display: 'flex', alignItems: 'center', gap: 5, padding: '5px 10px', borderRadius: 7, border: BORDER, background: 'transparent', fontSize: 12, cursor: 'pointer', color: MUTED }}>
              <RefreshCw size={12} /> Refresh
            </button>
            <button onClick={() => navigate(`/recommendations/${scanId}`)} style={{ display: 'flex', alignItems: 'center', gap: 5, padding: '5px 12px', borderRadius: 7, border: BORDER, background: 'transparent', fontSize: 13, cursor: 'pointer', color: TEXT, fontWeight: 500 }}>
              <Map size={13} /> Recommendations
            </button>
            <button onClick={() => navigate(`/risk/${scanId}`)} style={{ display: 'flex', alignItems: 'center', gap: 5, padding: '5px 12px', borderRadius: 7, border: BORDER, background: 'transparent', fontSize: 13, cursor: 'pointer', color: TEXT, fontWeight: 500 }}>
              <BarChart2 size={13} /> Risk Analysis
            </button>
          </div>
        </div>

        {/* ── Body ── */}
        <div style={{ padding: '24px 28px', display: 'flex', flexDirection: 'column', gap: 18 }}>

          {/* Info banner */}
          <div style={{
            display: 'flex', gap: 10, alignItems: 'flex-start',
            background: '#f5f3ff', border: '1px solid #ede9fe',
            borderRadius: 8, padding: '10px 14px', fontSize: 12, color: '#4c1d95',
          }}>
            <Info size={14} style={{ flexShrink: 0, marginTop: 1 }} />
            <span>
              <strong>Deterministic Migration Roadmap</strong> — Wave assignments are derived from actual
              risk scores, application context, and quantum findings. Stage updates persist to the database.
              {' '}{data.summary}
            </span>
          </div>

          {/* ── SECTION 1: Three-Wave Timeline ── */}
          <WaveTimeline summaries={data.wave_summaries} />

          {/* ── SECTION 2: Lifecycle Bar ── */}
          {data.total_items > 0 && (
            <LifecycleBar items={displayItems} />
          )}

          {/* ── SECTION 3: Detailed Items ── */}
          {data.total_items === 0 ? (
            <div style={{ background: BG_SURF, border: BORDER, borderRadius: 10, padding: '48px 20px', textAlign: 'center' }}>
              <CheckCircle size={36} style={{ color: '#22c55e', margin: '0 auto 12px', display: 'block' }} />
              <div style={{ fontSize: 15, fontWeight: 600, color: TEXT, marginBottom: 6 }}>No findings to roadmap</div>
              <div style={{ fontSize: 13, color: MUTED }}>
                Scan this application and run risk analysis first.
              </div>
            </div>
          ) : (
            <>
              {/* Section label */}
              <div style={{ fontSize: 11, fontWeight: 600, color: MUTED2, textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: -6 }}>
                Migration Items ({data.total_items})
              </div>
              <WaveGroup wave={1} items={wave1} scanId={scanId!} onStageUpdated={handleStageUpdated} />
              <WaveGroup wave={2} items={wave2} scanId={scanId!} onStageUpdated={handleStageUpdated} />
              <WaveGroup wave={3} items={wave3} scanId={scanId!} onStageUpdated={handleStageUpdated} />
            </>
          )}

          {/* Footer */}
          <div style={{ fontSize: 11, color: MUTED2, textAlign: 'center', paddingBottom: 16 }}>
            QShield Migration Roadmap Engine — Deterministic wave assignment from actual scan data.
            Stage updates persist to the database and survive page reload.
          </div>
        </div>
      </div>
    </div>
  );
}

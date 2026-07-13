/**
 * RiskPage.tsx — QShield Quantum Migration Risk Analysis
 *
 * Displays:
 *  - Overall quantum migration score + severity gauge
 *  - Methodology name, version, disclaimer
 *  - Factor-by-factor breakdown (with gate/raw transparency)
 *  - Finding counts (quantum vs classical/legacy)
 *  - Top-priority findings with per-finding factor drill-down
 *  - Application business context used for scoring
 *
 * ALL values come from backend API — nothing is hardcoded here.
 */

import { useEffect, useState, useCallback } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import {
  Shield, AlertTriangle, ChevronRight, ArrowLeft, Info,
  Cpu, Clock, Activity, Globe, Lock, FileKey,
  CheckCircle, AlertCircle, HelpCircle,
  ChevronDown, ChevronUp, RefreshCw, Layers
} from 'lucide-react';
import { getRiskAnalysis } from '../services/riskApi';
import type { ScanRiskResult, FindingRisk, FactorScore } from '../services/riskApi';

// ── Design constants ─────────────────────────────────────────────────────────

const SEVERITY_CONFIG = {
  Low:      { bg: 'bg-emerald-500/10', border: 'border-emerald-500/30', text: 'text-emerald-400', bar: '#10b981', ring: '#10b981' },
  Moderate: { bg: 'bg-amber-500/10',   border: 'border-amber-500/30',   text: 'text-amber-400',   bar: '#f59e0b', ring: '#f59e0b' },
  High:     { bg: 'bg-orange-500/10',  border: 'border-orange-500/30',  text: 'text-orange-400',  bar: '#f97316', ring: '#f97316' },
  Critical: { bg: 'bg-red-500/10',     border: 'border-red-500/30',     text: 'text-red-400',     bar: '#ef4444', ring: '#ef4444' },
} as const;

const PRIORITY_CONFIG = {
  immediate: { label: 'Immediate',   color: 'text-red-400',     dot: 'bg-red-400' },
  near_term: { label: 'Near Term',   color: 'text-orange-400',  dot: 'bg-orange-400' },
  long_term: { label: 'Long Term',   color: 'text-amber-400',   dot: 'bg-amber-400' },
  low:        { label: 'Low Priority', color: 'text-emerald-400', dot: 'bg-emerald-400' },
} as const;

const FACTOR_ICONS: Record<string, React.ReactNode> = {
  crypto_vulnerability:   <Cpu size={14} />,
  confidentiality:        <Clock size={14} />,
  business_criticality:   <Activity size={14} />,
  external_exposure:      <Globe size={14} />,
  migration_complexity:   <Layers size={14} />,
  compliance_sensitivity: <Lock size={14} />,
};

// ── Sub-components ────────────────────────────────────────────────────────────

function ScoreGauge({ score, severity }: { score: number; severity: string }) {
  const sev = severity as keyof typeof SEVERITY_CONFIG;
  const cfg = SEVERITY_CONFIG[sev] ?? SEVERITY_CONFIG.Low;
  const circumference = 2 * Math.PI * 54;
  const dash = (score / 100) * circumference;

  return (
    <div className="flex flex-col items-center gap-3">
      <div className="relative w-40 h-40">
        {/* Track */}
        <svg className="w-full h-full -rotate-90" viewBox="0 0 120 120">
          <circle cx="60" cy="60" r="54" fill="none"
            stroke="rgba(255,255,255,0.05)" strokeWidth="10" />
          <circle cx="60" cy="60" r="54" fill="none"
            stroke={cfg.ring} strokeWidth="10" strokeLinecap="round"
            strokeDasharray={`${dash} ${circumference}`}
            style={{ transition: 'stroke-dasharray 1.2s cubic-bezier(.4,0,.2,1)' }} />
        </svg>
        {/* Center text */}
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-4xl font-bold text-white leading-none" style={{ fontFamily: 'var(--font-heading)' }}>
            {Math.round(score)}
          </span>
          <span className="text-xs text-white/40 mt-1">/ 100</span>
        </div>
      </div>
      <span className={`px-4 py-1.5 rounded-full text-sm font-semibold border ${cfg.bg} ${cfg.border} ${cfg.text}`}>
        {severity} Risk
      </span>
    </div>
  );
}

function FactorBar({ factor, maxContrib = 30 }: { factor: FactorScore; maxContrib?: number }) {
  const pct = Math.min(100, (factor.weighted_contribution / maxContrib) * 100);
  const icon = FACTOR_ICONS[factor.factor] ?? <FileKey size={14} />;
  return (
    <div className="group">
      <div className="flex items-center justify-between mb-1.5 gap-2">
        <div className="flex items-center gap-1.5 text-white/60 text-xs min-w-0">
          <span className="shrink-0 text-white/40">{icon}</span>
          <span className="truncate">{factor.label}</span>
          <span className="shrink-0 text-white/30 text-[10px]">({Math.round(factor.weight * 100)}%)</span>
        </div>
        <span className="text-white/80 text-xs font-mono shrink-0">
          {factor.weighted_contribution.toFixed(1)}
          <span className="text-white/30 text-[10px]">pts</span>
        </span>
      </div>
      <div className="h-1.5 rounded-full bg-white/5 overflow-hidden">
        <div
          className="h-full rounded-full bg-gradient-to-r from-violet-500 to-purple-400 transition-all duration-700"
          style={{ width: `${pct}%`, opacity: factor.raw_value < 0.1 ? 0.3 : 1 }}
        />
      </div>
      <p className="mt-1 text-white/35 text-[10px] leading-snug line-clamp-2 hidden group-hover:block">
        {factor.rationale}
      </p>
    </div>
  );
}

function FindingCard({ finding, scanId }: { finding: FindingRisk; scanId: string }) {
  const [expanded, setExpanded] = useState(false);
  const sevCfg = SEVERITY_CONFIG[finding.quantum_migration_severity] ?? SEVERITY_CONFIG.Low;
  const priCfg = PRIORITY_CONFIG[finding.migration_priority] ?? PRIORITY_CONFIG.low;
  const gateReduced = finding.raw_weighted_sum - finding.quantum_migration_score > 5;

  return (
    <div className={`rounded-xl border ${sevCfg.border} bg-white/[0.03] overflow-hidden`}>
      {/* Header */}
      <button
        className="w-full flex items-start gap-4 p-4 text-left hover:bg-white/[0.02] transition-colors"
        onClick={() => setExpanded(e => !e)}
        aria-expanded={expanded}
      >
        {/* Score circle */}
        <div className={`mt-0.5 flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center border ${sevCfg.border} ${sevCfg.bg}`}>
          <span className={`text-sm font-bold ${sevCfg.text}`}>{Math.round(finding.quantum_migration_score)}</span>
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-semibold text-white text-sm">{finding.algorithm}</span>
            <span className="text-white/40 text-xs px-2 py-0.5 rounded bg-white/5">{finding.algorithm_family}</span>
            <span className={`text-[11px] font-medium ${priCfg.color} flex items-center gap-1`}>
              <span className={`w-1.5 h-1.5 rounded-full inline-block ${priCfg.dot}`} />
              {priCfg.label}
            </span>
          </div>
          {finding.file_path && (
            <p className="text-white/35 text-xs mt-0.5 truncate font-mono">{finding.file_path}</p>
          )}
          {/* Classical warning badge */}
          {finding.classical_legacy_risk && (
            <span className="inline-flex items-center gap-1 mt-1.5 px-2 py-0.5 rounded text-[10px] font-medium bg-orange-500/10 text-orange-400 border border-orange-500/20">
              <AlertTriangle size={10} />
              Classical {finding.classical_legacy_risk} risk (separate concern)
            </span>
          )}
        </div>

        <span className="shrink-0 text-white/30">
          {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </span>
      </button>

      {/* Expanded detail */}
      {expanded && (
        <div className="border-t border-white/5 px-4 pb-4 pt-3 space-y-4">
          {/* Explanation */}
          <div className="rounded-lg bg-white/[0.03] p-3">
            <p className="text-white/60 text-xs leading-relaxed">{finding.explanation}</p>
          </div>

          {/* Gate transparency note */}
          {gateReduced && (
            <div className="flex gap-2 rounded-lg bg-violet-500/5 border border-violet-500/20 p-3">
              <Info size={14} className="text-violet-400 shrink-0 mt-0.5" />
              <p className="text-violet-300/70 text-xs leading-relaxed">
                <strong className="text-violet-300">Gate applied:</strong> Raw weighted sum was{' '}
                <span className="font-mono">{finding.raw_weighted_sum.toFixed(1)}/100</span>, reduced to{' '}
                <span className="font-mono">{finding.quantum_migration_score.toFixed(1)}/100</span> by
                crypto-vulnerability gate ({(finding.crypto_vulnerability_gate * 100).toFixed(0)}%).
                This algorithm has low quantum relevance — business context factors are suppressed accordingly.
              </p>
            </div>
          )}

          {/* Classical/Legacy risk section */}
          {finding.classical_legacy_risk && finding.classical_legacy_rationale && (
            <div className="flex gap-2 rounded-lg bg-orange-500/5 border border-orange-500/20 p-3">
              <AlertTriangle size={14} className="text-orange-400 shrink-0 mt-0.5" />
              <div>
                <p className="text-orange-400 text-xs font-semibold mb-0.5">
                  Classical / Legacy Security Issue ({finding.classical_legacy_risk})
                </p>
                <p className="text-orange-300/60 text-xs leading-relaxed">{finding.classical_legacy_rationale}</p>
              </div>
            </div>
          )}

          {/* Factor breakdown */}
          <div className="space-y-2">
            <p className="text-white/30 text-[10px] uppercase tracking-wider font-medium">Factor Breakdown</p>
            <div className="space-y-2">
              {finding.factors.map(f => <FactorBar key={f.factor} factor={f} />)}
            </div>
          </div>

          {/* NIST Recommendation */}
          {finding.nist_recommendation && (
            <div className="flex gap-2 rounded-lg bg-blue-500/5 border border-blue-500/20 p-3">
              <Shield size={14} className="text-blue-400 shrink-0 mt-0.5" />
              <p className="text-blue-300/80 text-xs leading-relaxed">
                <strong className="text-blue-300">NIST Recommendation:</strong> {finding.nist_recommendation}
              </p>
            </div>
          )}

          {/* Link to finding detail */}
          <Link
            to={`/inventory/${scanId}/finding/${finding.finding_id}`}
            className="inline-flex items-center gap-1.5 text-violet-400 hover:text-violet-300 text-xs transition-colors"
          >
            View full finding detail <ChevronRight size={12} />
          </Link>
        </div>
      )}
    </div>
  );
}

function ContextBadge({ label, value, active }: { label: string; value: string; active?: boolean }) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-white/30 text-[10px] uppercase tracking-wide">{label}</span>
      <span className={`text-xs font-medium ${active ? 'text-violet-300' : 'text-white/60'}`}>{value}</span>
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
  const [showMethodology, setShowMethodology] = useState(false);

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

  // ── Loading state ─────────────────────────────────────────────────────────
  if (loading) {
    return (
      <div className="min-h-dvh flex items-center justify-center"
        style={{ background: 'var(--color-login-bg)' }}>
        <div className="flex flex-col items-center gap-4">
          <div className="w-12 h-12 rounded-full border-2 border-violet-500/30 border-t-violet-500 animate-spin" />
          <p className="text-white/50 text-sm">Running risk analysis…</p>
        </div>
      </div>
    );
  }

  // ── Error state ───────────────────────────────────────────────────────────
  if (error) {
    return (
      <div className="min-h-dvh flex items-center justify-center px-6"
        style={{ background: 'var(--color-login-bg)' }}>
        <div className="max-w-md w-full rounded-2xl border border-red-500/20 bg-red-500/5 p-8 text-center space-y-4">
          <AlertTriangle size={40} className="mx-auto text-red-400" />
          <h2 className="text-white font-semibold">Risk Analysis Failed</h2>
          <p className="text-white/50 text-sm">{error}</p>
          <div className="flex gap-3 justify-center">
            <button onClick={load}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-white/5 hover:bg-white/10 text-white/70 text-sm transition-colors">
              <RefreshCw size={14} /> Retry
            </button>
            <button onClick={() => navigate(-1)}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-violet-600 hover:bg-violet-500 text-white text-sm transition-colors">
              <ArrowLeft size={14} /> Back
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (!data) return null;

  const sev = data.overall_severity as keyof typeof SEVERITY_CONFIG;
  const sevCfg = SEVERITY_CONFIG[sev] ?? SEVERITY_CONFIG.Low;

  // Factor summary sorted by contribution descending
  const factorEntries = Object.entries(data.factor_summary).sort((a, b) => b[1] - a[1]);

  const bg = 'linear-gradient(135deg, #0d0f14 0%, #111827 50%, #0a0d12 100%)';

  return (
    <div className="min-h-dvh" style={{ background: bg }}>
      {/* ── Top bar ─────────────────────────────────────────────────────────── */}
      <div className="sticky top-0 z-10 backdrop-blur-xl border-b border-white/5"
        style={{ background: 'rgba(13,15,20,0.85)' }}>
        <div className="max-w-5xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3 min-w-0">
            <button onClick={() => navigate(`/inventory/${scanId}`)}
              className="shrink-0 p-1.5 rounded-lg hover:bg-white/5 text-white/50 hover:text-white/80 transition-colors">
              <ArrowLeft size={18} />
            </button>
            <div className="min-w-0">
              <h1 className="text-white font-semibold text-sm truncate">Risk Analysis</h1>
              <p className="text-white/30 text-[10px] font-mono truncate">{scanId}</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Link
              to={`/inventory/${scanId}`}
              className="text-xs text-white/40 hover:text-white/70 transition-colors hidden sm:block"
            >
              ← Inventory
            </Link>
            <button onClick={load}
              className="p-1.5 rounded-lg hover:bg-white/5 text-white/40 hover:text-white/70 transition-colors"
              title="Recalculate">
              <RefreshCw size={15} />
            </button>
          </div>
        </div>
      </div>

      <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8 space-y-8">

        {/* ── Context defaulted warning ─────────────────────────────────── */}
        {data.context_defaulted && (
          <div className="flex gap-3 rounded-xl border border-amber-500/20 bg-amber-500/5 px-4 py-3">
            <HelpCircle size={16} className="text-amber-400 shrink-0 mt-0.5" />
            <p className="text-amber-300/80 text-xs leading-relaxed">
              Business context for this application was unavailable. Neutral defaults were used
              (medium criticality, internal, medium-term). Scores may understate or overstate
              actual migration priority.
            </p>
          </div>
        )}

        {/* ── Hero: score + overall counts ──────────────────────────────── */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

          {/* Score gauge */}
          <div className={`lg:col-span-1 rounded-2xl border ${sevCfg.border} p-6 flex flex-col items-center gap-5`}
            style={{ background: 'rgba(255,255,255,0.02)' }}>
            <ScoreGauge score={data.overall_quantum_score} severity={data.overall_severity} />
            <div className="text-center space-y-1">
              <p className="text-white/70 text-sm font-medium">Quantum Migration Priority</p>
              <p className="text-white/30 text-xs leading-relaxed max-w-xs">
                {data.summary_text}
              </p>
            </div>
          </div>

          {/* Counts grid */}
          <div className="lg:col-span-2 grid grid-cols-2 sm:grid-cols-2 gap-4">
            {/* Quantum vulnerable */}
            <div className="rounded-2xl border border-red-500/20 bg-red-500/5 p-5 space-y-2">
              <div className="flex items-center gap-2 text-red-400">
                <AlertCircle size={18} />
                <span className="text-sm font-semibold">Quantum Vulnerable</span>
              </div>
              <p className="text-4xl font-bold text-white">{data.vulnerable_count}</p>
              <p className="text-white/35 text-xs">algorithms requiring PQC migration</p>
            </div>

            {/* Quantum safe */}
            <div className="rounded-2xl border border-emerald-500/20 bg-emerald-500/5 p-5 space-y-2">
              <div className="flex items-center gap-2 text-emerald-400">
                <CheckCircle size={18} />
                <span className="text-sm font-semibold">Already Safe</span>
              </div>
              <p className="text-4xl font-bold text-white">{data.safe_count}</p>
              <p className="text-white/35 text-xs">quantum-safe algorithms found</p>
            </div>

            {/* Classical/legacy — explicitly separate */}
            <div className="rounded-2xl border border-orange-500/20 bg-orange-500/5 p-5 space-y-2">
              <div className="flex items-center gap-2 text-orange-400">
                <AlertTriangle size={18} />
                <span className="text-sm font-semibold">Classical / Legacy</span>
              </div>
              <p className="text-4xl font-bold text-white">{data.legacy_count}</p>
              <p className="text-white/35 text-xs">classical security concerns (separate from quantum risk)</p>
            </div>

            {/* Borderline */}
            <div className="rounded-2xl border border-amber-500/20 bg-amber-500/5 p-5 space-y-2">
              <div className="flex items-center gap-2 text-amber-400">
                <HelpCircle size={18} />
                <span className="text-sm font-semibold">Borderline / Review</span>
              </div>
              <p className="text-4xl font-bold text-white">{data.borderline_count}</p>
              <p className="text-white/35 text-xs">requires case-by-case assessment</p>
            </div>
          </div>
        </div>

        {/* ── Factor breakdown ────────────────────────────────────────────── */}
        <div className="rounded-2xl border border-white/5 p-6 space-y-5" style={{ background: 'rgba(255,255,255,0.02)' }}>
          <div className="flex items-center justify-between gap-4">
            <div>
              <h2 className="text-white font-semibold">Factor Breakdown</h2>
              <p className="text-white/30 text-xs mt-0.5">
                Average weighted contribution across all findings (before crypto-vulnerability gate)
              </p>
            </div>
            <button
              onClick={() => setShowMethodology(m => !m)}
              className="shrink-0 flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/8 text-white/40 hover:text-white/60 text-xs transition-colors"
            >
              <Info size={12} />
              {showMethodology ? 'Hide' : 'Methodology'}
            </button>
          </div>

          {/* Methodology explanation panel */}
          {showMethodology && (
            <div className="rounded-xl border border-violet-500/20 bg-violet-500/5 p-4 space-y-3">
              <div className="flex items-center gap-2">
                <Shield size={16} className="text-violet-400" />
                <span className="text-violet-300 text-sm font-semibold">{data.methodology}</span>
                <span className="text-violet-400/50 text-xs">v{data.methodology_version}</span>
              </div>
              <p className="text-violet-300/60 text-xs leading-relaxed">{data.methodology_description}</p>
              <p className="text-white/30 text-xs leading-relaxed italic">{data.disclaimer}</p>
            </div>
          )}

          {/* Factor bars */}
          <div className="space-y-4">
            {factorEntries.map(([factor, contrib]) => {
              const label = data.top_findings[0]?.factors.find(f => f.factor === factor)?.label ?? factor.replace(/_/g, ' ');
              const icon = FACTOR_ICONS[factor] ?? <FileKey size={14} />;
              const pct = Math.min(100, (contrib / 30) * 100);
              return (
                <div key={factor}>
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="flex items-center gap-1.5 text-white/60 text-xs">
                      <span className="text-white/40">{icon}</span>
                      {label}
                    </span>
                    <span className="text-white/70 text-xs font-mono">{contrib.toFixed(1)} pts avg</span>
                  </div>
                  <div className="h-2 rounded-full bg-white/5 overflow-hidden">
                    <div
                      className="h-full rounded-full bg-gradient-to-r from-violet-600 to-purple-400 transition-all duration-700"
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* ── Business context used ───────────────────────────────────────── */}
        <div className="rounded-2xl border border-white/5 p-5 space-y-4" style={{ background: 'rgba(255,255,255,0.02)' }}>
          <h2 className="text-white font-semibold text-sm flex items-center gap-2">
            <Activity size={16} className="text-violet-400" />
            Application Context Used for Scoring
          </h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
            <ContextBadge label="Criticality"     value={data.business_criticality} active={['high','critical'].includes(data.business_criticality)} />
            <ContextBadge label="Environment"     value={data.environment} />
            <ContextBadge label="Internet Exposed" value={data.internet_exposed ? 'Yes' : 'No'} active={data.internet_exposed} />
            <ContextBadge label="Confidentiality" value={data.confidentiality_requirement.replace(/_/g, ' ')} />
            <ContextBadge label="Data Sensitivity" value={data.data_sensitivity} active={['restricted','top_secret'].includes(data.data_sensitivity)} />
            <ContextBadge label="Data Lifetime"   value={`${data.data_lifetime_years} years`} active={data.data_lifetime_years >= 10} />
          </div>
        </div>

        {/* ── Top priority findings ────────────────────────────────────────── */}
        {data.top_findings.length > 0 && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-white font-semibold flex items-center gap-2">
                <Shield size={18} className="text-violet-400" />
                Priority Findings
                <span className="ml-1 text-white/30 text-sm font-normal">
                  ({data.top_findings.length} highest-priority)
                </span>
              </h2>
              <Link
                to={`/inventory/${scanId}`}
                className="text-xs text-violet-400 hover:text-violet-300 transition-colors flex items-center gap-1"
              >
                View all findings <ChevronRight size={12} />
              </Link>
            </div>
            <div className="space-y-3">
              {data.top_findings.map(f => (
                <FindingCard key={f.finding_id} finding={f} scanId={scanId!} />
              ))}
            </div>
          </div>
        )}

        {/* ── Empty state ──────────────────────────────────────────────────── */}
        {data.top_findings.length === 0 && (
          <div className="rounded-2xl border border-emerald-500/20 bg-emerald-500/5 p-8 text-center space-y-3">
            <CheckCircle size={36} className="mx-auto text-emerald-400" />
            <h3 className="text-white font-semibold">No Quantum Migration Required</h3>
            <p className="text-white/40 text-sm max-w-sm mx-auto">
              {data.summary_text || 'No quantum-vulnerable cryptography was detected in this scan.'}
            </p>
            <Link
              to={`/inventory/${scanId}`}
              className="inline-flex items-center gap-1.5 text-sm text-violet-400 hover:text-violet-300 transition-colors"
            >
              View full inventory <ChevronRight size={14} />
            </Link>
          </div>
        )}

        {/* ── Footer disclaimer ────────────────────────────────────────────── */}
        <p className="text-white/20 text-[10px] text-center leading-relaxed pb-4">
          {data.disclaimer}
        </p>
      </div>
    </div>
  );
}

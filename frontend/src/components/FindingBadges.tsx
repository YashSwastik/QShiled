/**
 * CategoryBadge — visual chip for FindingCategory.
 * QuantumBadge  — visual chip for QuantumStatus.
 * ConfidenceBar — thin bar showing detection confidence.
 *
 * Uses semantic status colours — purple only for accent/brand where warranted.
 */
import type { FindingCategory, QuantumStatus } from '../services/inventoryApi';

// ── Category ──────────────────────────────────────────────────────────────────

const CAT_META: Record<FindingCategory, { label: string; bg: string; text: string }> = {
  QUANTUM_VULNERABLE_PUBLIC_KEY: { label: 'Quantum Vulnerable', bg: '#fef2f2', text: '#b91c1c' },
  SYMMETRIC:                     { label: 'Symmetric',          bg: '#f0fdf4', text: '#15803d' },
  HASH:                          { label: 'Hash',               bg: '#eff6ff', text: '#1d4ed8' },
  LEGACY_DEPRECATED:             { label: 'Legacy / Deprecated',bg: '#fff7ed', text: '#c2410c' },
  POST_QUANTUM:                  { label: 'Post-Quantum',       bg: '#f0fdf4', text: '#166534' },
  UNKNOWN_REVIEW:                { label: 'Needs Review',       bg: '#f5f3ff', text: '#6b21a8' },
};

export function CategoryBadge({ category, size = 'sm' }: { category: FindingCategory; size?: 'xs' | 'sm' }) {
  const m = CAT_META[category] ?? CAT_META.UNKNOWN_REVIEW;
  const px = size === 'xs' ? '6px' : '8px';
  const py = size === 'xs' ? '2px' : '3px';
  const fs = size === 'xs' ? '10px' : '11px';
  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        padding: `${py} ${px}`,
        borderRadius: 6,
        fontSize: fs,
        fontWeight: 600,
        letterSpacing: '0.02em',
        background: m.bg,
        color: m.text,
        whiteSpace: 'nowrap',
      }}
    >
      {m.label}
    </span>
  );
}

// ── Quantum status ────────────────────────────────────────────────────────────

const QS_META: Record<QuantumStatus, { label: string; bg: string; text: string; dot: string }> = {
  vulnerable: { label: 'Quantum Vulnerable', bg: '#fef2f2', text: '#b91c1c', dot: '#ef4444' },
  safe:       { label: 'Quantum Safe',       bg: '#f0fdf4', text: '#166534', dot: '#22c55e' },
  borderline: { label: 'Borderline',         bg: '#fffbeb', text: '#92400e', dot: '#f59e0b' },
  unknown:    { label: 'Unknown',            bg: '#f9fafb', text: '#374151', dot: '#9ca3af' },
  hybrid:     { label: 'Hybrid',             bg: '#eff6ff', text: '#1e40af', dot: '#3b82f6' },
};

export function QuantumBadge({ status, size = 'sm' }: { status: QuantumStatus; size?: 'xs' | 'sm' }) {
  const m = QS_META[status] ?? QS_META.unknown;
  const px = size === 'xs' ? '6px' : '8px';
  const py = size === 'xs' ? '2px' : '3px';
  const fs = size === 'xs' ? '10px' : '11px';
  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 5,
        padding: `${py} ${px}`,
        borderRadius: 6,
        fontSize: fs,
        fontWeight: 600,
        background: m.bg,
        color: m.text,
        whiteSpace: 'nowrap',
      }}
    >
      <span
        style={{
          width: 6, height: 6,
          borderRadius: '50%',
          background: m.dot,
          flexShrink: 0,
        }}
      />
      {m.label}
    </span>
  );
}

// ── Confidence bar ────────────────────────────────────────────────────────────

export function ConfidenceBar({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const color = pct >= 90 ? '#22c55e' : pct >= 70 ? '#f59e0b' : '#9ca3af';
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
      <div
        style={{
          width: 48, height: 4, borderRadius: 2,
          background: 'rgba(25,40,55,0.1)',
          overflow: 'hidden',
          flexShrink: 0,
        }}
      >
        <div style={{ width: `${pct}%`, height: '100%', borderRadius: 2, background: color }} />
      </div>
      <span style={{ fontSize: 11, opacity: 0.6, fontVariantNumeric: 'tabular-nums' }}>
        {pct}%
      </span>
    </div>
  );
}

// ── Detection method label ────────────────────────────────────────────────────

const METHOD_LABELS: Record<string, string> = {
  regex:      'Pattern match',
  ast:        'AST analysis',
  cert_parse: 'Certificate parse',
};

export function DetectionMethodLabel({ method }: { method: string }) {
  return (
    <span style={{ fontSize: 11, opacity: 0.55, fontStyle: 'italic' }}>
      {METHOD_LABELS[method] ?? method}
    </span>
  );
}

/**
 * InventoryPage — Cryptographic Inventory (CBOM) viewer.
 *
 * Route: /inventory/:scanId
 *
 * Features:
 *   - Real data from GET /api/findings and /api/findings/summary
 *   - Search by algorithm / file / context
 *   - Filter: category, quantum_status, algorithm_family
 *   - Sort: algorithm, confidence, category, quantum_status, file_path
 *   - Pagination
 *   - Loading / empty / error / no-findings states
 *   - Click row → /inventory/:scanId/finding/:findingId
 */
import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Search, SlidersHorizontal, ChevronUp, ChevronDown,
  ChevronLeft, ChevronRight, FileSearch, AlertTriangle,
  ArrowLeft, ShieldCheck, RefreshCw,
} from 'lucide-react';
import QShieldLogo from '../components/QShieldLogo';
import { CategoryBadge, QuantumBadge, ConfidenceBar } from '../components/FindingBadges';
import {
  getFindings, getFindingSummary, getScan,
  type Finding, type FindingListResponse, type FindingSummary, type Scan,
  type FindingCategory, type QuantumStatus,
} from '../services/inventoryApi';

// ── Constants ─────────────────────────────────────────────────────────────────

const CATEGORIES: { value: string; label: string }[] = [
  { value: '', label: 'All Categories' },
  { value: 'QUANTUM_VULNERABLE_PUBLIC_KEY', label: 'Quantum Vulnerable' },
  { value: 'SYMMETRIC',                     label: 'Symmetric' },
  { value: 'HASH',                          label: 'Hash' },
  { value: 'LEGACY_DEPRECATED',             label: 'Legacy / Deprecated' },
  { value: 'POST_QUANTUM',                  label: 'Post-Quantum' },
  { value: 'UNKNOWN_REVIEW',                label: 'Needs Review' },
];

const QUANTUM_OPTIONS: { value: string; label: string }[] = [
  { value: '', label: 'Any Quantum Status' },
  { value: 'vulnerable',  label: 'Vulnerable' },
  { value: 'safe',        label: 'Safe' },
  { value: 'borderline',  label: 'Borderline' },
  { value: 'unknown',     label: 'Unknown' },
];

const SORT_OPTIONS = [
  { value: 'created_at', label: 'Date found' },
  { value: 'algorithm',  label: 'Algorithm' },
  { value: 'category',   label: 'Category' },
  { value: 'quantum_status', label: 'Quantum status' },
  { value: 'confidence', label: 'Confidence' },
  { value: 'file_path',  label: 'File path' },
];

const PAGE_SIZE = 25;

// ── Styles ───────────────────────────────────────────────────────────────────

const S = {
  surface: { background: 'white', border: '1px solid rgba(25,40,55,0.08)', borderRadius: 12 },
  inputBase: {
    width: '100%',
    borderRadius: 8,
    border: '1px solid rgba(25,40,55,0.15)',
    background: 'white',
    color: 'var(--color-text)',
    fontSize: 13,
    outline: 'none',
    padding: '7px 12px',
  } as React.CSSProperties,
  selectBase: {
    borderRadius: 8,
    border: '1px solid rgba(25,40,55,0.15)',
    background: 'white',
    color: 'var(--color-text)',
    fontSize: 13,
    padding: '7px 10px',
    cursor: 'pointer',
    outline: 'none',
  } as React.CSSProperties,
  th: {
    padding: '10px 14px',
    fontSize: 11,
    fontWeight: 600,
    textTransform: 'uppercase' as const,
    letterSpacing: '0.06em',
    opacity: 0.45,
    whiteSpace: 'nowrap' as const,
    cursor: 'pointer',
    userSelect: 'none' as const,
    borderBottom: '1px solid rgba(25,40,55,0.07)',
  },
  td: {
    padding: '11px 14px',
    fontSize: 13,
    borderBottom: '1px solid rgba(25,40,55,0.06)',
    verticalAlign: 'middle' as const,
  },
};

// ── Sub-components ────────────────────────────────────────────────────────────

function SummaryCard({ label, value, sub }: { label: string; value: string | number; sub?: string }) {
  return (
    <div style={{ ...S.surface, padding: '16px 20px', minWidth: 120, flex: 1 }}>
      <div style={{ fontSize: 22, fontWeight: 700, color: 'var(--color-text)', fontFamily: 'var(--font-heading)' }}>{value}</div>
      <div style={{ fontSize: 12, fontWeight: 600, marginTop: 2, opacity: 0.55 }}>{label}</div>
      {sub && <div style={{ fontSize: 11, marginTop: 1, opacity: 0.4 }}>{sub}</div>}
    </div>
  );
}

function SortHeader({
  label, field, sortBy, sortDir, onSort,
}: {
  label: string; field: string;
  sortBy: string; sortDir: 'asc' | 'desc';
  onSort: (f: string) => void;
}) {
  const active = sortBy === field;
  return (
    <th style={{ ...S.th, color: active ? 'var(--color-text)' : undefined }} onClick={() => onSort(field)}>
      <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
        {label}
        {active
          ? (sortDir === 'asc'
              ? <ChevronUp size={11} />
              : <ChevronDown size={11} />)
          : <ChevronUp size={11} style={{ opacity: 0.2 }} />
        }
      </span>
    </th>
  );
}

// ── Main ──────────────────────────────────────────────────────────────────────

export default function InventoryPage() {
  const { scanId } = useParams<{ scanId: string }>();
  const navigate = useNavigate();

  // ── Scan meta ──────────────────────────────────────────────────────────────
  const [scan, setScan] = useState<Scan | null>(null);
  const [summary, setSummary] = useState<FindingSummary | null>(null);

  // ── Filters ────────────────────────────────────────────────────────────────
  const [search, setSearch]           = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [category, setCategory]       = useState('');
  const [quantumFilter, setQuantum]   = useState('');
  const [familyFilter, setFamily]     = useState('');
  const [sortBy, setSortBy]           = useState('created_at');
  const [sortDir, setSortDir]         = useState<'asc' | 'desc'>('asc');
  const [page, setPage]               = useState(1);
  const [showFilters, setShowFilters] = useState(false);

  // ── Data ───────────────────────────────────────────────────────────────────
  const [data, setData]           = useState<FindingListResponse | null>(null);
  const [loading, setLoading]     = useState(true);
  const [summaryLoading, setSummaryLoading] = useState(true);
  const [error, setError]         = useState<string | null>(null);

  // Debounce search
  useEffect(() => {
    const t = setTimeout(() => setDebouncedSearch(search), 320);
    return () => clearTimeout(t);
  }, [search]);

  // Load scan metadata once
  useEffect(() => {
    if (!scanId) return;
    getScan(scanId).then(setScan).catch(() => {});
    setSummaryLoading(true);
    getFindingSummary(scanId)
      .then(setSummary)
      .finally(() => setSummaryLoading(false));
  }, [scanId]);

  // Load findings whenever filters change
  const loadFindings = useCallback(async () => {
    if (!scanId) return;
    setLoading(true);
    setError(null);
    try {
      const res = await getFindings({
        scan_id: scanId,
        search: debouncedSearch || undefined,
        category: category || undefined,
        quantum_status: quantumFilter || undefined,
        algorithm_family: familyFilter || undefined,
        sort_by: sortBy,
        sort_dir: sortDir,
        page,
        page_size: PAGE_SIZE,
      });
      setData(res);
    } catch {
      setError('Failed to load findings. Is the backend running?');
    } finally {
      setLoading(false);
    }
  }, [scanId, debouncedSearch, category, quantumFilter, familyFilter, sortBy, sortDir, page]);

  useEffect(() => { loadFindings(); }, [loadFindings]);

  // Reset to page 1 on filter change
  useEffect(() => { setPage(1); }, [debouncedSearch, category, quantumFilter, familyFilter]);

  // ── Sort toggle ────────────────────────────────────────────────────────────
  function handleSort(field: string) {
    if (sortBy === field) {
      setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(field);
      setSortDir('asc');
    }
    setPage(1);
  }

  // ── Derived ────────────────────────────────────────────────────────────────
  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 1;
  const families = summary
    ? summary.by_algorithm_family.map(f => f.family)
    : [];

  // ── Render ─────────────────────────────────────────────────────────────────
  return (
    <div
      className="min-h-dvh flex flex-col"
      style={{ background: '#f8f8f5', color: 'var(--color-text)' }}
    >
      {/* ── Header ── */}
      <header
        style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          padding: '14px 24px', borderBottom: '1px solid rgba(25,40,55,0.1)',
          background: 'white', position: 'sticky', top: 0, zIndex: 20,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <a href="/" style={{ display: 'flex', alignItems: 'center', gap: 8, textDecoration: 'none' }}>
            <QShieldLogo size={22} color="#192837" />
            <span style={{ fontFamily: 'var(--font-heading)', fontWeight: 700, fontSize: 15, color: 'var(--color-text)' }}>
              QShield
            </span>
          </a>
          <span style={{ opacity: 0.2, fontSize: 18 }}>/</span>
          <span style={{ fontSize: 13, opacity: 0.6 }}>Crypto Inventory</span>
          {scan && (
            <>
              <span style={{ opacity: 0.2, fontSize: 18 }}>/</span>
              <span style={{ fontSize: 13, fontWeight: 500 }} title={scan.upload_name ?? ''}>
                {scan.upload_name
                  ? (scan.upload_name.length > 28 ? scan.upload_name.slice(0, 28) + '…' : scan.upload_name)
                  : scan.name}
              </span>
            </>
          )}
        </div>
        <button
          onClick={() => navigate(-1)}
          style={{
            display: 'flex', alignItems: 'center', gap: 6,
            fontSize: 13, opacity: 0.5, background: 'none',
            border: 'none', cursor: 'pointer', color: 'var(--color-text)',
          }}
          onMouseEnter={(e) => (e.currentTarget.style.opacity = '1')}
          onMouseLeave={(e) => (e.currentTarget.style.opacity = '0.5')}
        >
          <ArrowLeft size={14} /> Back
        </button>
      </header>

      {/* ── Main ── */}
      <main style={{ flex: 1, padding: '24px 24px 40px', maxWidth: 1280, width: '100%', margin: '0 auto' }}>

        {/* Page title + summary cards */}
        <div style={{ marginBottom: 20 }}>
          <h1 style={{ fontFamily: 'var(--font-heading)', fontSize: 22, margin: '0 0 4px' }}>
            Cryptographic Inventory
          </h1>
          <p style={{ fontSize: 13, opacity: 0.5, margin: 0 }}>
            CBOM — all cryptographic usages detected during this scan
          </p>
        </div>

        {/* Summary row */}
        {!summaryLoading && summary && (
          <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 20 }}>
            <SummaryCard label="Total findings" value={summary.total} />
            <SummaryCard
              label="Quantum vulnerable"
              value={summary.by_quantum_status.vulnerable ?? 0}
              sub="need migration"
            />
            <SummaryCard
              label="Legacy / deprecated"
              value={summary.by_category.LEGACY_DEPRECATED ?? 0}
              sub="classical weakness"
            />
            <SummaryCard
              label="Quantum safe"
              value={(summary.by_quantum_status.safe ?? 0) + (summary.by_quantum_status.borderline ?? 0)}
              sub="safe or borderline"
            />
            <SummaryCard
              label="Post-quantum"
              value={summary.by_category.POST_QUANTUM ?? 0}
              sub="already migrated"
            />
          </div>
        )}

        {/* ── Filter bar ── */}
        <div
          style={{
            ...S.surface,
            padding: '12px 16px',
            marginBottom: 16,
            display: 'flex',
            flexWrap: 'wrap',
            gap: 8,
            alignItems: 'center',
          }}
        >
          {/* Search */}
          <div style={{ position: 'relative', flex: '1 1 200px', minWidth: 160 }}>
            <Search
              size={13}
              style={{
                position: 'absolute', left: 10, top: '50%',
                transform: 'translateY(-50%)', opacity: 0.35,
              }}
            />
            <input
              type="text"
              placeholder="Search algorithm, file, context…"
              value={search}
              onChange={e => setSearch(e.target.value)}
              style={{ ...S.inputBase, paddingLeft: 30 }}
            />
          </div>

          {/* Category filter */}
          <select
            value={category}
            onChange={e => setCategory(e.target.value)}
            style={S.selectBase}
          >
            {CATEGORIES.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
          </select>

          {/* Quantum filter */}
          <select
            value={quantumFilter}
            onChange={e => setQuantum(e.target.value)}
            style={S.selectBase}
          >
            {QUANTUM_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>

          {/* More filters toggle */}
          <button
            onClick={() => setShowFilters(v => !v)}
            style={{
              display: 'flex', alignItems: 'center', gap: 5,
              padding: '7px 12px', borderRadius: 8, border: '1px solid rgba(25,40,55,0.15)',
              background: showFilters ? 'rgba(25,40,55,0.06)' : 'white',
              fontSize: 13, cursor: 'pointer', color: 'var(--color-text)',
            }}
          >
            <SlidersHorizontal size={12} />
            {showFilters ? 'Fewer' : 'More'} filters
          </button>

          {/* Sort */}
          <div style={{ display: 'flex', gap: 6, marginLeft: 'auto', alignItems: 'center' }}>
            <select
              value={sortBy}
              onChange={e => { setSortBy(e.target.value); setPage(1); }}
              style={S.selectBase}
            >
              {SORT_OPTIONS.map(s => <option key={s.value} value={s.value}>{s.label}</option>)}
            </select>
            <button
              onClick={() => { setSortDir(d => d === 'asc' ? 'desc' : 'asc'); setPage(1); }}
              title={sortDir === 'asc' ? 'Ascending' : 'Descending'}
              style={{
                padding: '7px 10px', borderRadius: 8, border: '1px solid rgba(25,40,55,0.15)',
                background: 'white', cursor: 'pointer', display: 'flex', alignItems: 'center',
              }}
            >
              {sortDir === 'asc' ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
            </button>
          </div>
        </div>

        {/* Extended filters */}
        <AnimatePresence>
          {showFilters && (
            <motion.div
              key="ext"
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.2 }}
              style={{ overflow: 'hidden', marginBottom: 12 }}
            >
              <div style={{ ...S.surface, padding: '12px 16px', display: 'flex', gap: 10, flexWrap: 'wrap' }}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                  <label style={{ fontSize: 11, fontWeight: 600, opacity: 0.45, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                    Algorithm family
                  </label>
                  <select
                    value={familyFilter}
                    onChange={e => setFamily(e.target.value)}
                    style={{ ...S.selectBase, minWidth: 160 }}
                  >
                    <option value="">All families</option>
                    {families.map(f => <option key={f} value={f}>{f}</option>)}
                  </select>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* ── Table or states ── */}
        {error && (
          <div
            style={{
              ...S.surface, padding: 32, textAlign: 'center',
              display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 12,
            }}
          >
            <AlertTriangle size={28} style={{ color: '#ef4444' }} />
            <p style={{ margin: 0, opacity: 0.7, fontSize: 14 }}>{error}</p>
            <button
              onClick={loadFindings}
              style={{
                display: 'flex', alignItems: 'center', gap: 6,
                padding: '8px 16px', borderRadius: 8, border: '1px solid rgba(25,40,55,0.15)',
                background: 'white', cursor: 'pointer', fontSize: 13,
              }}
            >
              <RefreshCw size={13} /> Retry
            </button>
          </div>
        )}

        {!error && loading && (
          <div style={{ ...S.surface, padding: 48, textAlign: 'center' }}>
            <div style={{ opacity: 0.4, fontSize: 13 }}>Loading findings…</div>
          </div>
        )}

        {!error && !loading && data && data.total === 0 && !search && !category && !quantumFilter && !familyFilter && (
          <div
            style={{
              ...S.surface, padding: '56px 32px', textAlign: 'center',
              display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 12,
            }}
          >
            <ShieldCheck size={40} style={{ opacity: 0.25 }} />
            <div style={{ fontFamily: 'var(--font-heading)', fontSize: 18, opacity: 0.6 }}>
              No cryptographic findings
            </div>
            <p style={{ margin: 0, opacity: 0.4, fontSize: 13, maxWidth: 320 }}>
              The scanner found no supported cryptographic usage in the uploaded files. This may mean
              the files don't use cryptography, or the patterns weren't detected.
            </p>
          </div>
        )}

        {!error && !loading && data && data.total === 0 && (search || category || quantumFilter || familyFilter) && (
          <div style={{ ...S.surface, padding: '40px 32px', textAlign: 'center' }}>
            <FileSearch size={32} style={{ opacity: 0.25, display: 'block', margin: '0 auto 12px' }} />
            <p style={{ margin: 0, opacity: 0.5, fontSize: 14 }}>No findings match your filters.</p>
          </div>
        )}

        {!error && !loading && data && data.total > 0 && (
          <FindingsTable
            items={data.items}
            scanId={scanId!}
            sortBy={sortBy}
            sortDir={sortDir}
            onSort={handleSort}
          />
        )}

        {/* ── Pagination ── */}
        {!error && data && data.total > PAGE_SIZE && (
          <div
            style={{
              display: 'flex', justifyContent: 'space-between', alignItems: 'center',
              marginTop: 16, fontSize: 13, opacity: 0.6,
            }}
          >
            <span>
              Showing {(page - 1) * PAGE_SIZE + 1}–{Math.min(page * PAGE_SIZE, data.total)} of {data.total}
            </span>
            <div style={{ display: 'flex', gap: 6 }}>
              <button
                disabled={page <= 1}
                onClick={() => setPage(p => p - 1)}
                style={{
                  padding: '5px 10px', borderRadius: 6, border: '1px solid rgba(25,40,55,0.15)',
                  background: 'white', cursor: page > 1 ? 'pointer' : 'default',
                  opacity: page <= 1 ? 0.35 : 1,
                }}
              >
                <ChevronLeft size={13} />
              </button>
              <span style={{ padding: '5px 12px', background: 'white', borderRadius: 6, border: '1px solid rgba(25,40,55,0.15)' }}>
                {page} / {totalPages}
              </span>
              <button
                disabled={page >= totalPages}
                onClick={() => setPage(p => p + 1)}
                style={{
                  padding: '5px 10px', borderRadius: 6, border: '1px solid rgba(25,40,55,0.15)',
                  background: 'white', cursor: page < totalPages ? 'pointer' : 'default',
                  opacity: page >= totalPages ? 0.35 : 1,
                }}
              >
                <ChevronRight size={13} />
              </button>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

// ── Findings table ────────────────────────────────────────────────────────────

function FindingsTable({
  items, scanId, sortBy, sortDir, onSort,
}: {
  items: Finding[], scanId: string,
  sortBy: string, sortDir: 'asc' | 'desc',
  onSort: (f: string) => void,
}) {
  const navigate = useNavigate();

  return (
    <div style={{ ...S.surface, overflow: 'hidden' }}>
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ background: '#fafafa' }}>
              <SortHeader label="Algorithm"      field="algorithm"      sortBy={sortBy} sortDir={sortDir} onSort={onSort} />
              <SortHeader label="Category"       field="category"       sortBy={sortBy} sortDir={sortDir} onSort={onSort} />
              <SortHeader label="Quantum"        field="quantum_status" sortBy={sortBy} sortDir={sortDir} onSort={onSort} />
              <th style={{ ...S.th, cursor: 'default' }}>Family</th>
              <SortHeader label="File"           field="file_path"      sortBy={sortBy} sortDir={sortDir} onSort={onSort} />
              <th style={{ ...S.th, cursor: 'default' }}>Line</th>
              <th style={{ ...S.th, cursor: 'default' }}>Key size</th>
              <SortHeader label="Confidence"     field="confidence"     sortBy={sortBy} sortDir={sortDir} onSort={onSort} />
            </tr>
          </thead>
          <tbody>
            {items.map((f, i) => (
              <tr
                key={f.id}
                onClick={() => navigate(`/inventory/${scanId}/finding/${f.id}`)}
                style={{
                  cursor: 'pointer',
                  background: i % 2 === 0 ? 'white' : '#fafafa',
                  transition: 'background 0.1s',
                }}
                onMouseEnter={e => (e.currentTarget.style.background = '#f0f4ff')}
                onMouseLeave={e => (e.currentTarget.style.background = i % 2 === 0 ? 'white' : '#fafafa')}
              >
                <td style={S.td}>
                  <span style={{ fontWeight: 600, fontSize: 13 }}>{f.algorithm}</span>
                  {f.usage_context && (
                    <div style={{ fontSize: 11, opacity: 0.45, marginTop: 1 }}>{f.usage_context}</div>
                  )}
                </td>
                <td style={S.td}>
                  <CategoryBadge category={f.category as FindingCategory} size="xs" />
                </td>
                <td style={S.td}>
                  <QuantumBadge status={f.quantum_status as QuantumStatus} size="xs" />
                </td>
                <td style={{ ...S.td, opacity: 0.55, fontFamily: 'monospace', fontSize: 12 }}>
                  {f.algorithm_family}
                </td>
                <td style={{ ...S.td, maxWidth: 200 }}>
                  <div
                    title={f.file_path}
                    style={{
                      fontSize: 12, fontFamily: 'monospace', overflow: 'hidden',
                      textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: 200,
                      opacity: 0.75,
                    }}
                  >
                    {f.file_path}
                  </div>
                </td>
                <td style={{ ...S.td, fontFamily: 'monospace', fontSize: 12, opacity: 0.55 }}>
                  {f.line_number ?? '—'}
                </td>
                <td style={{ ...S.td, fontFamily: 'monospace', fontSize: 12, opacity: 0.55 }}>
                  {f.key_size ? `${f.key_size}b` : '—'}
                </td>
                <td style={S.td}>
                  <ConfidenceBar value={f.confidence} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

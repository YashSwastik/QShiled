/**
 * ScansPage.tsx — Previous Scans
 *
 * Lists every scan (newest first) with key metadata. Per-scan actions:
 *   • Open Dashboard → /dashboard?scan_id=
 *   • View Reports   → /reports?scan_id=
 *   • Delete Scan    → confirmation dialog → DELETE /api/scans/{id}
 *
 * QRS (Quantum Readiness Score) is loaded lazily per completed scan from
 * GET /api/dashboard?scan_id= so we reuse existing backend logic without
 * duplicating computation.
 */
import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  LayoutDashboard, FileText, Trash2, RefreshCw,
  Clock, CheckCircle2, XCircle, Loader2, AlertTriangle,
  ChevronRight, Search,
} from 'lucide-react';
import AppSidebar from '../components/AppSidebar';
import {
  listDashboardScans,
  getDashboardSummary,
  deleteScan,
  type ScanOption,
} from '../services/dashboardApi';

// ── Design tokens ─────────────────────────────────────────────────────────────
const ACCENT  = '#7342E2';
const TEXT    = '#192837';
const MUTED   = 'rgba(25,40,55,0.50)';
const BORDER  = '1px solid rgba(25,40,55,0.09)';
const BG_PAGE = '#f5f4f1';
const BG_CARD = '#ffffff';
const C_CRIT  = '#ef4444';
const C_HIGH  = '#f97316';
const C_MOD   = '#eab308';
const C_LOW   = '#22c55e';

// ── Types ─────────────────────────────────────────────────────────────────────
interface ScanRow extends ScanOption {
  qrs?: number | null;        // null = not yet loaded, undefined = loading
  qrsLoading?: boolean;
  qrsError?: boolean;
}

// ── Helpers ───────────────────────────────────────────────────────────────────
function qrsColor(score: number): string {
  if (score >= 70) return C_LOW;
  if (score >= 50) return C_MOD;
  if (score >= 30) return C_HIGH;
  return C_CRIT;
}

function statusBadge(status: string) {
  const cfg: Record<string, { label: string; icon: React.ReactElement; color: string; bg: string }> = {
    completed: { label: 'Completed', icon: <CheckCircle2 size={12} />, color: C_LOW,  bg: '#dcfce7' },
    running:   { label: 'Running',   icon: <Loader2 size={12} className="animate-spin" />, color: '#3b82f6', bg: '#dbeafe' },
    queued:    { label: 'Queued',    icon: <Clock size={12} />,    color: MUTED.replace('0.50','0.70'), bg: '#f1f5f9' },
    failed:    { label: 'Failed',    icon: <XCircle size={12} />,  color: C_CRIT, bg: '#fee2e2' },
  };
  const c = cfg[status] ?? { label: status, icon: <Clock size={12} />, color: MUTED, bg: '#f1f5f9' };
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 4,
      fontSize: 11, fontWeight: 600, borderRadius: 20,
      padding: '3px 8px',
      background: c.bg, color: c.color,
    }}>
      {c.icon} {c.label}
    </span>
  );
}

function formatDate(iso: string | null): string {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleString(undefined, {
      year: 'numeric', month: 'short', day: 'numeric',
      hour: '2-digit', minute: '2-digit',
    });
  } catch { return iso; }
}

// ── Delete confirmation dialog ────────────────────────────────────────────────
interface DeleteDialogProps {
  scan: ScanRow;
  onCancel: () => void;
  onConfirm: () => void;
  deleting: boolean;
}

function DeleteDialog({ scan, onCancel, onConfirm, deleting }: DeleteDialogProps) {
  return (
    <div
      style={{
        position: 'fixed', inset: 0, zIndex: 100,
        background: 'rgba(25,40,55,0.45)', backdropFilter: 'blur(4px)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        padding: 24,
      }}
      onClick={onCancel}
    >
      <div
        style={{
          background: BG_CARD, borderRadius: 16,
          boxShadow: '0 24px 64px rgba(25,40,55,0.22)',
          padding: '32px 32px 28px',
          maxWidth: 460, width: '100%',
        }}
        onClick={e => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="delete-dialog-title"
      >
        {/* Icon */}
        <div style={{
          width: 48, height: 48, borderRadius: 12,
          background: '#fee2e2', display: 'flex', alignItems: 'center', justifyContent: 'center',
          marginBottom: 20,
        }}>
          <AlertTriangle size={22} color={C_CRIT} />
        </div>

        <h2 id="delete-dialog-title" style={{ fontSize: 18, fontWeight: 700, color: TEXT, margin: '0 0 8px' }}>
          Delete Scan?
        </h2>

        <p style={{ fontSize: 14, color: MUTED, margin: '0 0 6px', lineHeight: 1.6 }}>
          This will permanently remove:
        </p>
        <ul style={{ margin: '0 0 16px 16px', padding: 0, fontSize: 13, color: MUTED, lineHeight: 1.8 }}>
          <li>Scan "{scan.scan_name}"</li>
          <li>All cryptographic findings</li>
          <li>Inventory (CBOM)</li>
          <li>Risk analysis &amp; scores</li>
          <li>Recommendations &amp; Roadmap</li>
          <li>Generated reports</li>
        </ul>

        <p style={{ fontSize: 13, fontWeight: 600, color: C_CRIT, margin: '0 0 24px' }}>
          This action cannot be undone.
        </p>

        <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
          <button
            onClick={onCancel}
            disabled={deleting}
            style={{
              padding: '9px 20px', borderRadius: 8, border: BORDER,
              background: BG_PAGE, color: TEXT, fontSize: 14, fontWeight: 600,
              cursor: deleting ? 'not-allowed' : 'pointer', opacity: deleting ? 0.6 : 1,
            }}
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            disabled={deleting}
            style={{
              padding: '9px 20px', borderRadius: 8, border: 'none',
              background: C_CRIT, color: '#fff', fontSize: 14, fontWeight: 600,
              cursor: deleting ? 'not-allowed' : 'pointer',
              display: 'flex', alignItems: 'center', gap: 6,
              opacity: deleting ? 0.75 : 1,
            }}
          >
            {deleting && <Loader2 size={14} className="animate-spin" />}
            Delete
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────
export default function ScansPage() {
  const navigate = useNavigate();
  const [scans, setScans] = useState<ScanRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState<string | null>(null);
  const [search, setSearch]   = useState('');
  const [toDelete, setToDelete] = useState<ScanRow | null>(null);
  const [deleting, setDeleting] = useState(false);

  // ── Load scans ─────────────────────────────────────────────────────────────
  const loadScans = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const rows = await listDashboardScans();
      // Sort newest first (API already does this but guarantee it)
      const sorted = [...rows].sort((a, b) => {
        const da = a.completed_at ?? '';
        const db = b.completed_at ?? '';
        return db.localeCompare(da);
      });
      setScans(sorted.map(s => ({ ...s, qrs: null })));
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load scans');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadScans(); }, [loadScans]);

  // ── Lazy-load QRS for completed scans ──────────────────────────────────────
  useEffect(() => {
    scans.forEach((scan, idx) => {
      if (scan.status !== 'completed' || scan.qrs !== null || scan.qrsLoading) return;
      setScans(prev => {
        const copy = [...prev];
        copy[idx] = { ...copy[idx], qrsLoading: true };
        return copy;
      });
      getDashboardSummary(scan.scan_id)
        .then(dash => {
          setScans(prev => {
            const copy = [...prev];
            const i = copy.findIndex(s => s.scan_id === scan.scan_id);
            if (i !== -1) copy[i] = { ...copy[i], qrs: dash.quantum_readiness_score, qrsLoading: false };
            return copy;
          });
        })
        .catch(() => {
          setScans(prev => {
            const copy = [...prev];
            const i = copy.findIndex(s => s.scan_id === scan.scan_id);
            if (i !== -1) copy[i] = { ...copy[i], qrs: undefined, qrsLoading: false, qrsError: true };
            return copy;
          });
        });
    });
  }, [scans]);

  // ── Delete ─────────────────────────────────────────────────────────────────
  async function handleDelete() {
    if (!toDelete) return;
    setDeleting(true);
    try {
      await deleteScan(toDelete.scan_id);
      setScans(prev => prev.filter(s => s.scan_id !== toDelete.scan_id));
      setToDelete(null);
    } catch (e) {
      alert(e instanceof Error ? e.message : 'Delete failed');
    } finally {
      setDeleting(false);
    }
  }

  // ── Filter ─────────────────────────────────────────────────────────────────
  const filtered = scans.filter(s => {
    if (!search.trim()) return true;
    const q = search.toLowerCase();
    return (
      s.scan_name.toLowerCase().includes(q) ||
      s.application_name.toLowerCase().includes(q)
    );
  });

  // ── Render ─────────────────────────────────────────────────────────────────
  return (
    <div style={{ display: 'flex', minHeight: '100vh', background: BG_PAGE }}>
      <AppSidebar activeKey="scans" />

      <main style={{ flex: 1, padding: '32px 32px 48px', maxWidth: 1100, margin: '0 auto', width: '100%' }}>

        {/* ── Header ─────────────────────────────────────────────────────── */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 28, flexWrap: 'wrap', gap: 12 }}>
          <div>
            <h1 style={{ fontSize: 24, fontWeight: 700, color: TEXT, margin: 0, fontFamily: 'var(--font-heading)' }}>
              Previous Scans
            </h1>
            <p style={{ fontSize: 14, color: MUTED, margin: '4px 0 0' }}>
              All cryptography scans across your projects
            </p>
          </div>
          <div style={{ display: 'flex', gap: 10 }}>
            <button
              onClick={loadScans}
              title="Refresh"
              style={{
                display: 'flex', alignItems: 'center', gap: 6,
                padding: '8px 16px', borderRadius: 8, border: BORDER,
                background: BG_CARD, color: TEXT, fontSize: 13, fontWeight: 500,
                cursor: 'pointer',
              }}
            >
              <RefreshCw size={14} /> Refresh
            </button>
            <button
              onClick={() => navigate('/scan')}
              style={{
                display: 'flex', alignItems: 'center', gap: 6,
                padding: '8px 18px', borderRadius: 8, border: 'none',
                background: ACCENT, color: '#fff', fontSize: 13, fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              + New Scan
            </button>
          </div>
        </div>

        {/* ── Search ─────────────────────────────────────────────────────── */}
        <div style={{ position: 'relative', marginBottom: 20, maxWidth: 380 }}>
          <Search size={15} color={MUTED} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', pointerEvents: 'none' }} />
          <input
            type="search"
            placeholder="Search by scan or application name…"
            value={search}
            onChange={e => setSearch(e.target.value)}
            style={{
              width: '100%', padding: '9px 12px 9px 34px', borderRadius: 8,
              border: BORDER, background: BG_CARD, color: TEXT, fontSize: 13,
              outline: 'none', boxSizing: 'border-box',
            }}
          />
        </div>

        {/* ── States ─────────────────────────────────────────────────────── */}
        {loading && (
          <div style={{ textAlign: 'center', padding: '80px 0', color: MUTED }}>
            <Loader2 size={28} className="animate-spin" style={{ margin: '0 auto 12px', display: 'block' }} />
            <p style={{ margin: 0, fontSize: 14 }}>Loading scans…</p>
          </div>
        )}

        {!loading && error && (
          <div style={{
            padding: '24px', borderRadius: 12, background: '#fee2e2',
            border: '1px solid #fecaca', color: C_CRIT, textAlign: 'center',
          }}>
            <p style={{ margin: 0, fontWeight: 600 }}>{error}</p>
            <button onClick={loadScans} style={{ marginTop: 12, padding: '6px 16px', borderRadius: 6, border: 'none', background: C_CRIT, color: '#fff', cursor: 'pointer', fontSize: 13 }}>
              Retry
            </button>
          </div>
        )}

        {!loading && !error && filtered.length === 0 && (
          <div style={{
            display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
            padding: '80px 24px', textAlign: 'center',
          }}>
            <div style={{
              width: 64, height: 64, borderRadius: 16,
              background: `${ACCENT}15`,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              marginBottom: 20,
            }}>
              <Clock size={28} color={ACCENT} />
            </div>
            <h2 style={{ fontSize: 18, fontWeight: 700, color: TEXT, margin: '0 0 8px' }}>
              {search ? 'No matching scans' : 'No previous scans yet'}
            </h2>
            <p style={{ fontSize: 14, color: MUTED, margin: '0 0 24px', maxWidth: 320 }}>
              {search
                ? 'Try a different search term.'
                : 'Run your first scan to start discovering cryptographic usage across your codebase.'}
            </p>
            {!search && (
              <button
                onClick={() => navigate('/scan')}
                style={{
                  padding: '10px 24px', borderRadius: 8, border: 'none',
                  background: ACCENT, color: '#fff', fontSize: 14, fontWeight: 600,
                  cursor: 'pointer',
                }}
              >
                Start New Scan
              </button>
            )}
          </div>
        )}

        {/* ── Scan Cards ─────────────────────────────────────────────────── */}
        {!loading && !error && filtered.length > 0 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {filtered.map(scan => (
              <ScanCard
                key={scan.scan_id}
                scan={scan}
                onOpenDashboard={() => navigate(`/dashboard?scan_id=${scan.scan_id}`)}
                onViewReports={() => navigate(`/reports?scan_id=${scan.scan_id}`)}
                onDelete={() => setToDelete(scan)}
              />
            ))}
          </div>
        )}
      </main>

      {/* ── Delete dialog ───────────────────────────────────────────────── */}
      {toDelete && (
        <DeleteDialog
          scan={toDelete}
          onCancel={() => !deleting && setToDelete(null)}
          onConfirm={handleDelete}
          deleting={deleting}
        />
      )}
    </div>
  );
}

// ── ScanCard ──────────────────────────────────────────────────────────────────
interface ScanCardProps {
  scan: ScanRow;
  onOpenDashboard: () => void;
  onViewReports: () => void;
  onDelete: () => void;
}

function ScanCard({ scan, onOpenDashboard, onViewReports, onDelete }: ScanCardProps) {
  const isCompleted = scan.status === 'completed';

  return (
    <div
      style={{
        background: BG_CARD, borderRadius: 12,
        border: BORDER, padding: '18px 22px',
        display: 'flex', alignItems: 'center', gap: 16,
        flexWrap: 'wrap',
        boxShadow: '0 1px 4px rgba(25,40,55,0.05)',
        transition: 'box-shadow 0.15s',
      }}
      onMouseEnter={e => (e.currentTarget as HTMLElement).style.boxShadow = '0 4px 16px rgba(25,40,55,0.10)'}
      onMouseLeave={e => (e.currentTarget as HTMLElement).style.boxShadow = '0 1px 4px rgba(25,40,55,0.05)'}
    >
      {/* ── QRS ring ───────────────────────────────────────────────────── */}
      <div style={{
        width: 56, height: 56, borderRadius: '50%', flexShrink: 0,
        display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column',
        border: `3px solid ${isCompleted && scan.qrs != null ? qrsColor(scan.qrs) : 'rgba(25,40,55,0.12)'}`,
        background: `${isCompleted && scan.qrs != null ? qrsColor(scan.qrs) : 'rgba(25,40,55,0.06)'}18`,
      }}>
        {scan.qrsLoading ? (
          <Loader2 size={16} color={MUTED} className="animate-spin" />
        ) : scan.qrs != null ? (
          <>
            <span style={{ fontSize: 14, fontWeight: 800, color: qrsColor(scan.qrs), lineHeight: 1 }}>
              {scan.qrs}
            </span>
            <span style={{ fontSize: 9, color: MUTED, letterSpacing: 0.3, marginTop: 1 }}>QRS</span>
          </>
        ) : (
          <span style={{ fontSize: 9, color: MUTED, textAlign: 'center', lineHeight: 1.3 }}>
            {isCompleted ? '—' : '—'}
          </span>
        )}
      </div>

      {/* ── Main info ──────────────────────────────────────────────────── */}
      <div style={{ flex: 1, minWidth: 200 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap', marginBottom: 4 }}>
          <span style={{ fontSize: 15, fontWeight: 700, color: TEXT }}>{scan.scan_name}</span>
          {statusBadge(scan.status)}
        </div>
        <div style={{ fontSize: 12, color: MUTED, display: 'flex', flexWrap: 'wrap', gap: '0 16px' }}>
          <span>App: <strong style={{ color: TEXT }}>{scan.application_name}</strong></span>
          {scan.finding_count > 0 && (
            <span>Findings: <strong style={{ color: TEXT }}>{scan.finding_count}</strong></span>
          )}
          {scan.completed_at && (
            <span>Completed: <strong style={{ color: TEXT }}>{formatDate(scan.completed_at)}</strong></span>
          )}
        </div>
      </div>

      {/* ── Actions ────────────────────────────────────────────────────── */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexShrink: 0, flexWrap: 'wrap' }}>
        {isCompleted && (
          <>
            <ActionBtn
              icon={<LayoutDashboard size={13} />}
              label="Dashboard"
              onClick={onOpenDashboard}
              primary
            />
            <ActionBtn
              icon={<FileText size={13} />}
              label="Reports"
              onClick={onViewReports}
            />
          </>
        )}
        <button
          onClick={onDelete}
          title="Delete scan"
          style={{
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            width: 32, height: 32, borderRadius: 7, border: BORDER,
            background: 'transparent', cursor: 'pointer', color: MUTED,
            transition: 'all 0.15s',
          }}
          onMouseEnter={e => {
            (e.currentTarget as HTMLElement).style.background = '#fee2e2';
            (e.currentTarget as HTMLElement).style.color = C_CRIT;
            (e.currentTarget as HTMLElement).style.borderColor = '#fecaca';
          }}
          onMouseLeave={e => {
            (e.currentTarget as HTMLElement).style.background = 'transparent';
            (e.currentTarget as HTMLElement).style.color = MUTED;
            (e.currentTarget as HTMLElement).style.borderColor = 'rgba(25,40,55,0.09)';
          }}
        >
          <Trash2 size={14} />
        </button>
      </div>
    </div>
  );
}

function ActionBtn({ icon, label, onClick, primary }: { icon: React.ReactElement; label: string; onClick: () => void; primary?: boolean }) {
  return (
    <button
      onClick={onClick}
      style={{
        display: 'flex', alignItems: 'center', gap: 5,
        padding: '6px 12px', borderRadius: 7,
        border: primary ? 'none' : BORDER,
        background: primary ? ACCENT : BG_CARD,
        color: primary ? '#fff' : TEXT,
        fontSize: 12, fontWeight: 600, cursor: 'pointer',
        transition: 'opacity 0.15s',
      }}
      onMouseEnter={e => (e.currentTarget as HTMLElement).style.opacity = '0.8'}
      onMouseLeave={e => (e.currentTarget as HTMLElement).style.opacity = '1'}
    >
      {icon}
      {label}
      <ChevronRight size={11} />
    </button>
  );
}

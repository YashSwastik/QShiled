/**
 * AppSidebar — Shared collapsible application sidebar for all QShield app pages.
 *
 * TWO desktop states:
 *   EXPANDED (220px)  — logo, nav labels, active highlight
 *   COLLAPSED (48px)  — ONLY a hamburger button, NO nav icon rail
 *
 * Mobile: overlay drawer (full-width sheet from left, backdrop closes it)
 *
 * State persisted in localStorage key: "qshield_sidebar_open"
 *
 * Usage:
 *   <AppSidebar activeKey="risk" scanId={scanId} />
 *
 * activeKey values: dashboard | inventory | risk | migration | roadmap | pqclab | reports
 */
import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import {
  Home, BookOpen, BarChart2, Map, FlaskConical, FileText, Clock,
  Menu, X,
} from 'lucide-react';
import QShieldLogo from './QShieldLogo';

// ── Design tokens (match existing pages) ─────────────────────────────────────
const BORDER  = '1px solid rgba(25,40,55,0.09)';
const TEXT    = '#192837';
const MUTED   = 'rgba(25,40,55,0.45)';
const MUTED2  = 'rgba(25,40,55,0.30)';
const BG_SURF = '#ffffff';
const ACCENT  = '#7342E2';

const SIDEBAR_KEY = 'qshield_sidebar_open';
const SIDEBAR_WIDTH = 220;
const COLLAPSED_WIDTH = 48;

// ── Nav items factory ─────────────────────────────────────────────────────────
function buildNavItems(scanId?: string) {
  return [
    { key: 'dashboard',  label: 'Dashboard',        Icon: Home,         to: '/dashboard' },
    { key: 'inventory',  label: 'Crypto Inventory',  Icon: BookOpen,     to: scanId ? `/inventory/${scanId}` : '/upload', requiresScan: true },
    { key: 'risk',       label: 'Risk Analysis',     Icon: BarChart2,    to: scanId ? `/risk/${scanId}` : null, requiresScan: true },
    { key: 'migration',  label: 'Migration',         Icon: Map,          to: scanId ? `/recommendations/${scanId}` : null, requiresScan: true },
    { key: 'roadmap',    label: 'Roadmap',           Icon: Clock,        to: scanId ? `/roadmap/${scanId}` : null, requiresScan: true },
    { key: 'pqclab',     label: 'PQC Lab',           Icon: FlaskConical, to: '/demo' },
    { key: 'reports',    label: 'Reports',           Icon: FileText,     to: '/reports', requiresScan: false },
  ];
}

// ── Props ──────────────────────────────────────────────────────────────────
export interface AppSidebarProps {
  activeKey: string;
  scanId?: string;
}

// ── Component ─────────────────────────────────────────────────────────────────
export default function AppSidebar({ activeKey, scanId }: AppSidebarProps) {
  // Read stored preference; default open on desktop
  const [open, setOpen] = useState<boolean>(() => {
    try {
      const stored = localStorage.getItem(SIDEBAR_KEY);
      return stored === null ? true : stored === 'true';
    } catch {
      return true;
    }
  });

  // Mobile overlay state (always starts closed)
  const [mobileOpen, setMobileOpen] = useState(false);
  const [isMobile, setIsMobile] = useState(false);

  // Detect mobile
  useEffect(() => {
    const mq = window.matchMedia('(max-width: 768px)');
    setIsMobile(mq.matches);
    const handler = (e: MediaQueryListEvent) => setIsMobile(e.matches);
    mq.addEventListener('change', handler);
    return () => mq.removeEventListener('change', handler);
  }, []);

  // Persist preference
  const toggleOpen = useCallback(() => {
    setOpen(prev => {
      const next = !prev;
      try { localStorage.setItem(SIDEBAR_KEY, String(next)); } catch { /* */ }
      return next;
    });
  }, []);

  // Keyboard: Escape closes mobile overlay
  useEffect(() => {
    if (!mobileOpen) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setMobileOpen(false);
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [mobileOpen]);

  const navItems = buildNavItems(scanId);

  // ── Shared nav list ────────────────────────────────────────────────────────
  function NavList({ onNavigate }: { onNavigate?: () => void }) {
    return (
      <nav style={{ padding: '8px', flex: 1 }} aria-label="Application navigation">
        {navItems.map(({ key, label, Icon, to, requiresScan }) => {
          const isActive = key === activeKey;
          const disabled = !to;
          const disabledTitle = disabled
            ? requiresScan
              ? 'Select a scan first'
              : 'Not yet available'
            : undefined;

          if (disabled) {
            return (
              <div
                key={key}
                title={disabledTitle}
                style={{
                  display: 'flex', alignItems: 'center', gap: 10,
                  padding: '7px 12px', borderRadius: 7, marginBottom: 1,
                  fontSize: 13, fontWeight: 400,
                  color: MUTED2, cursor: 'default', userSelect: 'none',
                  opacity: 0.5,
                }}
              >
                <span style={{ color: MUTED2, flexShrink: 0 }}><Icon size={15} /></span>
                {label}
              </div>
            );
          }

          return (
            <Link
              key={key}
              to={to!}
              onClick={() => { onNavigate?.(); }}
              title={label}
              aria-current={isActive ? 'page' : undefined}
              style={{
                display: 'flex', alignItems: 'center', gap: 10,
                padding: '7px 12px', borderRadius: 7, marginBottom: 1,
                fontSize: 13, fontWeight: isActive ? 600 : 400,
                color: isActive ? ACCENT : TEXT,
                background: isActive ? `${ACCENT}10` : 'transparent',
                textDecoration: 'none',
                transition: 'background 0.1s',
              }}
              onMouseEnter={e => { if (!isActive) (e.currentTarget as HTMLElement).style.background = 'rgba(25,40,55,0.04)'; }}
              onMouseLeave={e => { if (!isActive) (e.currentTarget as HTMLElement).style.background = 'transparent'; }}
            >
              <span style={{ color: isActive ? ACCENT : MUTED, flexShrink: 0 }}><Icon size={15} /></span>
              {label}
            </Link>
          );
        })}
      </nav>
    );
  }

  // ── Mobile overlay ─────────────────────────────────────────────────────────
  if (isMobile) {
    return (
      <>
        {/* Mobile: floating hamburger button */}
        <button
          onClick={() => setMobileOpen(v => !v)}
          aria-label={mobileOpen ? 'Close navigation' : 'Open navigation'}
          aria-expanded={mobileOpen}
          style={{
            position: 'fixed', top: 12, left: 12, zIndex: 50,
            width: 40, height: 40, borderRadius: 8,
            background: BG_SURF, border: BORDER,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            cursor: 'pointer', boxShadow: '0 2px 8px rgba(25,40,55,0.12)',
          }}
        >
          {mobileOpen ? <X size={18} color={TEXT} /> : <Menu size={18} color={TEXT} />}
        </button>

        {/* Backdrop */}
        {mobileOpen && (
          <div
            onClick={() => setMobileOpen(false)}
            aria-hidden="true"
            style={{
              position: 'fixed', inset: 0, zIndex: 40,
              background: 'rgba(25,40,55,0.40)',
              backdropFilter: 'blur(3px)',
            }}
          />
        )}

        {/* Drawer */}
        <aside
          aria-label="Navigation menu"
          role="navigation"
          style={{
            position: 'fixed', top: 0, left: 0, bottom: 0, zIndex: 45,
            width: SIDEBAR_WIDTH, background: BG_SURF, borderRight: BORDER,
            display: 'flex', flexDirection: 'column',
            transform: mobileOpen ? 'translateX(0)' : 'translateX(-100%)',
            transition: 'transform 0.25s ease',
            boxShadow: mobileOpen ? '4px 0 24px rgba(25,40,55,0.14)' : 'none',
          }}
        >
          {/* Brand + close */}
          <div style={{ padding: '14px 16px', borderBottom: BORDER, display: 'flex', alignItems: 'center', gap: 10, justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <QShieldLogo size={18} color={TEXT} />
              <span style={{ fontSize: 14, fontWeight: 700, fontFamily: 'var(--font-heading)', color: TEXT }}>QShield</span>
            </div>
            <button
              onClick={() => setMobileOpen(false)}
              aria-label="Close navigation"
              style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 4, display: 'flex' }}
            >
              <X size={16} color={MUTED} />
            </button>
          </div>
          <NavList onNavigate={() => setMobileOpen(false)} />
          <div style={{ padding: '12px 16px', borderTop: BORDER }}>
            <span style={{ fontSize: 10, color: MUTED2 }}>QShield · {activeKey}</span>
          </div>
        </aside>
      </>
    );
  }

  // ── Desktop sidebar ────────────────────────────────────────────────────────
  const width = open ? SIDEBAR_WIDTH : COLLAPSED_WIDTH;

  return (
    <aside
      aria-label="Application sidebar"
      role="navigation"
      style={{
        width, flexShrink: 0,
        background: BG_SURF, borderRight: BORDER,
        display: 'flex', flexDirection: 'column',
        minHeight: '100vh',
        position: 'sticky', top: 0, alignSelf: 'flex-start',
        transition: 'width 0.22s ease',
        overflow: 'hidden',
      }}
    >
      {/* Brand header */}
      <div style={{
        padding: open ? '14px 16px' : '14px 0',
        borderBottom: BORDER,
        display: 'flex', alignItems: 'center',
        justifyContent: open ? 'space-between' : 'center',
        gap: 8, flexShrink: 0,
        minHeight: 52,
      }}>
        {open && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, overflow: 'hidden' }}>
            <QShieldLogo size={18} color={TEXT} />
            <span style={{ fontSize: 14, fontWeight: 700, fontFamily: 'var(--font-heading)', color: TEXT, whiteSpace: 'nowrap' }}>
              QShield
            </span>
          </div>
        )}
        {/* Hamburger toggle */}
        <button
          onClick={toggleOpen}
          aria-label={open ? 'Close navigation' : 'Open navigation'}
          aria-expanded={open}
          style={{
            background: 'none', border: 'none', cursor: 'pointer',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            width: 28, height: 28, borderRadius: 6, flexShrink: 0,
            color: MUTED,
            transition: 'background 0.1s',
          }}
          onMouseEnter={e => (e.currentTarget as HTMLElement).style.background = 'rgba(25,40,55,0.06)'}
          onMouseLeave={e => (e.currentTarget as HTMLElement).style.background = 'none'}
        >
          <Menu size={16} />
        </button>
      </div>

      {/* Navigation — only visible when expanded */}
      {open && (
        <>
          <NavList />
          <div style={{ padding: '12px 16px', borderTop: BORDER, flexShrink: 0 }}>
            <span style={{ fontSize: 10, color: MUTED2 }}>QShield · {activeKey}</span>
          </div>
        </>
      )}

      {/* Collapsed: only the hamburger — no nav icons */}
    </aside>
  );
}

/**
 * Navbar.tsx — QShield landing-page top navigation.
 *
 * Simplified: logo only on the left, single "Start New Scan" CTA removed.
 * The landing page hero already has the primary CTA.
 * Mobile: hamburger → slide-in sheet with only Start New Scan action.
 */
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { AnimatePresence, motion } from 'framer-motion';
import { Menu, X } from 'lucide-react';
import QShieldLogo from './QShieldLogo';

const TEXT   = 'var(--color-text)';
const ACCENT = 'var(--color-accent)';

export default function Navbar() {
  const [menuOpen, setMenuOpen] = useState(false);
  const navigate = useNavigate();

  // Lock body scroll when mobile menu is open
  useEffect(() => {
    document.body.classList.toggle('menu-open', menuOpen);
    return () => document.body.classList.remove('menu-open');
  }, [menuOpen]);

  return (
    <>
      {/* ── Bar ───────────────────────────────────────────────────────────── */}
      <nav className="relative z-10 w-full" aria-label="Primary navigation">
        <div
          className="mx-auto flex items-center justify-between px-5 py-4 sm:px-8 sm:py-5"
          style={{ maxWidth: 1280 }}
        >
          {/* Logo + wordmark */}
          <button
            onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
            className="flex items-center gap-2.5 shrink-0 cursor-pointer border-0 bg-transparent"
            aria-label="QShield — scroll to top"
          >
            <QShieldLogo size={28} color="#192837" />
            <span
              className="text-lg tracking-tight select-none"
              style={{ color: TEXT, fontFamily: 'var(--font-heading)' }}
            >
              QShield
            </span>
          </button>

          {/* Mobile hamburger */}
          <button
            className="md:hidden flex items-center justify-center w-10 h-10 rounded-xl transition-colors hover:bg-black/5 border-0 bg-transparent cursor-pointer"
            onClick={() => setMenuOpen((v) => !v)}
            aria-label={menuOpen ? 'Close menu' : 'Open menu'}
            aria-expanded={menuOpen}
          >
            {menuOpen
              ? <X size={24} color={TEXT} />
              : <Menu size={24} color={TEXT} />
            }
          </button>
        </div>
      </nav>

      {/* ── Mobile Menu ────────────────────────────────────────────────────── */}
      <AnimatePresence>
        {menuOpen && (
          <>
            {/* Backdrop */}
            <motion.div
              key="backdrop"
              initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              transition={{ duration: 0.3, ease: 'easeOut' }}
              className="fixed inset-0 z-20"
              style={{ background: 'rgba(25,40,55,0.35)', backdropFilter: 'blur(4px)' }}
              onClick={() => setMenuOpen(false)}
              aria-hidden="true"
            />
            {/* Sheet */}
            <motion.aside
              key="sheet"
              initial={{ x: '100%' }} animate={{ x: 0 }} exit={{ x: '100%' }}
              transition={{ duration: 0.35, ease: 'easeOut' }}
              className="fixed top-0 right-0 z-30 flex flex-col overflow-y-auto"
              style={{
                width: 'min(88vw, 320px)', height: '100dvh',
                background: '#CFC8C5',
                boxShadow: '-12px 0 48px rgba(25,40,55,0.18)',
              }}
              aria-label="Mobile navigation"
            >
              {/* Sheet header */}
              <div className="flex items-center justify-between px-6 py-5">
                <div className="flex items-center gap-2.5">
                  <QShieldLogo size={22} color="#192837" />
                  <span className="text-base tracking-tight" style={{ color: TEXT, fontFamily: 'var(--font-heading)' }}>
                    QShield
                  </span>
                </div>
                <button
                  onClick={() => setMenuOpen(false)}
                  className="flex items-center justify-center rounded-full border-0 cursor-pointer"
                  style={{ width: 36, height: 36, background: 'rgba(25,40,55,0.10)' }}
                  aria-label="Close menu"
                >
                  <X size={18} color={TEXT} />
                </button>
              </div>

              <div className="mx-6" style={{ height: 1, background: 'rgba(25,40,55,0.12)' }} />

              <div className="flex-1" />

              <div className="flex flex-col gap-3 px-6 pb-8 pt-4">
                <button
                  onClick={() => { setMenuOpen(false); navigate('/scan'); }}
                  className="w-full rounded-full text-white font-semibold border-0 cursor-pointer transition-all active:scale-95"
                  style={{ background: ACCENT, fontSize: '0.95rem', paddingTop: '0.875rem', paddingBottom: '0.875rem' }}
                >
                  Start New Scan
                </button>
                <button
                  onClick={() => { setMenuOpen(false); navigate('/scans'); }}
                  className="w-full rounded-full font-semibold border-0 cursor-pointer transition-all active:scale-95"
                  style={{ background: 'var(--color-login-bg)', color: TEXT, fontSize: '0.95rem', paddingTop: '0.875rem', paddingBottom: '0.875rem' }}
                >
                  Previous Scans
                </button>
              </div>
            </motion.aside>
          </>
        )}
      </AnimatePresence>
    </>
  );
}

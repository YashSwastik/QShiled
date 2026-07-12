import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { AnimatePresence, motion } from 'framer-motion';
import { Menu, X } from 'lucide-react';
import QShieldLogo from './QShieldLogo';

const NAV_LINKS = [
  { label: 'Platform', href: '#platform' },
  { label: 'Discovery', href: '#discovery' },
  { label: 'Migration', href: '#migration' },
  { label: 'PQC Lab', href: '#pqc-lab' },
  { label: 'About', href: '#about' },
];

export default function Navbar() {
  const [menuOpen, setMenuOpen] = useState(false);
  const navigate = useNavigate();

  // Lock body scroll when mobile menu is open
  useEffect(() => {
    if (menuOpen) {
      document.body.classList.add('menu-open');
    } else {
      document.body.classList.remove('menu-open');
    }
    return () => document.body.classList.remove('menu-open');
  }, [menuOpen]);

  function handleLaunch() {
    setMenuOpen(false);
    navigate('/app/dashboard');
  }

  function handleDemo() {
    setMenuOpen(false);
    navigate('/demo');
  }

  return (
    <>
      {/* ── Desktop / Mobile Bar ─────────────────────────────────────────── */}
      <nav className="relative z-10 w-full" aria-label="Primary navigation">
        <div
          className="mx-auto flex items-center justify-between px-5 py-4 sm:px-8 sm:py-5"
          style={{ maxWidth: 1280 }}
        >
          {/* Logo + wordmark */}
          <Link
            to="/"
            className="flex items-center gap-2.5 shrink-0 no-underline"
            aria-label="QShield home"
          >
            <QShieldLogo size={28} color="#192837" />
            <span
              className="text-lg tracking-tight select-none"
              style={{ color: 'var(--color-text)', fontFamily: 'var(--font-heading)' }}
            >
              QShield
            </span>
          </Link>

          {/* Desktop centre nav links */}
          <ul className="hidden md:flex items-center gap-8 list-none m-0 p-0">
            {NAV_LINKS.map((link) => (
              <li key={link.label}>
                <a
                  href={link.href}
                  className="text-sm font-medium transition-opacity hover:opacity-60 no-underline"
                  style={{ color: 'var(--color-text)' }}
                >
                  {link.label}
                </a>
              </li>
            ))}
          </ul>

          {/* Desktop CTAs */}
          <div className="hidden md:flex items-center gap-3">
            <button
              onClick={handleDemo}
              className="text-sm font-semibold px-5 py-2.5 rounded-full transition-all active:scale-95 cursor-pointer border-0"
              style={{ background: 'var(--color-login-bg)', color: 'var(--color-text)' }}
            >
              View Demo
            </button>
            <button
              onClick={handleLaunch}
              className="text-sm font-semibold px-5 py-2.5 rounded-full text-white transition-all hover:shadow-lg active:scale-95 cursor-pointer border-0"
              style={{ background: 'var(--color-accent)' }}
            >
              Launch QShield
            </button>
          </div>

          {/* Mobile hamburger */}
          <button
            className="md:hidden flex items-center justify-center w-10 h-10 rounded-xl transition-colors hover:bg-black/5 border-0 bg-transparent cursor-pointer"
            onClick={() => setMenuOpen((v) => !v)}
            aria-label={menuOpen ? 'Close menu' : 'Open menu'}
            aria-expanded={menuOpen}
          >
            {menuOpen
              ? <X size={24} color="var(--color-text)" />
              : <Menu size={24} color="var(--color-text)" />
            }
          </button>
        </div>
      </nav>

      {/* ── Mobile Menu (AnimatePresence) ────────────────────────────────── */}
      <AnimatePresence>
        {menuOpen && (
          <>
            {/* Backdrop */}
            <motion.div
              key="backdrop"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.3, ease: 'easeOut' }}
              className="fixed inset-0 z-20"
              style={{
                background: 'rgba(25,40,55,0.35)',
                backdropFilter: 'blur(4px)',
                WebkitBackdropFilter: 'blur(4px)',
              }}
              onClick={() => setMenuOpen(false)}
              aria-hidden="true"
            />

            {/* Sheet */}
            <motion.aside
              key="sheet"
              initial={{ x: '100%' }}
              animate={{ x: 0 }}
              exit={{ x: '100%' }}
              transition={{ duration: 0.45, ease: 'easeOut' }}
              className="fixed top-0 right-0 z-30 flex flex-col overflow-y-auto"
              style={{
                width: 'min(88vw, 360px)',
                height: '100dvh',
                background: '#CFC8C5',
                boxShadow: '-12px 0 48px rgba(25,40,55,0.18)',
              }}
              aria-label="Mobile navigation"
            >
              {/* Sheet header */}
              <div className="flex items-center justify-between px-6 py-5">
                <Link
                  to="/"
                  className="flex items-center gap-2.5 no-underline"
                  onClick={() => setMenuOpen(false)}
                  aria-label="QShield home"
                >
                  <QShieldLogo size={26} color="#192837" />
                  <span
                    className="text-base tracking-tight"
                    style={{ color: 'var(--color-text)', fontFamily: 'var(--font-heading)' }}
                  >
                    QShield
                  </span>
                </Link>

                <motion.button
                  whileTap={{ scale: 0.9 }}
                  onClick={() => setMenuOpen(false)}
                  className="flex items-center justify-center rounded-full border-0 cursor-pointer"
                  style={{
                    width: 40,
                    height: 40,
                    background: 'rgba(25,40,55,0.10)',
                  }}
                  aria-label="Close menu"
                >
                  <X size={20} color="var(--color-text)" />
                </motion.button>
              </div>

              {/* Divider */}
              <div
                className="mx-6"
                style={{ height: 1, background: 'rgba(25,40,55,0.12)' }}
              />

              {/* Nav links — staggered entrance */}
              <nav className="flex flex-col gap-1 px-4 pt-4">
                {NAV_LINKS.map((link, i) => (
                  <motion.a
                    key={link.label}
                    href={link.href}
                    initial={{ opacity: 0, x: 24 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{
                      delay: 0.18 + i * 0.07,
                      duration: 0.4,
                      ease: 'easeOut',
                    }}
                    className="rounded-xl px-4 py-3 no-underline transition-colors hover:bg-black/10"
                    style={{ color: 'var(--color-text)', fontSize: '1.1rem', fontWeight: 500 }}
                    onClick={() => setMenuOpen(false)}
                  >
                    {link.label}
                  </motion.a>
                ))}
              </nav>

              {/* Spacer */}
              <div className="flex-1" />

              {/* Mobile CTAs */}
              <div className="flex flex-col gap-3 px-6 pb-8 pt-4">
                <button
                  onClick={handleLaunch}
                  className="w-full rounded-full text-white font-semibold border-0 cursor-pointer transition-all active:scale-95"
                  style={{
                    background: 'var(--color-accent)',
                    fontSize: '0.95rem',
                    paddingTop: '0.875rem',
                    paddingBottom: '0.875rem',
                  }}
                >
                  Launch QShield
                </button>
                <button
                  onClick={handleDemo}
                  className="w-full rounded-full font-semibold border-0 cursor-pointer transition-all active:scale-95"
                  style={{
                    background: 'var(--color-login-bg)',
                    color: 'var(--color-text)',
                    fontSize: '0.95rem',
                    paddingTop: '0.875rem',
                    paddingBottom: '0.875rem',
                  }}
                >
                  View Demo
                </button>
              </div>
            </motion.aside>
          </>
        )}
      </AnimatePresence>
    </>
  );
}

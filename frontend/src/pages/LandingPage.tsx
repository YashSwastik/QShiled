/**
 * LandingPage.tsx — QShield landing experience
 *
 * Sections:
 *   1. HERO           — preserved video bg, grid overlay, headline, CTAs
 *   2. HOW IT WORKS   — 6 real implemented workflow steps
 *   3. PREVIOUS SCANS — real data from /api/dashboard/scans
 *   4. ABOUT          — technically accurate product description
 *
 * Preserves existing video background, hero-grid-overlay, hero-vignette,
 * motion fade-up animations, and enterprise visual identity.
 *
 * Route: /
 */
import { useEffect, useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, useReducedMotion, type Variants } from 'framer-motion';
import {
  ScanSearch, ShieldCheck, ArrowRightCircle, RefreshCw,
  AlertCircle, ChevronRight, ExternalLink,
} from 'lucide-react';
import { listDashboardScans } from '../services/dashboardApi';
import type { ScanOption } from '../services/dashboardApi';

const VIDEO_URL =
  'https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260606_131516_eca35265-ea66-4fbd-8d52-22aae6e1a503.mp4';

// ── Design tokens ─────────────────────────────────────────────────────────────
const TEXT   = '#192837';
const ACCENT = '#7342E2';
const MUTED  = 'rgba(25,40,55,0.50)';
const MUTED2 = 'rgba(25,40,55,0.30)';
const BG     = '#F2F2EE';
const SURF   = '#ffffff';
const BORDER = '1px solid rgba(25,40,55,0.09)';

// ── Animation helpers ─────────────────────────────────────────────────────────
function makeFadeUp(i: number): Variants {
  return {
    hidden: { opacity: 0, y: 28 },
    visible: {
      opacity: 1, y: 0,
      transition: { delay: i * 0.15, duration: 0.6, ease: 'easeOut' },
    },
  };
}

function makeFadeIn(delay = 0): Variants {
  return {
    hidden: { opacity: 0, y: 16 },
    visible: { opacity: 1, y: 0, transition: { delay, duration: 0.5, ease: 'easeOut' } },
  };
}

// ── Workflow steps (actual implemented features only) ─────────────────────────
const WORKFLOW_STEPS = [
  {
    num: '01', title: 'Discover',
    desc: 'Scan supported source code, configuration files, X.509 certificates, and cryptographic assets to surface every classical cryptographic dependency.',
  },
  {
    num: '02', title: 'Inventory',
    desc: 'Build structured, machine-readable visibility into detected cryptographic usage — a CBOM-style asset register with file-level provenance.',
  },
  {
    num: '03', title: 'Assess',
    desc: 'Calculate deterministic quantum-migration risk using algorithm type, key size, exposure, business criticality, and application context. No AI or LLM scoring.',
  },
  {
    num: '04', title: 'Recommend',
    desc: 'Generate purpose-aware migration guidance using deterministic rules and the curated migration knowledge base — not generic "replace RSA with ML-KEM" blanket advice.',
  },
  {
    num: '05', title: 'Plan',
    desc: 'Prioritize migration work into deterministic roadmap waves and lifecycle stages with persistent tracking across sessions.',
  },
  {
    num: '06', title: 'Validate',
    desc: 'Experiment with genuinely supported post-quantum cryptographic operations — ML-KEM and ML-DSA — in the PQC Lab. All operations are real, not simulated.',
  },
];

// ── Status badge ─────────────────────────────────────────────────────────────
function StatusBadge({ status }: { status: string }) {
  const s = status.toLowerCase();
  const cfg =
    s === 'completed' ? { bg: '#f0fdf4', text: '#15803d', border: '#bbf7d0' } :
    s === 'running'   ? { bg: '#eff6ff', text: '#1e40af', border: '#bfdbfe' } :
    s === 'failed'    ? { bg: '#fef2f2', text: '#b91c1c', border: '#fecaca' } :
                        { bg: '#f9fafb', text: '#374151', border: '#e5e7eb' };
  return (
    <span style={{
      fontSize: 10, fontWeight: 700, padding: '2px 8px', borderRadius: 20,
      background: cfg.bg, color: cfg.text, border: `1px solid ${cfg.border}`,
      textTransform: 'uppercase', letterSpacing: '0.05em',
    }}>
      {status}
    </span>
  );
}

// ── Section heading ───────────────────────────────────────────────────────────
function SectionHeading({ children }: { children: React.ReactNode }) {
  return (
    <h2 style={{
      margin: 0, fontFamily: 'var(--font-heading)',
      fontSize: 'clamp(1.4rem, 3vw, 2rem)',
      fontWeight: 700, color: TEXT, lineHeight: 1.15, letterSpacing: '-0.01em',
    }}>
      {children}
    </h2>
  );
}

// ── Main component ─────────────────────────────────────────────────────────────
export default function LandingPage() {
  const navigate = useNavigate();
  const prefersReducedMotion = useReducedMotion();

  // Previous scans state
  const [scans, setScans] = useState<ScanOption[]>([]);
  const [scansLoading, setScansLoading] = useState(true);
  const [scansError, setScansError] = useState<string | null>(null);

  const previousScansRef = useRef<HTMLElement>(null);

  function motionProps(i: number) {
    if (prefersReducedMotion) return {};
    return { initial: 'hidden' as const, whileInView: 'visible' as const, viewport: { once: true }, variants: makeFadeUp(i) };
  }

  function fetchScans() {
    setScansLoading(true);
    setScansError(null);
    listDashboardScans()
      .then(data => setScans(data))
      .catch(e => setScansError(e.message ?? 'Failed to load scans.'))
      .finally(() => setScansLoading(false));
  }

  useEffect(() => { fetchScans(); }, []);

  // Format date
  function fmtDate(iso: string | null): string {
    if (!iso) return '—';
    try {
      return new Date(iso).toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' });
    } catch { return '—'; }
  }

  return (
    <div style={{ minHeight: '100dvh', background: BG, color: TEXT, fontFamily: 'var(--font-body)' }}>

      {/* ══════════════════════════════════════════════════════
          1. HERO — VIDEO BACKGROUND (preserved)
         ══════════════════════════════════════════════════════ */}
      <section
        aria-label="QShield hero"
        style={{ position: 'relative', minHeight: '100dvh', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}
      >
        {/* Background Video */}
        <video
          autoPlay muted loop playsInline
          style={{ position: 'absolute', inset: 0, zIndex: 0, width: '100%', height: '100%', objectFit: 'cover' }}
          aria-hidden="true"
        >
          <source src={VIDEO_URL} type="video/mp4" />
        </video>

        {/* Overlays */}
        <div className="absolute inset-0 hero-grid-overlay pointer-events-none" style={{ zIndex: 1 }} aria-hidden="true" />
        <div className="absolute inset-0 hero-vignette pointer-events-none" style={{ zIndex: 2 }} aria-hidden="true" />

        {/* Hero content */}
        <div
          style={{
            position: 'relative', zIndex: 10,
            display: 'flex', flexDirection: 'column', alignItems: 'center',
            justifyContent: 'center', flex: 1,
            padding: 'clamp(40px, 8vw, 72px) 20px 64px',
            textAlign: 'center',
          }}
        >
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 28, maxWidth: 760 }}>

            {/* Heading */}
            <motion.h1
              {...motionProps(0)}
              style={{
                margin: 0, fontFamily: 'var(--font-heading)',
                fontSize: 'clamp(1.65rem, 5vw, 3rem)',
                lineHeight: 1.05, letterSpacing: '-0.01em',
                color: 'var(--color-text)',
              }}
            >
              Discover{' '}
              <ScanSearch size={28} strokeWidth={2} className="inline-block align-middle" style={{ top: -2, margin: '0 4px', color: 'var(--color-text)', position: 'relative' }} aria-hidden="true" />{' '}
              Your Cryptographic Exposure
              <br />
              Before the Quantum Era{' '}
              <ShieldCheck size={28} strokeWidth={2} className="inline-block align-middle" style={{ top: -2, margin: '0 4px', color: 'var(--color-text)', position: 'relative' }} aria-hidden="true" />{' '}
              Does
            </motion.h1>

            {/* Subtext */}
            <motion.p
              {...motionProps(1)}
              style={{
                margin: 0, fontFamily: 'var(--font-body)',
                fontSize: 'clamp(0.9rem, 2.5vw, 1.1rem)',
                lineHeight: 1.65, opacity: 0.8, color: 'var(--color-text)', maxWidth: 600,
              }}
            >
              Discover cryptographic dependencies, assess quantum-migration risk, and build a
              clear path toward post-quantum readiness — using real deterministic analysis, not guesswork.
            </motion.p>

            {/* CTA buttons */}
            <motion.div {...motionProps(2)} style={{ display: 'flex', gap: 14, flexWrap: 'wrap', justifyContent: 'center' }}>
              <motion.button
                onClick={() => navigate('/scan')}
                whileHover={{ scale: 1.04, filter: 'brightness(1.08)' }}
                whileTap={{ scale: 0.96 }}
                style={{
                  display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 10,
                  background: ACCENT, color: '#fff', border: 'none',
                  borderRadius: 50, fontSize: 'clamp(0.9rem, 2vw, 1rem)', fontWeight: 600,
                  padding: '15px 24px', minWidth: 200, cursor: 'pointer',
                  boxShadow: '0 4px 24px rgba(115,66,226,0.28)',
                }}
                aria-label="Start a new cryptographic scan"
              >
                <span>Start New Scan</span>
                <ArrowRightCircle size={20} strokeWidth={2} aria-hidden="true" />
              </motion.button>

              <motion.button
                onClick={() => { const el = document.getElementById('previous-scans'); el?.scrollIntoView({ behavior: 'smooth' }); }}
                whileHover={{ scale: 1.04 }}
                whileTap={{ scale: 0.96 }}
                style={{
                  display: 'flex', alignItems: 'center', gap: 8,
                  background: 'rgba(242,242,238,0.85)', color: TEXT, border: 'none',
                  borderRadius: 50, fontSize: 'clamp(0.9rem, 2vw, 1rem)', fontWeight: 600,
                  padding: '15px 24px', cursor: 'pointer',
                  backdropFilter: 'blur(4px)',
                }}
                aria-label="View previous scans"
              >
                <span>View Previous Scans</span>
              </motion.button>
            </motion.div>

            {/* Trust line */}
            <motion.p
              {...motionProps(3)}
              style={{
                margin: 0, fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.06em',
                color: 'var(--color-text)', opacity: 0.4,
              }}
            >
              Standards-aware migration guidance&nbsp;•&nbsp;Explainable risk&nbsp;•&nbsp;Real cryptographic discovery
            </motion.p>
          </div>
        </div>
      </section>

      {/* ══════════════════════════════════════════════════════
          2. HOW QSHIELD WORKS
         ══════════════════════════════════════════════════════ */}
      <section
        id="how-it-works"
        aria-labelledby="how-it-works-heading"
        style={{ padding: 'clamp(60px, 8vw, 96px) clamp(20px, 5vw, 60px)' }}
      >
        <div style={{ maxWidth: 1100, margin: '0 auto' }}>
          <motion.div
            initial={prefersReducedMotion ? undefined : 'hidden'}
            whileInView="visible"
            viewport={{ once: true }}
            variants={makeFadeIn(0)}
            style={{ marginBottom: 48, textAlign: 'center' }}
          >
            <div style={{ fontSize: 11, fontWeight: 700, color: ACCENT, textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 10 }}>
              The Workflow
            </div>
            <SectionHeading>
              <span id="how-it-works-heading">How QShield Works</span>
            </SectionHeading>
            <p style={{ margin: '12px auto 0', fontSize: 15, color: MUTED, maxWidth: 540, lineHeight: 1.6 }}>
              Six connected stages based on actually implemented capabilities — no simulated steps.
            </p>
          </motion.div>

          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
            gap: 20,
          }}>
            {WORKFLOW_STEPS.map((step, i) => (
              <motion.div
                key={step.num}
                initial={prefersReducedMotion ? undefined : 'hidden'}
                whileInView="visible"
                viewport={{ once: true }}
                variants={makeFadeIn(i * 0.08)}
                style={{
                  background: SURF, border: BORDER, borderRadius: 14,
                  padding: '24px 22px', position: 'relative', overflow: 'hidden',
                }}
              >
                <div style={{
                  fontSize: 36, fontWeight: 900, color: `${ACCENT}12`,
                  fontFamily: 'var(--font-heading)', lineHeight: 1,
                  position: 'absolute', top: 12, right: 16,
                  userSelect: 'none', letterSpacing: '-0.03em',
                }}>
                  {step.num}
                </div>
                <div style={{
                  display: 'inline-block', fontSize: 11, fontWeight: 700, color: ACCENT,
                  background: `${ACCENT}10`, borderRadius: 6, padding: '2px 8px',
                  textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: 10,
                }}>
                  {step.num}
                </div>
                <div style={{ fontSize: 16, fontWeight: 700, color: TEXT, fontFamily: 'var(--font-heading)', marginBottom: 8 }}>
                  {step.title}
                </div>
                <div style={{ fontSize: 13, color: MUTED, lineHeight: 1.65 }}>
                  {step.desc}
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ══════════════════════════════════════════════════════
          3. PREVIOUS SCANS
         ══════════════════════════════════════════════════════ */}
      <section
        id="previous-scans"
        ref={previousScansRef as React.RefObject<HTMLElement>}
        aria-labelledby="previous-scans-heading"
        style={{ padding: 'clamp(60px, 8vw, 96px) clamp(20px, 5vw, 60px)', background: SURF }}
      >
        <div style={{ maxWidth: 1100, margin: '0 auto' }}>
          <motion.div
            initial={prefersReducedMotion ? undefined : 'hidden'}
            whileInView="visible"
            viewport={{ once: true }}
            variants={makeFadeIn(0)}
            style={{ marginBottom: 40 }}
          >
            <div style={{ fontSize: 11, fontWeight: 700, color: ACCENT, textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 10 }}>
              Recent Work
            </div>
            <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', flexWrap: 'wrap', gap: 16 }}>
              <SectionHeading>
                <span id="previous-scans-heading">Previous Scans</span>
              </SectionHeading>
              <button
                onClick={() => navigate('/dashboard')}
                style={{
                  display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, fontWeight: 600,
                  color: ACCENT, background: 'none', border: 'none', cursor: 'pointer', padding: 0,
                }}
              >
                Open Dashboard <ExternalLink size={13} />
              </button>
            </div>
            <p style={{ margin: '10px 0 0', fontSize: 14, color: MUTED, lineHeight: 1.6 }}>
              Reopen an existing scan to continue where you left off.
            </p>
          </motion.div>

          {/* Loading skeleton */}
          {scansLoading && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {[1, 2, 3].map(i => (
                <div key={i} style={{
                  height: 68, borderRadius: 12, background: '#f0f0ec',
                  animation: 'shimmer 1.4s ease-in-out infinite',
                  backgroundImage: 'linear-gradient(90deg, #f0f0ec 25%, #e8e8e4 50%, #f0f0ec 75%)',
                  backgroundSize: '200% 100%',
                }} />
              ))}
              <style>{`@keyframes shimmer { 0%{background-position:200% 0} 100%{background-position:-200% 0} }`}</style>
            </div>
          )}

          {/* Error */}
          {scansError && !scansLoading && (
            <div style={{
              background: '#fef2f2', border: '1px solid #fecaca', borderRadius: 12,
              padding: '20px 24px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12,
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <AlertCircle size={18} style={{ color: '#ef4444', flexShrink: 0 }} />
                <span style={{ fontSize: 13, color: '#b91c1c' }}>{scansError}</span>
              </div>
              <button
                onClick={fetchScans}
                style={{
                  display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, fontWeight: 600,
                  color: '#b91c1c', background: 'none', border: '1px solid #fecaca',
                  borderRadius: 7, padding: '6px 14px', cursor: 'pointer',
                }}
              >
                <RefreshCw size={12} /> Retry
              </button>
            </div>
          )}

          {/* Empty */}
          {!scansLoading && !scansError && scans.length === 0 && (
            <div style={{
              background: BG, border: BORDER, borderRadius: 14, padding: '40px 32px',
              textAlign: 'center',
            }}>
              <ShieldCheck size={36} style={{ color: MUTED2, marginBottom: 14 }} />
              <div style={{ fontSize: 15, fontWeight: 600, color: TEXT, marginBottom: 6 }}>
                No previous scans yet
              </div>
              <div style={{ fontSize: 13, color: MUTED, marginBottom: 20 }}>
                Start a new scan to build your cryptographic inventory.
              </div>
              <button
                onClick={() => navigate('/scan')}
                style={{
                  display: 'inline-flex', alignItems: 'center', gap: 8,
                  background: ACCENT, color: '#fff', border: 'none',
                  borderRadius: 8, padding: '10px 22px', fontSize: 13, fontWeight: 600, cursor: 'pointer',
                }}
              >
                Start New Scan <ArrowRightCircle size={15} />
              </button>
            </div>
          )}

          {/* Scan list */}
          {!scansLoading && !scansError && scans.length > 0 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {scans.map((scan, i) => (
                <motion.div
                  key={scan.scan_id}
                  initial={prefersReducedMotion ? undefined : 'hidden'}
                  whileInView="visible"
                  viewport={{ once: true }}
                  variants={makeFadeIn(i * 0.05)}
                  style={{
                    background: BG, border: BORDER, borderRadius: 12,
                    padding: '16px 20px',
                    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                    flexWrap: 'wrap', gap: 14,
                    transition: 'box-shadow 0.15s',
                  }}
                  onMouseEnter={e => (e.currentTarget as HTMLDivElement).style.boxShadow = '0 2px 12px rgba(25,40,55,0.08)'}
                  onMouseLeave={e => (e.currentTarget as HTMLDivElement).style.boxShadow = 'none'}
                >
                  {/* Scan info */}
                  <div style={{ flex: 1, minWidth: 200 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                      <span style={{ fontSize: 14, fontWeight: 700, color: TEXT }}>
                        {scan.scan_name || scan.application_name || 'Unnamed Scan'}
                      </span>
                      <StatusBadge status={scan.status} />
                    </div>
                    <div style={{ fontSize: 12, color: MUTED, marginTop: 4 }}>
                      {scan.application_name && scan.application_name !== scan.scan_name && (
                        <span>{scan.application_name} · </span>
                      )}
                      {scan.finding_count} finding{scan.finding_count !== 1 ? 's' : ''}
                      {scan.completed_at && ` · ${fmtDate(scan.completed_at)}`}
                    </div>
                  </div>

                  {/* Quick actions */}
                  <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                    <button
                      onClick={() => navigate(`/dashboard?scan_id=${scan.scan_id}`)}
                      style={{
                        display: 'flex', alignItems: 'center', gap: 5, fontSize: 12, fontWeight: 600,
                        color: ACCENT, background: `${ACCENT}0E`, border: `1px solid ${ACCENT}20`,
                        borderRadius: 7, padding: '6px 12px', cursor: 'pointer',
                      }}
                    >
                      Dashboard <ChevronRight size={12} />
                    </button>
                    {scan.status.toLowerCase() === 'completed' && (
                      <>
                        <button
                          onClick={() => navigate(`/inventory/${scan.scan_id}`)}
                          style={{
                            display: 'flex', alignItems: 'center', gap: 5, fontSize: 12, fontWeight: 500,
                            color: TEXT, background: SURF, border: BORDER,
                            borderRadius: 7, padding: '6px 12px', cursor: 'pointer',
                          }}
                        >
                          Inventory
                        </button>
                        <button
                          onClick={() => navigate(`/risk/${scan.scan_id}`)}
                          style={{
                            display: 'flex', alignItems: 'center', gap: 5, fontSize: 12, fontWeight: 500,
                            color: TEXT, background: SURF, border: BORDER,
                            borderRadius: 7, padding: '6px 12px', cursor: 'pointer',
                          }}
                        >
                          Risk Analysis
                        </button>
                      </>
                    )}
                  </div>
                </motion.div>
              ))}

              <div style={{ marginTop: 8, textAlign: 'center' }}>
                <button
                  onClick={() => navigate('/scan')}
                  style={{
                    display: 'inline-flex', alignItems: 'center', gap: 8,
                    background: ACCENT, color: '#fff', border: 'none',
                    borderRadius: 8, padding: '10px 22px', fontSize: 13, fontWeight: 600, cursor: 'pointer',
                    boxShadow: '0 2px 12px rgba(115,66,226,0.18)',
                  }}
                >
                  Start New Scan <ArrowRightCircle size={15} />
                </button>
              </div>
            </div>
          )}
        </div>
      </section>

      {/* ══════════════════════════════════════════════════════
          4. ABOUT QSHIELD
         ══════════════════════════════════════════════════════ */}
      <section
        id="about"
        aria-labelledby="about-heading"
        style={{ padding: 'clamp(60px, 8vw, 96px) clamp(20px, 5vw, 60px)' }}
      >
        <div style={{ maxWidth: 1100, margin: '0 auto', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: 48 }}>

          {/* Left: Main description */}
          <div>
            <motion.div
              initial={prefersReducedMotion ? undefined : 'hidden'}
              whileInView="visible"
              viewport={{ once: true }}
              variants={makeFadeIn(0)}
            >
              <div style={{ fontSize: 11, fontWeight: 700, color: ACCENT, textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: 10 }}>
                About
              </div>
              <SectionHeading>
                <span id="about-heading">What Is QShield?</span>
              </SectionHeading>
              <p style={{ margin: '16px 0 0', fontSize: 14, color: MUTED, lineHeight: 1.75 }}>
                QShield is a <strong style={{ color: TEXT }}>cryptographic discovery, quantum-risk assessment, and post-quantum migration planning platform</strong> for security and engineering teams preparing for the transition to post-quantum cryptography.
              </p>
              <p style={{ margin: '12px 0 0', fontSize: 14, color: MUTED, lineHeight: 1.75 }}>
                It produces structured, actionable intelligence — not generic recommendations — by analyzing the actual cryptographic context of each discovered asset before producing migration guidance.
              </p>
            </motion.div>

            <motion.div
              initial={prefersReducedMotion ? undefined : 'hidden'}
              whileInView="visible"
              viewport={{ once: true }}
              variants={makeFadeIn(0.1)}
              style={{ marginTop: 28 }}
            >
              <div style={{ fontSize: 13, fontWeight: 700, color: TEXT, marginBottom: 10 }}>Implemented capabilities</div>
              {[
                'Cryptographic discovery across source code, configs, and certificates',
                'CBOM-style cryptographic asset inventory with file-level provenance',
                'Deterministic quantum-migration risk scoring (no LLM, no AI)',
                'Application-context-aware prioritization',
                'Purpose-aware migration recommendations from a curated knowledge base',
                'Deterministic migration roadmap with wave and lifecycle tracking',
                'Persistent migration lifecycle stage management',
                'Real PQC Lab operations (ML-KEM, ML-DSA) where runtime supports them',
              ].map(cap => (
                <div key={cap} style={{
                  display: 'flex', alignItems: 'flex-start', gap: 8,
                  marginBottom: 7, fontSize: 13, color: MUTED, lineHeight: 1.5,
                }}>
                  <span style={{ width: 6, height: 6, borderRadius: '50%', background: ACCENT, flexShrink: 0, marginTop: 6 }} />
                  {cap}
                </div>
              ))}
            </motion.div>
          </div>

          {/* Right: Technical transparency */}
          <div>
            <motion.div
              initial={prefersReducedMotion ? undefined : 'hidden'}
              whileInView="visible"
              viewport={{ once: true }}
              variants={makeFadeIn(0.1)}
            >
              <div style={{
                background: SURF, border: BORDER, borderRadius: 14, padding: '24px 24px', marginBottom: 20,
              }}>
                <div style={{ fontSize: 13, fontWeight: 700, color: TEXT, marginBottom: 12 }}>
                  Purpose-aware migration guidance
                </div>
                <p style={{ margin: 0, fontSize: 13, color: MUTED, lineHeight: 1.65 }}>
                  QShield does <em>not</em> blindly recommend "replace RSA with ML-KEM." It reasons about the cryptographic purpose of each finding:
                </p>
                {[
                  { label: 'RSA used for key establishment or encryption', action: 'Assess an appropriate ML-KEM-compatible migration path' },
                  { label: 'RSA / ECDSA used for digital signatures', action: 'Assess an appropriate PQC signature migration path (ML-DSA)' },
                  { label: 'Symmetric cryptography (AES, ChaCha20)', action: 'Analyzed separately — not treated as quantum-vulnerable asymmetric crypto' },
                  { label: 'Unknown cryptographic purpose', action: 'Flagged for manual review — no invented recommendation' },
                ].map(row => (
                  <div key={row.label} style={{
                    marginTop: 10, paddingTop: 10, borderTop: '1px solid rgba(25,40,55,0.06)',
                  }}>
                    <div style={{ fontSize: 12, fontWeight: 600, color: TEXT }}>{row.label}</div>
                    <div style={{ fontSize: 12, color: MUTED, marginTop: 2, display: 'flex', alignItems: 'flex-start', gap: 6 }}>
                      <ChevronRight size={13} style={{ color: ACCENT, flexShrink: 0, marginTop: 2 }} />
                      {row.action}
                    </div>
                  </div>
                ))}
              </div>

              <div style={{
                background: `${ACCENT}08`, border: `1px solid ${ACCENT}20`, borderRadius: 12, padding: '16px 20px',
              }}>
                <div style={{ fontSize: 12, fontWeight: 700, color: ACCENT, marginBottom: 8 }}>Disclaimers</div>
                {[
                  'QShield risk and readiness scores are internal deterministic prioritization metrics — not official NIST scores or compliance certifications.',
                  'PQC Lab demonstrations use real cryptographic operations but do not automatically migrate production applications.',
                  'Production migration requires protocol, interoperability, key-management, deployment, and security validation beyond what QShield automates.',
                  'Current prototype uses local single-user project access. Production deployment would require authenticated users, workspace isolation, and role-based access control.',
                ].map((note, i) => (
                  <div key={i} style={{ fontSize: 12, color: MUTED, marginBottom: i < 3 ? 6 : 0, lineHeight: 1.55, paddingLeft: 12, borderLeft: `2px solid ${ACCENT}30` }}>
                    {note}
                  </div>
                ))}
              </div>
            </motion.div>
          </div>
        </div>
      </section>

      {/* ── Footer ─────────────────────────────────────────────────────────────── */}
      <footer style={{
        borderTop: BORDER, background: SURF,
        padding: '20px clamp(20px, 5vw, 60px)',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12,
      }}>
        <span style={{ fontSize: 12, color: MUTED2 }}>QShield · Cryptographic Migration Platform · Prototype</span>
        <div style={{ display: 'flex', gap: 16 }}>
          <button onClick={() => navigate('/scan')} style={{ fontSize: 12, color: MUTED, background: 'none', border: 'none', cursor: 'pointer', padding: 0 }}>
            Start New Scan
          </button>
          <button onClick={() => navigate('/dashboard')} style={{ fontSize: 12, color: MUTED, background: 'none', border: 'none', cursor: 'pointer', padding: 0 }}>
            Dashboard
          </button>
          <button onClick={() => navigate('/demo')} style={{ fontSize: 12, color: MUTED, background: 'none', border: 'none', cursor: 'pointer', padding: 0 }}>
            PQC Lab
          </button>
        </div>
      </footer>
    </div>
  );
}

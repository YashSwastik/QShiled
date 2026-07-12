import { useNavigate } from 'react-router-dom';
import { motion, useReducedMotion, type Variants } from 'framer-motion';
import { ScanSearch, ShieldCheck, ArrowRightCircle } from 'lucide-react';

const VIDEO_URL =
  'https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260606_131516_eca35265-ea66-4fbd-8d52-22aae6e1a503.mp4';

/* ── Shared animation variant factory ────────────────────────────────────── */
/**
 * Returns a Framer Motion Variants object for a fade-up entrance.
 * Uses 'easeOut' named easing to satisfy framer-motion v12 strict types.
 */
function makeFadeUp(i: number): Variants {
  return {
    hidden: { opacity: 0, y: 28 },
    visible: {
      opacity: 1,
      y: 0,
      transition: {
        delay: i * 0.15,
        duration: 0.6,
        ease: 'easeOut',
      },
    },
  };
}

export default function LandingPage() {
  const navigate = useNavigate();
  const prefersReducedMotion = useReducedMotion();

  function motionProps(i: number) {
    if (prefersReducedMotion) {
      // Skip animation entirely for users who prefer reduced motion
      return {};
    }
    return {
      initial: 'hidden' as const,
      animate: 'visible' as const,
      variants: makeFadeUp(i),
    };
  }

  return (
    <div className="relative min-h-dvh w-full overflow-hidden flex flex-col">

      {/* ── Background Video ─────────────────────────────────────────────── */}
      <video
        autoPlay
        muted
        loop
        playsInline
        className="absolute inset-0 z-0 w-full h-full object-cover"
        aria-hidden="true"
      >
        <source src={VIDEO_URL} type="video/mp4" />
      </video>

      {/* ── Overlays — subtle, never obscure the video ───────────────────── */}
      <div className="absolute inset-0 z-[1] hero-grid-overlay pointer-events-none" aria-hidden="true" />
      <div className="absolute inset-0 z-[2] hero-vignette pointer-events-none" aria-hidden="true" />

      {/* ── Hero Content ─────────────────────────────────────────────────── */}
      <div
        className="relative z-10 flex flex-col items-center justify-center flex-1 px-5 text-center"
        style={{
          paddingTop: 'clamp(40px, 8vw, 72px)',
          paddingBottom: 48,
        }}
      >
        <div className="flex flex-col items-center gap-7" style={{ maxWidth: 760 }}>

          {/* ── Heading ── */}
          <motion.h1
            {...motionProps(0)}
            className="m-0 leading-none"
            style={{
              fontFamily: 'var(--font-heading)',
              fontSize: 'clamp(1.65rem, 5vw, 3rem)',
              lineHeight: 1.05,
              letterSpacing: '-0.01em',
              color: 'var(--color-text)',
            }}
          >
            Discover{' '}
            <ScanSearch
              size={28}
              strokeWidth={2}
              className="inline-block align-middle relative"
              style={{ top: -2, margin: '0 4px', color: 'var(--color-text)' }}
              aria-hidden="true"
            />{' '}
            Your Cryptographic Exposure
            <br />
            Before the Quantum Era{' '}
            <ShieldCheck
              size={28}
              strokeWidth={2}
              className="inline-block align-middle relative"
              style={{ top: -2, margin: '0 4px', color: 'var(--color-text)' }}
              aria-hidden="true"
            />{' '}
            Does
          </motion.h1>

          {/* ── Subtext ── */}
          <motion.p
            {...motionProps(1)}
            className="m-0"
            style={{
              fontFamily: 'var(--font-body)',
              fontSize: 'clamp(0.9rem, 2.5vw, 1.1rem)',
              lineHeight: 1.65,
              opacity: 0.8,
              color: 'var(--color-text)',
              maxWidth: 600,
            }}
          >
            Discover vulnerable cryptography, quantify quantum risk, and build a clear
            path to post-quantum security—all from one intelligent migration platform.
          </motion.p>

          {/* ── CTA ── */}
          <motion.div {...motionProps(2)}>
            <motion.button
              onClick={() => navigate('/scan')}
              whileHover={{ scale: 1.04, filter: 'brightness(1.1)' }}
              whileTap={{ scale: 0.96 }}
              className="flex items-center justify-between gap-8 text-white font-semibold cursor-pointer border-0"
              style={{
                background: 'var(--color-accent)',
                borderRadius: 50,
                fontSize: 'clamp(0.9rem, 2vw, 1rem)',
                padding: '17px 24px',
                minWidth: 210,
                boxShadow: '0 4px 24px rgba(115,66,226,0.28)',
              }}
              aria-label="Scan your cryptographic assets"
            >
              <span>Scan Your Crypto</span>
              <ArrowRightCircle size={20} strokeWidth={2} aria-hidden="true" />
            </motion.button>
          </motion.div>

          {/* ── Trust line ── */}
          <motion.p
            {...motionProps(3)}
            className="m-0 text-xs uppercase tracking-wide"
            style={{
              color: 'var(--color-text)',
              opacity: 0.45,
              letterSpacing: '0.06em',
            }}
          >
            NIST-aligned migration intelligence&nbsp;•&nbsp;Explainable risk&nbsp;•&nbsp;Real cryptographic discovery
          </motion.p>

        </div>
      </div>
    </div>
  );
}

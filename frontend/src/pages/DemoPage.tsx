/**
 * DemoPage — PENDING IMPLEMENTATION (Phase 7)
 * Stable route placeholder.
 */
import { FlaskConical, ArrowLeft } from 'lucide-react';
import { Link } from 'react-router-dom';

export default function DemoPage() {
  return (
    <div className="min-h-dvh flex flex-col items-center justify-center gap-6 px-6 text-center"
         style={{ background: 'var(--color-login-bg)', color: 'var(--color-text)' }}>
      <FlaskConical size={48} strokeWidth={1.5} style={{ opacity: 0.35 }} />
      <div>
        <h1 className="font-heading text-2xl m-0 mb-2"
            style={{ fontFamily: 'var(--font-heading)' }}>
          PQC Demo
        </h1>
        <p className="text-sm opacity-60 m-0">
          Phase 7 — not yet implemented. Live ML-KEM vs RSA demonstration coming soon.
        </p>
      </div>
      <span className="inline-block text-xs font-semibold px-3 py-1 rounded-full bg-yellow-100 text-yellow-800 border border-yellow-300">
        PENDING IMPLEMENTATION
      </span>
      <Link to="/" className="flex items-center gap-2 text-sm no-underline opacity-60 hover:opacity-100 transition-opacity"
            style={{ color: 'var(--color-text)' }}>
        <ArrowLeft size={16} /> Back to home
      </Link>
    </div>
  );
}

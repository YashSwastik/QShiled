/**
 * ScanUpload — PENDING IMPLEMENTATION (Phase 3)
 * This is a stable route placeholder. No fake data or functionality.
 */
import { ArrowLeft, UploadCloud } from 'lucide-react';
import { Link } from 'react-router-dom';

export default function ScanUpload() {
  return (
    <div className="min-h-dvh flex flex-col items-center justify-center gap-6 px-6 text-center"
         style={{ background: 'var(--color-login-bg)', color: 'var(--color-text)' }}>
      <UploadCloud size={48} strokeWidth={1.5} style={{ opacity: 0.35 }} />
      <div>
        <h1 className="font-heading text-2xl m-0 mb-2"
            style={{ fontFamily: 'var(--font-heading)' }}>
          Scan Upload
        </h1>
        <p className="text-sm opacity-60 m-0">
          Phase 3 — not yet implemented. Upload + crypto scanner coming soon.
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

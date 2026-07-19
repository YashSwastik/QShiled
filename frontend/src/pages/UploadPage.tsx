/**
 * UploadPage — Secure file upload experience (Phase B).
 *
 * Receives applicationId + appName via location state from OnboardingPage.
 * Allows drag-drop or file select → calls POST /api/scans/upload
 * Shows upload/processing/success/failure states.
 * Does NOT display fake cryptographic results.
 */
import { useState, useRef } from 'react';
import type { DragEvent, ChangeEvent } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  UploadCloud, FileText, CheckCircle, XCircle, Loader2, ArrowLeft, RefreshCw,
} from 'lucide-react';
import QShieldLogo from '../components/QShieldLogo';
import { uploadScan, type ScanResult } from '../services/uploadApi';

// ── Types ─────────────────────────────────────────────────────────────────────

type UploadState = 'idle' | 'uploading' | 'success' | 'error';

// ── Allowed extension hint ────────────────────────────────────────────────────
const ALLOWED_HINT = '.py .js .ts .java .cs .json .yaml .yml .xml .properties .conf .config .pem .crt .cer  •  ZIP archives';

export default function UploadPage() {
  const { state } = useLocation() as { state?: { applicationId?: string; appName?: string } };
  const navigate = useNavigate();

  const applicationId = state?.applicationId ?? '';
  const appName = state?.appName ?? 'Application';

  const [uploadState, setUploadState] = useState<UploadState>('idle');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [dragging, setDragging] = useState(false);
  const [scanResult, setScanResult] = useState<ScanResult | null>(null);
  const [errorMsg, setErrorMsg] = useState<string>('');
  const [uploadProgress, setUploadProgress] = useState(0);

  const inputRef = useRef<HTMLInputElement>(null);

  // ── No applicationId — likely direct navigation ───────────────────────────
  if (!applicationId) {
    return (
      <div className="min-h-dvh flex flex-col items-center justify-center gap-4" style={{ background: 'var(--color-login-bg)', color: 'var(--color-text)' }}>
        <p className="opacity-60 text-sm">No application selected. Please start from the onboarding flow.</p>
        <button onClick={() => navigate('/scan')} className="text-sm px-5 py-2.5 rounded-full text-white border-0 cursor-pointer" style={{ background: 'var(--color-accent)' }}>
          Start Onboarding
        </button>
      </div>
    );
  }

  // ── File selection ─────────────────────────────────────────────────────────

  function handleFileChange(e: ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0];
    if (f) { setSelectedFile(f); setUploadState('idle'); setScanResult(null); setErrorMsg(''); }
  }

  function handleDrop(e: DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setDragging(false);
    const f = e.dataTransfer.files[0];
    if (f) { setSelectedFile(f); setUploadState('idle'); setScanResult(null); setErrorMsg(''); }
  }

  // ── Upload handler ─────────────────────────────────────────────────────────

  async function handleUpload() {
    if (!selectedFile || !applicationId) return;
    setUploadState('uploading');
    setUploadProgress(0);
    setScanResult(null);
    setErrorMsg('');

    try {
      const result = await uploadScan(applicationId, selectedFile, setUploadProgress);
      setScanResult(result);
      setUploadState(result.status === 'completed' ? 'success' : 'error');
      if (result.status === 'failed') {
        setErrorMsg(result.error_message ?? 'Processing failed.');
      }
    } catch (err: unknown) {
      const e = err as { userMessage?: string };
      setErrorMsg(e.userMessage ?? 'Upload failed. Is the backend running?');
      setUploadState('error');
    }
  }

  function reset() {
    setSelectedFile(null);
    setUploadState('idle');
    setScanResult(null);
    setErrorMsg('');
    setUploadProgress(0);
    if (inputRef.current) inputRef.current.value = '';
  }

  // ── Render ─────────────────────────────────────────────────────────────────
  return (
    <div className="min-h-dvh flex flex-col" style={{ background: 'var(--color-login-bg)', color: 'var(--color-text)' }}>
      {/* Header */}
      <header className="flex items-center justify-between px-6 py-5 border-b" style={{ borderColor: 'rgba(25,40,55,0.1)' }}>
        <a href="/" className="flex items-center gap-2 no-underline">
          <QShieldLogo size={24} color="#192837" />
          <span className="text-base font-semibold" style={{ fontFamily: 'var(--font-heading)', color: 'var(--color-text)' }}>QShield</span>
        </a>
        <button
          onClick={() => navigate(-1)}
          className="flex items-center gap-1 text-sm opacity-50 hover:opacity-100 border-0 bg-transparent cursor-pointer"
          style={{ color: 'var(--color-text)' }}
        >
          <ArrowLeft size={14} /> Back
        </button>
      </header>

      {/* Content */}
      <div className="flex-1 flex items-center justify-center px-5 py-12">
        <div className="w-full" style={{ maxWidth: 540 }}>
          <AnimatePresence mode="wait">

            {/* ── Idle / file selected ── */}
            {(uploadState === 'idle' || uploadState === 'uploading') && (
              <motion.div key="upload" initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} transition={{ duration: 0.3 }}>
                <h1 className="text-2xl mb-1" style={{ fontFamily: 'var(--font-heading)' }}>
                  Upload files for {appName}
                </h1>
                <p className="text-sm opacity-60 mb-8">
                  Upload a ZIP archive or individual supported files. Files are never executed.
                </p>

                {/* Drop zone */}
                <div
                  onDrop={handleDrop}
                  onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
                  onDragLeave={() => setDragging(false)}
                  onClick={() => inputRef.current?.click()}
                  className="flex flex-col items-center justify-center gap-3 rounded-2xl border-2 border-dashed cursor-pointer transition-colors py-12 px-6 text-center mb-6"
                  style={{
                    borderColor: dragging ? 'var(--color-accent)' : 'rgba(25,40,55,0.2)',
                    background: dragging ? 'rgba(115,66,226,0.04)' : 'white',
                  }}
                >
                  <UploadCloud size={36} style={{ color: 'var(--color-accent)', opacity: 0.8 }} />
                  {selectedFile ? (
                    <div className="flex flex-col items-center gap-1">
                      <FileText size={20} style={{ color: 'var(--color-accent)' }} />
                      <span className="text-sm font-medium">{selectedFile.name}</span>
                      <span className="text-xs opacity-50">{(selectedFile.size / 1024).toFixed(1)} KB</span>
                    </div>
                  ) : (
                    <>
                      <p className="text-sm font-medium">Drag & drop or click to select</p>
                      <p className="text-xs opacity-50">{ALLOWED_HINT}</p>
                    </>
                  )}
                  <input
                    ref={inputRef}
                    type="file"
                    className="hidden"
                    accept=".zip,.py,.js,.ts,.java,.cs,.json,.yaml,.yml,.xml,.properties,.conf,.config,.pem,.crt,.cer"
                    onChange={handleFileChange}
                  />
                </div>

                {/* Upload progress bar */}
                {uploadState === 'uploading' && (
                  <div className="mb-4">
                    <div className="flex items-center justify-between text-xs opacity-60 mb-1">
                      <span>Uploading…</span>
                      <span>{uploadProgress}%</span>
                    </div>
                    <div className="h-1.5 rounded-full overflow-hidden" style={{ background: 'rgba(25,40,55,0.1)' }}>
                      <motion.div
                        className="h-full rounded-full"
                        style={{ background: 'var(--color-accent)' }}
                        initial={{ width: 0 }}
                        animate={{ width: `${uploadProgress}%` }}
                        transition={{ duration: 0.2 }}
                      />
                    </div>
                  </div>
                )}

                <button
                  onClick={handleUpload}
                  disabled={!selectedFile || uploadState === 'uploading'}
                  className="w-full flex items-center justify-center gap-2 rounded-full py-3 text-sm font-semibold text-white border-0 cursor-pointer transition-all disabled:opacity-40"
                  style={{ background: 'var(--color-accent)' }}
                >
                  {uploadState === 'uploading'
                    ? <><Loader2 size={16} className="animate-spin" /> Processing…</>
                    : <><UploadCloud size={16} /> Start Secure Upload</>
                  }
                </button>
              </motion.div>
            )}

            {/* ── Success ── */}
            {uploadState === 'success' && scanResult && (
              <motion.div key="success" initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} className="flex flex-col items-center text-center gap-6">
                <div className="w-16 h-16 rounded-full flex items-center justify-center" style={{ background: 'rgba(16,185,129,0.1)' }}>
                  <CheckCircle size={32} style={{ color: '#10b981' }} />
                </div>
                <div>
                  <h2 className="text-xl mb-2" style={{ fontFamily: 'var(--font-heading)' }}>Files securely processed</h2>
                  <p className="text-sm opacity-60 max-w-sm">
                    Your files are ready for cryptographic analysis. No analysis has run yet.
                  </p>
                </div>

                {/* Scan metadata */}
                <div className="w-full rounded-xl p-5 text-sm text-left" style={{ background: 'white' }}>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <div className="text-xs opacity-50 mb-0.5">Scan ID</div>
                      <div className="font-mono text-xs truncate">{scanResult.id}</div>
                    </div>
                    <div>
                      <div className="text-xs opacity-50 mb-0.5">Status</div>
                      <div className="font-medium text-emerald-600">Completed</div>
                    </div>
                    <div>
                      <div className="text-xs opacity-50 mb-0.5">Files scanned</div>
                      <div className="font-semibold text-lg">{scanResult.file_count}</div>
                    </div>
                    <div>
                      <div className="text-xs opacity-50 mb-0.5">Crypto findings</div>
                      <div className="font-semibold text-lg" style={{ color: scanResult.finding_count > 0 ? '#b91c1c' : '#15803d' }}>
                        {scanResult.finding_count}
                      </div>
                    </div>
                    <div>
                      <div className="text-xs opacity-50 mb-0.5">Upload type</div>
                      <div className="capitalize">{scanResult.upload_type?.replace('_', ' ')}</div>
                    </div>
                    <div className="col-span-1">
                      <div className="text-xs opacity-50 mb-0.5">File</div>
                      <div className="truncate">{scanResult.upload_name}</div>
                    </div>
                  </div>
                </div>

                <p className="text-xs opacity-40 max-w-sm">
                  {scanResult.finding_count > 0
                    ? `The Crypto Discovery Engine detected ${scanResult.finding_count} cryptographic usages.`
                    : 'No cryptographic usages were detected in these files.'}
                </p>

                <div className="flex gap-3 w-full">
                  <button onClick={reset} className="flex-1 flex items-center justify-center gap-2 rounded-full py-3 text-sm font-semibold border-0 cursor-pointer" style={{ background: 'rgba(25,40,55,0.08)', color: 'var(--color-text)' }}>
                    <RefreshCw size={14} /> Upload another
                  </button>
                  <button
                    onClick={() => navigate(`/inventory/${scanResult.id}`)}
                    className="flex-1 rounded-full py-3 text-sm font-semibold text-white border-0 cursor-pointer"
                    style={{ background: 'var(--color-accent)' }}
                  >
                    View Findings ({scanResult.finding_count}) →
                  </button>
                </div>
              </motion.div>
            )}

            {/* ── Error ── */}
            {uploadState === 'error' && (
              <motion.div key="error" initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} className="flex flex-col items-center text-center gap-6">
                <div className="w-16 h-16 rounded-full flex items-center justify-center" style={{ background: 'rgba(239,68,68,0.1)' }}>
                  <XCircle size={32} style={{ color: '#ef4444' }} />
                </div>
                <div>
                  <h2 className="text-xl mb-2" style={{ fontFamily: 'var(--font-heading)' }}>Upload failed</h2>
                  <p className="text-sm opacity-60 max-w-sm">{errorMsg || 'An error occurred during processing.'}</p>
                </div>
                <button onClick={reset} className="flex items-center gap-2 rounded-full px-8 py-3 text-sm font-semibold text-white border-0 cursor-pointer" style={{ background: 'var(--color-accent)' }}>
                  <RefreshCw size={14} /> Try again
                </button>
              </motion.div>
            )}

          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}

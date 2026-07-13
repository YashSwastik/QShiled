/**
 * FindingDetailPage — deep-dive view for one CryptoFinding.
 *
 * Route: /inventory/:scanId/finding/:findingId
 *
 * Sections:
 *   1. Algorithm + classification (header)
 *   2. Source location (file, line, evidence)
 *   3. Detection metadata (method, confidence, rule)
 *   4. Quantum migration relevance
 *   5. Classical / legacy warning (only when applicable)
 *   6. NIST recommendation
 */
import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  ArrowLeft, FileCode, AlertTriangle, ShieldAlert, ShieldCheck,
  Cpu, Hash, Lock, Atom, HelpCircle,
} from 'lucide-react';
import QShieldLogo from '../components/QShieldLogo';
import { CategoryBadge, QuantumBadge, ConfidenceBar, DetectionMethodLabel } from '../components/FindingBadges';
import { getFinding, type Finding, type FindingCategory, type QuantumStatus } from '../services/inventoryApi';

// ── Constants ─────────────────────────────────────────────────────────────────

const CATEGORY_CONTEXT: Record<string, { icon: React.ReactNode; description: string }> = {
  QUANTUM_VULNERABLE_PUBLIC_KEY: {
    icon: <ShieldAlert size={18} style={{ color: '#b91c1c' }} />,
    description:
      `Public-key asymmetric algorithm that is broken by Shor's algorithm on a cryptographically relevant ` +
      `quantum computer. This finding should be prioritised for migration to NIST-approved post-quantum algorithms.`,
  },
  SYMMETRIC: {
    icon: <Lock size={18} style={{ color: '#15803d' }} />,
    description:
      `Symmetric cipher. Grover's algorithm provides a quadratic speedup for brute-force attacks, ` +
      `halving effective key length. AES-256 retains ≪128-bit post-quantum security and is quantum-safe for most applications.`,
  },
  HASH: {
    icon: <Hash size={18} style={{ color: '#1d4ed8' }} />,
    description:
      `Cryptographic hash function. Grover's algorithm reduces collision resistance, but SHA-256 and stronger ` +
      `variants remain acceptable post-quantum. SHA-3 family is fully quantum-safe.`,
  },
  LEGACY_DEPRECATED: {
    icon: <AlertTriangle size={18} style={{ color: '#c2410c' }} />,
    description:
      `Classically broken or deprecated algorithm. This is a conventional security concern independent of ` +
      `quantum computing — it should be remediated urgently regardless of the quantum migration timeline.`,
  },
  POST_QUANTUM: {
    icon: <Atom size={18} style={{ color: '#166534' }} />,
    description:
      `NIST-approved post-quantum algorithm (FIPS 203 / 204 / 205). This usage is already quantum-safe.`,
  },
  UNKNOWN_REVIEW: {
    icon: <HelpCircle size={18} style={{ color: '#6b21a8' }} />,
    description:
      `Pattern detected but classification requires manual review. Inspect the source context to determine ` +
      `algorithm and quantum relevance.`,
  },
};

const QUANTUM_EXPLANATION: Record<string, string> = {
  vulnerable:
    `Broken by Shor's algorithm. A cryptographically relevant quantum computer could recover private keys ` +
    `or forge signatures for this algorithm. Migration to a NIST-approved post-quantum alternative is required.`,
  safe:
    `Quantum-safe. Grover's algorithm provides at most a quadratic speedup, which does not break this ` +
    `algorithm at the recommended key or output size.`,
  borderline:
    `Borderline quantum security. Grover's algorithm halves the effective security level. ` +
    `Consider upgrading to a larger variant (e.g. AES-256, SHA-384) to maintain long-term security margins.`,
  unknown:
    `Quantum relevance could not be determined automatically. Manual review is required to classify this finding.`,
  hybrid:
    `Hybrid scheme combining classical and post-quantum cryptography. Provides a migration path with ` +
    `backward-compatible security.`,
};

const LEGACY_NOTE: Record<string, string> = {
  MD5:
    'MD5 is classically broken — MD5 collision attacks are trivially computable (Wang et al., 2004). ' +
    'This is a conventional security failure unrelated to quantum computing. Replace with SHA-256 or SHA-3 immediately.',
  SHA1:
    'SHA-1 is classically broken — practical collision attacks were demonstrated by Google (SHAttered, 2017). ' +
    'This is a conventional security failure, not a quantum concern. Replace with SHA-256 or SHA-3.',
  'SHA-1':
    'SHA-1 is classically broken — practical collision attacks were demonstrated by Google (SHAttered, 2017). ' +
    'This is a conventional security failure, not a quantum concern. Replace with SHA-256 or SHA-3.',
  DES:
    'DES and 3DES use key sizes too small to be secure classically (56-bit DES, ~112-bit 3DES). ' +
    'Deprecated per NIST SP 800-67r2. Replace with AES-256.',
  RC4:
    'RC4 is prohibited in TLS (RFC 7465) due to statistical biases enabling key recovery attacks. ' +
    'Replace with AES-256-GCM or ChaCha20-Poly1305.',
};

// ── Styles ─────────────────────────────────────────────────────────────────────

const S = {
  card: {
    background: 'white',
    border: '1px solid rgba(25,40,55,0.08)',
    borderRadius: 12,
    padding: '20px 24px',
    marginBottom: 14,
  } as React.CSSProperties,
  label: {
    fontSize: 11,
    fontWeight: 600,
    textTransform: 'uppercase' as const,
    letterSpacing: '0.06em',
    opacity: 0.4,
    marginBottom: 4,
  },
  value: { fontSize: 14, fontWeight: 500 },
  code: {
    fontFamily: 'monospace',
    fontSize: 12,
    background: '#f3f4f6',
    padding: '10px 14px',
    borderRadius: 8,
    overflow: 'auto',
    whiteSpace: 'pre-wrap' as const,
    wordBreak: 'break-all' as const,
    border: '1px solid rgba(25,40,55,0.06)',
    lineHeight: 1.6,
    marginTop: 8,
  },
};

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div style={{ marginBottom: 16 }}>
      <div style={S.label}>{label}</div>
      <div style={S.value}>{children}</div>
    </div>
  );
}

// ── Main ──────────────────────────────────────────────────────────────────────

export default function FindingDetailPage() {
  const { scanId, findingId } = useParams<{ scanId: string; findingId: string }>();
  const navigate = useNavigate();

  const [finding, setFinding] = useState<Finding | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!findingId) return;
    setLoading(true);
    setError(null);
    getFinding(findingId)
      .then(setFinding)
      .catch(() => setError('Could not load finding. It may have been removed.'))
      .finally(() => setLoading(false));
  }, [findingId]);

  const catCtx = finding ? (CATEGORY_CONTEXT[finding.category] ?? CATEGORY_CONTEXT.UNKNOWN_REVIEW) : null;
  const qExplain = finding ? (QUANTUM_EXPLANATION[finding.quantum_status] ?? '') : '';
  const legacyNote = finding
    ? (LEGACY_NOTE[finding.algorithm_family] ?? LEGACY_NOTE[finding.algorithm] ?? null)
    : null;
  const isLegacy = finding?.category === 'LEGACY_DEPRECATED';

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
        <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
          <a href="/" style={{ display: 'flex', alignItems: 'center', gap: 8, textDecoration: 'none' }}>
            <QShieldLogo size={22} color="#192837" />
            <span style={{ fontFamily: 'var(--font-heading)', fontWeight: 700, fontSize: 15, color: 'var(--color-text)' }}>
              QShield
            </span>
          </a>
          <span style={{ opacity: 0.2, fontSize: 18 }}>/</span>
          <button
            onClick={() => navigate(`/inventory/${scanId}`)}
            style={{ fontSize: 13, opacity: 0.5, background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-text)', padding: 0 }}
          >
            Crypto Inventory
          </button>
          <span style={{ opacity: 0.2, fontSize: 18 }}>/</span>
          <span style={{ fontSize: 13, fontWeight: 500 }}>Finding Detail</span>
        </div>
        <button
          onClick={() => navigate(-1)}
          style={{
            display: 'flex', alignItems: 'center', gap: 6,
            fontSize: 13, opacity: 0.5, background: 'none', border: 'none',
            cursor: 'pointer', color: 'var(--color-text)',
          }}
          onMouseEnter={e => (e.currentTarget.style.opacity = '1')}
          onMouseLeave={e => (e.currentTarget.style.opacity = '0.5')}
        >
          <ArrowLeft size={14} /> Back
        </button>
      </header>

      <main style={{ flex: 1, padding: '28px 24px 48px', maxWidth: 820, width: '100%', margin: '0 auto' }}>

        {/* Loading */}
        {loading && (
          <div style={{ padding: '48px 0', textAlign: 'center', opacity: 0.4, fontSize: 14 }}>
            Loading finding…
          </div>
        )}

        {/* Error */}
        {error && (
          <div style={{
            background: 'white', borderRadius: 12, border: '1px solid rgba(25,40,55,0.08)',
            padding: 40, textAlign: 'center', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 12,
          }}>
            <AlertTriangle size={28} style={{ color: '#ef4444' }} />
            <p style={{ margin: 0, opacity: 0.6, fontSize: 14 }}>{error}</p>
            <button
              onClick={() => navigate(-1)}
              style={{ padding: '8px 16px', borderRadius: 8, border: '1px solid rgba(25,40,55,0.15)', background: 'white', cursor: 'pointer', fontSize: 13 }}
            >
              <ArrowLeft size={12} style={{ display: 'inline', marginRight: 4 }} />Back to inventory
            </button>
          </div>
        )}

        {/* Content */}
        {!loading && !error && finding && (
          <motion.div initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}>

            {/* ── 1. Classification header ── */}
            <div style={{ ...S.card, borderLeft: '4px solid var(--color-accent)' }}>
              <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 16, flexWrap: 'wrap' }}>
                <div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                    {catCtx?.icon}
                    <h1 style={{ fontFamily: 'var(--font-heading)', fontSize: 22, margin: 0 }}>
                      {finding.algorithm}
                    </h1>
                  </div>
                  <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 8 }}>
                    <CategoryBadge category={finding.category as FindingCategory} />
                    <QuantumBadge status={finding.quantum_status as QuantumStatus} />
                    {finding.key_size && (
                      <span style={{
                        display: 'inline-flex', alignItems: 'center', padding: '3px 8px',
                        borderRadius: 6, fontSize: 11, fontWeight: 600,
                        background: '#f3f4f6', color: '#374151',
                      }}>
                        {finding.key_size}-bit key
                      </span>
                    )}
                  </div>
                  <p style={{ margin: 0, fontSize: 13, lineHeight: 1.6, opacity: 0.6, maxWidth: 520 }}>
                    {catCtx?.description}
                  </p>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6, alignItems: 'flex-end', minWidth: 120 }}>
                  <div style={S.label}>Algorithm family</div>
                  <code style={{ fontSize: 13, fontFamily: 'monospace', opacity: 0.65 }}>
                    {finding.algorithm_family}
                  </code>
                  {finding.usage_context && (
                    <div style={{ fontSize: 12, opacity: 0.5, marginTop: 4 }}>
                      Used as: <strong>{finding.usage_context}</strong>
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* ── 2. Source location ── */}
            <div style={S.card}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 7, marginBottom: 14 }}>
                <FileCode size={15} style={{ opacity: 0.5 }} />
                <span style={{ fontWeight: 600, fontSize: 14 }}>Source Location</span>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px 24px', marginBottom: 14 }}>
                <Field label="File">
                  <code style={{ fontFamily: 'monospace', fontSize: 12, wordBreak: 'break-all' }}>
                    {finding.file_path}
                  </code>
                </Field>
                <Field label="Line number">
                  {finding.line_number != null
                    ? <code style={{ fontFamily: 'monospace', fontSize: 13 }}>L{finding.line_number}</code>
                    : <span style={{ opacity: 0.4 }}>—</span>}
                </Field>
              </div>
              {finding.raw_snippet && (
                <div>
                  <div style={S.label}>Evidence (masked)</div>
                  <div style={S.code}>{finding.raw_snippet}</div>
                  <div style={{ fontSize: 11, opacity: 0.4, marginTop: 6 }}>
                    Sensitive key material is redacted. Only the structural pattern is shown.
                  </div>
                </div>
              )}
            </div>

            {/* ── 3. Detection metadata ── */}
            <div style={S.card}>
              <div style={{ fontWeight: 600, fontSize: 14, marginBottom: 14 }}>Detection Details</div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '12px 24px' }}>
                <Field label="Detection method">
                  <DetectionMethodLabel method={finding.detection_method} />
                  {' '}
                  <span style={{ fontSize: 12, opacity: 0.55 }}>({finding.detection_method})</span>
                </Field>
                <Field label="Confidence score">
                  <ConfidenceBar value={finding.confidence} />
                </Field>
                <Field label="Finding ID">
                  <code style={{ fontFamily: 'monospace', fontSize: 11, opacity: 0.55, wordBreak: 'break-all' }}>
                    {finding.id}
                  </code>
                </Field>
              </div>
              <div style={{
                marginTop: 12, padding: '10px 14px',
                background: '#f8f8f5', borderRadius: 8, fontSize: 12, lineHeight: 1.7, opacity: 0.7,
              }}>
                {finding.detection_method === 'ast' && (
                  'Detected via Python Abstract Syntax Tree analysis — requires the code to be syntactically valid Python. High confidence.'
                )}
                {finding.detection_method === 'regex' && (
                  'Detected via pattern matching across source text. Confidence may be lower if the match is in a comment or documentation string.'
                )}
                {finding.detection_method === 'cert_parse' && (
                  'Detected by cryptographically parsing the certificate or key file using the cryptography library. Confidence is 1.0.'
                )}
              </div>
            </div>

            {/* ── 4. Quantum migration relevance ── */}
            <div style={{
              ...S.card,
              borderLeft: finding.quantum_status === 'vulnerable'
                ? '4px solid #ef4444'
                : finding.quantum_status === 'safe'
                ? '4px solid #22c55e'
                : '4px solid #f59e0b',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 7, marginBottom: 10 }}>
                {finding.quantum_status === 'vulnerable'
                  ? <ShieldAlert size={15} style={{ color: '#b91c1c' }} />
                  : finding.quantum_status === 'safe'
                  ? <ShieldCheck size={15} style={{ color: '#15803d' }} />
                  : <AlertTriangle size={15} style={{ color: '#c2410c' }} />
                }
                <span style={{ fontWeight: 600, fontSize: 14 }}>Quantum Migration Relevance</span>
                <QuantumBadge status={finding.quantum_status as QuantumStatus} size="xs" />
              </div>
              <p style={{ margin: '0 0 12px', fontSize: 13, lineHeight: 1.7, opacity: 0.7 }}>
                {qExplain}
              </p>
              {finding.nist_recommendation && (
                <div style={{
                  padding: '12px 16px', borderRadius: 8,
                  background: finding.quantum_status === 'vulnerable' ? '#fef2f2' : '#f0fdf4',
                  border: `1px solid ${finding.quantum_status === 'vulnerable' ? '#fecaca' : '#bbf7d0'}`,
                }}>
                  <div style={{ fontSize: 11, fontWeight: 600, opacity: 0.5, marginBottom: 4, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                    NIST recommendation
                  </div>
                  <p style={{ margin: 0, fontSize: 13, lineHeight: 1.65 }}>{finding.nist_recommendation}</p>
                </div>
              )}
            </div>

            {/* ── 5. Legacy / classical warning (only for LEGACY_DEPRECATED) ── */}
            {isLegacy && (
              <div style={{
                ...S.card,
                borderLeft: '4px solid #f97316',
                background: '#fffbf7',
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 7, marginBottom: 10 }}>
                  <AlertTriangle size={15} style={{ color: '#c2410c' }} />
                  <span style={{ fontWeight: 600, fontSize: 14, color: '#c2410c' }}>
                    Classical / Legacy Warning
                  </span>
                </div>
                <div style={{
                  display: 'inline-block', padding: '3px 8px', borderRadius: 6,
                  background: '#fff7ed', border: '1px solid #fed7aa',
                  fontSize: 11, fontWeight: 600, color: '#9a3412', marginBottom: 10,
                }}>
                  ⚠ NOT a quantum-specific concern
                </div>
                <p style={{ margin: 0, fontSize: 13, lineHeight: 1.7, opacity: 0.75 }}>
                  {legacyNote ??
                    'This algorithm is classically broken or deprecated. It should be replaced immediately ' +
                    'as a conventional security measure, independent of the quantum migration timeline.'}
                </p>
              </div>
            )}

            {/* ── Key size note ── */}
            {finding.key_size && (
              <div style={{ ...S.card, background: '#f8f8f5' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 7, marginBottom: 8 }}>
                  <Cpu size={14} style={{ opacity: 0.4 }} />
                  <span style={{ fontWeight: 600, fontSize: 14 }}>Key Size</span>
                </div>
                <p style={{ margin: 0, fontSize: 13, lineHeight: 1.65, opacity: 0.65 }}>
                  Detected key size: <strong>{finding.key_size} bits</strong>.{' '}
                  {finding.algorithm_family === 'RSA' && finding.key_size < 3072 &&
                    'RSA keys under 3072 bits are considered below the NIST minimum for long-term security. ' +
                    'Regardless, all RSA keys are quantum-vulnerable and should be migrated to ML-KEM or ML-DSA.'}
                  {finding.algorithm_family === 'RSA' && finding.key_size >= 3072 &&
                    'RSA-3072+ meets NIST classical security requirements, but all RSA is quantum-vulnerable.'}
                  {finding.algorithm_family === 'AES' && finding.key_size === 128 &&
                    'AES-128 retains 64-bit post-quantum security (Grover). Prefer AES-256 for long-term data protection.'}
                  {finding.algorithm_family === 'AES' && finding.key_size === 256 &&
                    'AES-256 retains 128-bit post-quantum security (Grover). Considered quantum-safe.'}
                </p>
              </div>
            )}

          </motion.div>
        )}
      </main>
    </div>
  );
}

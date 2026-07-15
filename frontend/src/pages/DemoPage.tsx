/**
 * PQCLabPage.tsx — QShield PQC Lab
 *
 * Professional interactive post-quantum cryptography demonstration workspace.
 * All operations are real — executed on the backend using the cryptography
 * library (PyCA / OpenSSL 3.x backend).
 *
 * Algorithm support (verified against cryptography 49.0.0):
 *   ML-KEM-768, ML-KEM-1024  (FIPS 203 — Key Establishment)
 *   ML-DSA-44, ML-DSA-65, ML-DSA-87  (FIPS 204 — Digital Signatures)
 *   SLH-DSA — unavailable in current build
 *
 * Route: /demo
 */

import { useEffect, useState, useCallback } from 'react';
import { Link } from 'react-router-dom';
import {
  Home, BookOpen, BarChart2, Map, FlaskConical, FileText, Clock,
  ChevronDown, ChevronUp, RefreshCw, CheckCircle, XCircle,
  AlertCircle, Loader2, Info,
} from 'lucide-react';
import QShieldLogo from '../components/QShieldLogo';
import {
  getCapabilities,
  runKEMDemo,
  runSignatureDemo,
  runBenchmark,
} from '../services/pqcLabApi';
import type {
  PQCCapabilities,
  KEMDemoResult,
  SignatureDemoResult,
  BenchmarkResult,
} from '../services/pqcLabApi';

// ── Design tokens ─────────────────────────────────────────────────────────────
const BORDER  = '1px solid rgba(25,40,55,0.09)';
const BORDER2 = '1px solid rgba(25,40,55,0.06)';
const TEXT    = '#192837';
const MUTED   = 'rgba(25,40,55,0.50)';
const MUTED2  = 'rgba(25,40,55,0.30)';
const BG_PAGE = '#F2F2EE';
const BG_SURF = '#ffffff';
const ACCENT  = '#7342E2';
const GREEN   = '#15803d';
const RED     = '#b91c1c';
const AMBER   = '#92400e';
const BG_GREEN = '#f0fdf4';
const BG_RED   = '#fef2f2';
const BG_AMBER = '#fffbeb';

// ── Sidebar ───────────────────────────────────────────────────────────────────
function Sidebar() {
  const navItems = [
    { key: 'dashboard',  label: 'Dashboard',        Icon: Home,         to: '/dashboard' },
    { key: 'inventory',  label: 'Crypto Inventory',  Icon: BookOpen,     to: '#' },
    { key: 'risk',       label: 'Risk Analysis',     Icon: BarChart2,    to: '#' },
    { key: 'migration',  label: 'Migration',         Icon: Map,          to: '#' },
    { key: 'roadmap',    label: 'Roadmap',           Icon: Clock,        to: '#' },
    { key: 'pqclab',    label: 'PQC Lab',           Icon: FlaskConical, to: '/demo', active: true },
    { key: 'reports',    label: 'Reports',           Icon: FileText,     to: '#' },
  ] as const;

  return (
    <aside style={{
      width: 220, flexShrink: 0, background: BG_SURF, borderRight: BORDER,
      display: 'flex', flexDirection: 'column', minHeight: '100vh',
      position: 'sticky', top: 0, alignSelf: 'flex-start',
    }}>
      <div style={{ padding: '18px 20px 16px', borderBottom: BORDER, display: 'flex', alignItems: 'center', gap: 10 }}>
        <QShieldLogo size={20} color={TEXT} />
        <span style={{ fontSize: 15, fontWeight: 700, color: TEXT, fontFamily: 'var(--font-heading)', letterSpacing: '-0.01em' }}>
          QShield
        </span>
      </div>
      <nav style={{ padding: '10px', flex: 1 }}>
        {navItems.map(({ key, label, Icon, to, ...rest }) => {
          const active = (rest as { active?: boolean }).active ?? false;
          const disabled = to === '#';
          return (
            <Link key={key} to={to} style={{
              display: 'flex', alignItems: 'center', gap: 10,
              padding: '7px 12px', borderRadius: 7, marginBottom: 1,
              fontSize: 13, fontWeight: active ? 600 : 400,
              color: active ? ACCENT : disabled ? MUTED2 : TEXT,
              background: active ? `${ACCENT}10` : 'transparent',
              textDecoration: 'none', opacity: disabled ? 0.5 : 1,
              cursor: disabled ? 'default' : 'pointer',
              pointerEvents: disabled ? 'none' : 'auto',
            }}
              onMouseEnter={e => { if (!active && !disabled) (e.currentTarget as HTMLElement).style.background = 'rgba(25,40,55,0.04)'; }}
              onMouseLeave={e => { if (!active && !disabled) (e.currentTarget as HTMLElement).style.background = 'transparent'; }}
            >
              <span style={{ color: active ? ACCENT : MUTED, flexShrink: 0 }}><Icon size={15} /></span>
              {label}
            </Link>
          );
        })}
      </nav>
      <div style={{ padding: '14px 20px', borderTop: BORDER }}>
        <span style={{ fontSize: 11, color: MUTED2 }}>QShield · PQC Lab</span>
      </div>
    </aside>
  );
}

// ── Metric card ───────────────────────────────────────────────────────────────
function MetricCard({ label, value, unit }: { label: string; value: string | number; unit?: string }) {
  return (
    <div style={{
      background: BG_SURF, border: BORDER, borderRadius: 10,
      padding: '12px 16px', display: 'flex', flexDirection: 'column', gap: 3, minWidth: 110,
    }}>
      <div style={{ fontSize: 10, fontWeight: 600, color: MUTED2, textTransform: 'uppercase', letterSpacing: '0.07em' }}>{label}</div>
      <div style={{ fontSize: 20, fontWeight: 700, color: TEXT, fontFamily: 'var(--font-heading)', lineHeight: 1.1 }}>
        {typeof value === 'number' ? value.toFixed(2) : value}
        {unit && <span style={{ fontSize: 12, fontWeight: 500, color: MUTED, marginLeft: 3 }}>{unit}</span>}
      </div>
    </div>
  );
}

// ── Section label ─────────────────────────────────────────────────────────────
function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <div style={{ fontSize: 10, fontWeight: 700, color: MUTED2, textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: 10 }}>
      {children}
    </div>
  );
}

// ── Algorithm family selector card ────────────────────────────────────────────
function AlgoFamilyCard({
  name, category, standard, supported, reason, selected, onClick,
}: {
  name: string; category: string; standard: string;
  supported: boolean; reason?: string;
  selected: boolean; onClick: () => void;
}) {
  return (
    <button
      onClick={supported ? onClick : undefined}
      disabled={!supported}
      aria-pressed={selected}
      aria-label={`${name} — ${supported ? 'supported' : 'unavailable'}`}
      style={{
        flex: '1 1 140px', minWidth: 130, padding: '14px 16px',
        borderRadius: 10, border: selected ? `2px solid ${ACCENT}` : BORDER,
        background: selected ? `${ACCENT}08` : BG_SURF,
        cursor: supported ? 'pointer' : 'default',
        opacity: supported ? 1 : 0.5,
        textAlign: 'left', display: 'flex', flexDirection: 'column', gap: 5,
        transition: 'border 0.12s, background 0.12s',
      }}
    >
      <div style={{ fontSize: 14, fontWeight: 700, color: selected ? ACCENT : TEXT }}>{name}</div>
      <div style={{ fontSize: 11, color: MUTED, lineHeight: 1.3 }}>{category}</div>
      <div style={{ fontSize: 10, color: MUTED2 }}>{standard}</div>
      <div style={{
        display: 'inline-flex', alignItems: 'center', gap: 4, marginTop: 2,
        fontSize: 10, fontWeight: 700,
        color: supported ? GREEN : RED,
      }}>
        <span style={{
          width: 6, height: 6, borderRadius: '50%',
          background: supported ? GREEN : '#ef4444', flexShrink: 0,
        }} />
        {supported ? 'Supported' : `Unavailable${reason ? ' — ' + reason : ''}`}
      </div>
    </button>
  );
}

// ── KEM stepper ───────────────────────────────────────────────────────────────
function KEMStepper({ result }: { result: KEMDemoResult }) {
  const steps = [
    { label: 'Keypair', sub: `Public key: ${result.sizes_bytes.public_key} B · Private key: ${result.sizes_bytes.private_key} B` },
    { label: 'Encapsulate', sub: `Ciphertext: ${result.sizes_bytes.ciphertext} B · Shared secret: ${result.sizes_bytes.shared_secret} B` },
    { label: 'Decapsulate', sub: `Recovered shared secret from ciphertext` },
    { label: result.success ? '✓ Secrets Match' : '✕ Mismatch', sub: result.verification_message, success: result.success },
  ];
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 0 }}>
      {steps.map((s, i) => (
        <div key={i} style={{ display: 'flex', gap: 12 }}>
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', width: 28, flexShrink: 0 }}>
            <div style={{
              width: 28, height: 28, borderRadius: '50%',
              background: i === steps.length - 1
                ? (s.success ? '#dcfce7' : '#fef2f2')
                : `${ACCENT}15`,
              border: `2px solid ${i === steps.length - 1 ? (s.success ? GREEN : RED) : ACCENT}`,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 11, fontWeight: 700, color: i === steps.length - 1 ? (s.success ? GREEN : RED) : ACCENT,
              flexShrink: 0,
            }}>
              {i + 1}
            </div>
            {i < steps.length - 1 && (
              <div style={{ width: 2, flex: 1, background: `${ACCENT}20`, minHeight: 16, margin: '2px 0' }} />
            )}
          </div>
          <div style={{ paddingBottom: 16 }}>
            <div style={{
              fontSize: 13, fontWeight: 600,
              color: i === steps.length - 1 ? (s.success ? GREEN : RED) : TEXT,
            }}>{s.label}</div>
            <div style={{ fontSize: 11, color: MUTED, lineHeight: 1.5, marginTop: 2 }}>{s.sub}</div>
          </div>
        </div>
      ))}
    </div>
  );
}

// ── Result banner ─────────────────────────────────────────────────────────────
function ResultBanner({ success, title, sub }: { success: boolean; title: string; sub: string }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'flex-start', gap: 10,
      background: success ? BG_GREEN : BG_RED,
      border: `1px solid ${success ? '#bbf7d0' : '#fecaca'}`,
      borderRadius: 10, padding: '12px 16px',
    }}>
      {success
        ? <CheckCircle size={20} style={{ color: GREEN, flexShrink: 0, marginTop: 1 }} />
        : <XCircle size={20} style={{ color: RED, flexShrink: 0, marginTop: 1 }} />
      }
      <div>
        <div style={{ fontSize: 14, fontWeight: 700, color: success ? GREEN : RED }}>{title}</div>
        <div style={{ fontSize: 12, color: MUTED, marginTop: 2 }}>{sub}</div>
      </div>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────
type AlgoFamily = 'kem' | 'signature';

export default function PQCLabPage() {
  const [caps, setCaps] = useState<PQCCapabilities | null>(null);
  const [capsLoading, setCapsLoading] = useState(true);
  const [capsError, setCapsError] = useState<string | null>(null);

  const [family, setFamily] = useState<AlgoFamily>('kem');
  const [kemParam, setKemParam] = useState('ML-KEM-768');
  const [sigParam, setSigParam] = useState('ML-DSA-65');
  const [sigMessage, setSigMessage] = useState('QShield PQC Lab — post-quantum signature demonstration.');
  const [tamper, setTamper] = useState(true);

  // Tab: demo or benchmark
  const [tab, setTab] = useState<'demo' | 'benchmark'>('demo');
  const [benchIter, setBenchIter] = useState(10);

  // Results
  const [kemResult, setKemResult] = useState<KEMDemoResult | null>(null);
  const [sigResult, setSigResult] = useState<SignatureDemoResult | null>(null);
  const [benchResult, setBenchResult] = useState<BenchmarkResult | null>(null);
  const [running, setRunning] = useState(false);
  const [opError, setOpError] = useState<string | null>(null);

  // Technical details panel
  const [showDetails, setShowDetails] = useState(false);

  // Load capabilities
  useEffect(() => {
    setCapsLoading(true);
    getCapabilities()
      .then(data => {
        setCaps(data);
        if (data.kem.length > 0) setKemParam(data.kem[0].name);
        if (data.signature.length > 0) setSigParam(data.signature[1]?.name ?? data.signature[0].name);
      })
      .catch(e => setCapsError(e.message))
      .finally(() => setCapsLoading(false));
  }, []);

  const runDemo = useCallback(async () => {
    setRunning(true);
    setOpError(null);
    setKemResult(null);
    setSigResult(null);
    setBenchResult(null);
    try {
      if (tab === 'benchmark') {
        const param = family === 'kem' ? kemParam : sigParam;
        const r = await runBenchmark(param, benchIter);
        setBenchResult(r);
      } else if (family === 'kem') {
        const r = await runKEMDemo(kemParam);
        setKemResult(r);
      } else {
        const r = await runSignatureDemo(sigParam, sigMessage, tamper);
        setSigResult(r);
      }
    } catch (e) {
      setOpError(e instanceof Error ? e.message : 'Operation failed');
    } finally {
      setRunning(false);
    }
  }, [family, kemParam, sigParam, sigMessage, tamper, tab, benchIter]);

  // ── Loading state
  if (capsLoading) {
    return (
      <div style={{ display: 'flex', minHeight: '100dvh', background: BG_PAGE }}>
        <Sidebar />
        <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column', gap: 12 }}>
          <Loader2 size={28} style={{ color: ACCENT, animation: 'spin 1s linear infinite' }} />
          <div style={{ fontSize: 13, color: MUTED }}>Checking PQC runtime capabilities…</div>
          <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
        </div>
      </div>
    );
  }

  // ── Capability error state
  if (capsError || !caps) {
    return (
      <div style={{ display: 'flex', minHeight: '100dvh', background: BG_PAGE }}>
        <Sidebar />
        <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 40 }}>
          <div style={{ background: BG_SURF, border: '1px solid #fecaca', borderRadius: 12, padding: '32px 40px', textAlign: 'center', maxWidth: 440 }}>
            <AlertCircle size={32} style={{ color: '#ef4444', marginBottom: 12 }} />
            <div style={{ fontSize: 15, fontWeight: 600, color: TEXT, marginBottom: 6 }}>PQC Implementation Unavailable</div>
            <div style={{ fontSize: 12, color: MUTED, marginBottom: 20 }}>{capsError}</div>
            <button onClick={() => window.location.reload()} style={{
              display: 'inline-flex', alignItems: 'center', gap: 6,
              padding: '7px 16px', borderRadius: 7, border: BORDER,
              background: BG_SURF, fontSize: 13, cursor: 'pointer', color: TEXT,
            }}>
              <RefreshCw size={13} /> Retry
            </button>
          </div>
        </div>
      </div>
    );
  }

  const env = caps.environment;
  const currentKEMCap = caps.kem.find(k => k.name === kemParam);
  const currentSigCap = caps.signature.find(s => s.name === sigParam);
  const currentCap = family === 'kem' ? currentKEMCap : currentSigCap;
  const benchParam = family === 'kem' ? kemParam : sigParam;

  return (
    <div style={{ display: 'flex', minHeight: '100dvh', background: BG_PAGE, color: TEXT, fontFamily: 'var(--font-body)' }}>
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      <Sidebar />

      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>

        {/* ── Page header ── */}
        <div style={{
          background: BG_SURF, borderBottom: BORDER,
          padding: '14px 28px', position: 'sticky', top: 0, zIndex: 10,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
            <div>
              <div style={{ fontSize: 17, fontWeight: 700, color: TEXT, fontFamily: 'var(--font-heading)' }}>PQC Lab</div>
              <div style={{ fontSize: 11, color: MUTED }}>
                Run and inspect real post-quantum cryptographic operations supported by the current QShield runtime.
              </div>
            </div>
            {/* Runtime strip */}
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
              {[
                { label: env.library.split(' ')[0], value: env.library_version },
                { label: 'Python', value: env.python_version },
                { label: env.platform_system, value: '' },
              ].map(({ label, value }) => (
                <span key={label} style={{
                  fontSize: 10, fontWeight: 600, color: MUTED,
                  background: BG_PAGE, border: BORDER, borderRadius: 5,
                  padding: '3px 8px',
                }}>
                  {label}{value ? `: ${value}` : ''}
                </span>
              ))}
              <span style={{
                fontSize: 10, fontWeight: 700, color: GREEN,
                background: BG_GREEN, border: '1px solid #bbf7d0', borderRadius: 5,
                padding: '3px 8px', display: 'flex', alignItems: 'center', gap: 4,
              }}>
                <span style={{ width: 6, height: 6, borderRadius: '50%', background: GREEN }} />
                PQC Backend Ready
              </span>
            </div>
          </div>
        </div>

        {/* ── Body ── */}
        <div style={{ padding: '22px 28px', display: 'flex', flexDirection: 'column', gap: 18 }}>

          {/* Algorithm family selector */}
          <div>
            <SectionLabel>Algorithm Family</SectionLabel>
            <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
              <AlgoFamilyCard
                name="ML-KEM" category="Key Establishment / KEM"
                standard="FIPS 203" supported={caps.kem.length > 0}
                selected={family === 'kem'}
                onClick={() => setFamily('kem')}
              />
              <AlgoFamilyCard
                name="ML-DSA" category="Digital Signatures"
                standard="FIPS 204" supported={caps.signature.length > 0}
                selected={family === 'signature'}
                onClick={() => setFamily('signature')}
              />
              <AlgoFamilyCard
                name="SLH-DSA" category="Stateless Hash-Based Signatures"
                standard="FIPS 205" supported={false}
                reason={caps.slhdsa.reason}
                selected={false}
                onClick={() => {}}
              />
            </div>
          </div>

          {/* Parameter set + tab bar */}
          <div style={{ display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
            <div>
              <SectionLabel>Parameter Set</SectionLabel>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                {(family === 'kem' ? caps.kem : caps.signature).map(p => (
                  <button key={p.name}
                    onClick={() => family === 'kem' ? setKemParam(p.name) : setSigParam(p.name)}
                    aria-pressed={family === 'kem' ? kemParam === p.name : sigParam === p.name}
                    style={{
                      padding: '5px 14px', borderRadius: 7, border: BORDER,
                      background: (family === 'kem' ? kemParam : sigParam) === p.name
                        ? `${ACCENT}12` : BG_SURF,
                      color: (family === 'kem' ? kemParam : sigParam) === p.name ? ACCENT : TEXT,
                      fontWeight: (family === 'kem' ? kemParam : sigParam) === p.name ? 700 : 400,
                      fontSize: 12, cursor: 'pointer',
                      ...(((family === 'kem' ? kemParam : sigParam) === p.name)
                        ? { borderColor: ACCENT }
                        : {}),
                    }}>
                    {p.name}
                  </button>
                ))}
              </div>
            </div>

            {/* Mode toggle */}
            <div style={{ marginLeft: 'auto' }}>
              <SectionLabel>Mode</SectionLabel>
              <div style={{ display: 'flex', border: BORDER, borderRadius: 8, overflow: 'hidden' }}>
                {(['demo', 'benchmark'] as const).map(t => (
                  <button key={t} onClick={() => setTab(t)} style={{
                    padding: '5px 16px', fontSize: 12, cursor: 'pointer',
                    background: tab === t ? `${ACCENT}12` : BG_SURF,
                    color: tab === t ? ACCENT : MUTED,
                    fontWeight: tab === t ? 700 : 400, border: 'none',
                    borderRight: t === 'demo' ? BORDER : 'none',
                  }}>
                    {t === 'demo' ? 'Interactive Demo' : 'Benchmark'}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* ── Two-column workspace ── */}
          <div style={{ display: 'flex', gap: 18, alignItems: 'flex-start', flexWrap: 'wrap' }}>

            {/* LEFT — interactive workspace */}
            <div style={{ flex: '1 1 400px', minWidth: 300, display: 'flex', flexDirection: 'column', gap: 14 }}>

              {/* KEM demo UI */}
              {tab === 'demo' && family === 'kem' && (
                <div style={{ background: BG_SURF, border: BORDER, borderRadius: 12, padding: '22px 24px', display: 'flex', flexDirection: 'column', gap: 16 }}>
                  <SectionLabel>ML-KEM Key Establishment Demonstration</SectionLabel>

                  {/* Flow preview */}
                  <div style={{
                    display: 'flex', alignItems: 'center', gap: 6,
                    fontSize: 11, color: MUTED, flexWrap: 'wrap',
                  }}>
                    {['Keypair', '→', 'Encapsulate', '→', 'Decapsulate', '→', '✓ Shared Secret Match'].map((s, i) => (
                      <span key={i} style={{ color: s.startsWith('✓') ? GREEN : s === '→' ? MUTED2 : TEXT, fontWeight: s.startsWith('✓') ? 700 : 400 }}>
                        {s}
                      </span>
                    ))}
                  </div>

                  {/* Run button */}
                  <button
                    id="kem-run-btn"
                    onClick={runDemo}
                    disabled={running}
                    aria-label={`Run ${kemParam} demonstration`}
                    style={{
                      padding: '10px 24px', borderRadius: 8, border: 'none',
                      background: running ? '#e5e7eb' : ACCENT,
                      color: running ? MUTED : '#fff',
                      fontSize: 13, fontWeight: 700, cursor: running ? 'not-allowed' : 'pointer',
                      display: 'flex', alignItems: 'center', gap: 8, alignSelf: 'flex-start',
                      transition: 'background 0.12s',
                    }}>
                    {running && <Loader2 size={14} style={{ animation: 'spin 1s linear infinite' }} />}
                    {running ? `Running ${kemParam}…` : `Run ${kemParam} Demonstration`}
                  </button>

                  {opError && (
                    <div style={{ background: BG_RED, border: '1px solid #fecaca', borderRadius: 8, padding: '10px 14px', fontSize: 12, color: RED }}>
                      {opError}
                    </div>
                  )}

                  {kemResult && (
                    <>
                      <KEMStepper result={kemResult} />
                      <ResultBanner
                        success={kemResult.success}
                        title={kemResult.success ? 'Key Establishment Successful' : 'Key Establishment Failed'}
                        sub={kemResult.verification_message}
                      />

                      <div>
                        <SectionLabel>Measured This Run</SectionLabel>
                        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
                          <MetricCard label="Key Generation" value={kemResult.timings_ms.key_generation} unit="ms" />
                          <MetricCard label="Encapsulation" value={kemResult.timings_ms.encapsulation} unit="ms" />
                          <MetricCard label="Decapsulation" value={kemResult.timings_ms.decapsulation} unit="ms" />
                          <MetricCard label="Ciphertext" value={kemResult.sizes_bytes.ciphertext} unit="B" />
                        </div>
                      </div>

                      <div>
                        <SectionLabel>Cryptographic Object Sizes</SectionLabel>
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px 24px', fontSize: 12 }}>
                          {[
                            ['Public Key', `${kemResult.sizes_bytes.public_key} bytes`],
                            ['Private Key', `${kemResult.sizes_bytes.private_key} bytes`],
                            ['Ciphertext', `${kemResult.sizes_bytes.ciphertext} bytes`],
                            ['Shared Secret', `${kemResult.sizes_bytes.shared_secret} bytes`],
                          ].map(([k, v]) => (
                            <div key={k} style={{ display: 'flex', justifyContent: 'space-between', padding: '4px 0', borderBottom: BORDER2 }}>
                              <span style={{ color: MUTED }}>{k}</span>
                              <span style={{ fontWeight: 600, fontFamily: 'monospace' }}>{v}</span>
                            </div>
                          ))}
                        </div>
                        <div style={{ fontSize: 10, color: MUTED2, marginTop: 6 }}>
                          Public-key fingerprint: <code style={{ fontSize: 10 }}>{kemResult.fingerprints.public_key}…</code>
                        </div>
                      </div>
                    </>
                  )}
                </div>
              )}

              {/* Signature demo UI */}
              {tab === 'demo' && family === 'signature' && (
                <div style={{ background: BG_SURF, border: BORDER, borderRadius: 12, padding: '22px 24px', display: 'flex', flexDirection: 'column', gap: 16 }}>
                  <SectionLabel>ML-DSA Signature Demonstration</SectionLabel>

                  <div style={{
                    display: 'flex', alignItems: 'center', gap: 6,
                    fontSize: 11, color: MUTED, flexWrap: 'wrap',
                  }}>
                    {['Keypair', '→', 'Sign Message', '→', 'Verify', '→', '✓ Signature Valid'].map((s, i) => (
                      <span key={i} style={{ color: s.startsWith('✓') ? GREEN : s === '→' ? MUTED2 : TEXT, fontWeight: s.startsWith('✓') ? 700 : 400 }}>
                        {s}
                      </span>
                    ))}
                  </div>

                  {/* Message input */}
                  <div>
                    <label htmlFor="sig-message" style={{ fontSize: 11, fontWeight: 600, color: MUTED2, textTransform: 'uppercase', letterSpacing: '0.06em', display: 'block', marginBottom: 6 }}>
                      Message to Sign
                    </label>
                    <textarea
                      id="sig-message"
                      value={sigMessage}
                      onChange={e => setSigMessage(e.target.value)}
                      rows={3}
                      maxLength={4096}
                      style={{
                        width: '100%', padding: '10px 12px',
                        border: BORDER, borderRadius: 8, fontSize: 13,
                        fontFamily: 'var(--font-body)', resize: 'vertical',
                        outline: 'none', background: BG_PAGE, color: TEXT,
                        boxSizing: 'border-box',
                      }}
                      placeholder="Enter a message to sign…"
                    />
                    <div style={{ fontSize: 10, color: MUTED2, textAlign: 'right', marginTop: 2 }}>
                      {sigMessage.length} / 4096
                    </div>
                  </div>

                  {/* Tamper toggle */}
                  <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, cursor: 'pointer', userSelect: 'none' }}>
                    <input
                      type="checkbox"
                      checked={tamper}
                      onChange={e => setTamper(e.target.checked)}
                      aria-label="Also run tampered-message verification"
                      style={{ accentColor: ACCENT, width: 14, height: 14 }}
                    />
                    <span style={{ color: TEXT, fontWeight: 500 }}>
                      Also run tampered-message verification
                    </span>
                    <span style={{ fontSize: 11, color: MUTED }}>(demonstrates signature integrity)</span>
                  </label>

                  <button
                    id="sig-run-btn"
                    onClick={runDemo}
                    disabled={running || !sigMessage.trim()}
                    aria-label={`Run ${sigParam} demonstration`}
                    style={{
                      padding: '10px 24px', borderRadius: 8, border: 'none',
                      background: (running || !sigMessage.trim()) ? '#e5e7eb' : ACCENT,
                      color: (running || !sigMessage.trim()) ? MUTED : '#fff',
                      fontSize: 13, fontWeight: 700, cursor: (running || !sigMessage.trim()) ? 'not-allowed' : 'pointer',
                      display: 'flex', alignItems: 'center', gap: 8, alignSelf: 'flex-start',
                    }}>
                    {running && <Loader2 size={14} style={{ animation: 'spin 1s linear infinite' }} />}
                    {running ? `Running ${sigParam}…` : `Generate Keypair & Sign`}
                  </button>

                  {opError && (
                    <div style={{ background: BG_RED, border: '1px solid #fecaca', borderRadius: 8, padding: '10px 14px', fontSize: 12, color: RED }}>
                      {opError}
                    </div>
                  )}

                  {sigResult && (
                    <>
                      {/* Sizes */}
                      <div>
                        <SectionLabel>Cryptographic Object Sizes</SectionLabel>
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px 24px', fontSize: 12 }}>
                          {[
                            ['Public Key', `${sigResult.sizes_bytes.public_key} bytes`],
                            ['Private Key', `${sigResult.sizes_bytes.private_key} bytes`],
                            ['Signature', `${sigResult.sizes_bytes.signature} bytes`],
                            ['Message', `${sigResult.message_length_bytes} bytes`],
                          ].map(([k, v]) => (
                            <div key={k} style={{ display: 'flex', justifyContent: 'space-between', padding: '4px 0', borderBottom: BORDER2 }}>
                              <span style={{ color: MUTED }}>{k}</span>
                              <span style={{ fontWeight: 600, fontFamily: 'monospace' }}>{v}</span>
                            </div>
                          ))}
                        </div>
                      </div>

                      {/* Original verification */}
                      <ResultBanner
                        success={sigResult.original_verification.valid}
                        title={sigResult.original_verification.valid ? 'Signature Valid' : 'Signature Invalid'}
                        sub={sigResult.original_verification.message}
                      />

                      {/* Tamper test */}
                      {sigResult.tamper_verification && (
                        <div>
                          <div style={{ fontSize: 11, color: AMBER, fontWeight: 700, marginBottom: 6, display: 'flex', alignItems: 'center', gap: 5 }}>
                            <Info size={12} /> Tamper Test — expected to fail
                          </div>
                          <ResultBanner
                            success={false}
                            title="Signature Invalid for Modified Message"
                            sub={sigResult.tamper_verification.message}
                          />
                        </div>
                      )}

                      <div>
                        <SectionLabel>Measured This Run</SectionLabel>
                        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
                          <MetricCard label="Key Generation" value={sigResult.timings_ms.key_generation} unit="ms" />
                          <MetricCard label="Signing" value={sigResult.timings_ms.signing} unit="ms" />
                          <MetricCard label="Verification" value={sigResult.timings_ms.verification} unit="ms" />
                          <MetricCard label="Signature" value={sigResult.sizes_bytes.signature} unit="B" />
                        </div>
                      </div>
                    </>
                  )}
                </div>
              )}

              {/* Benchmark UI */}
              {tab === 'benchmark' && (
                <div style={{ background: BG_SURF, border: BORDER, borderRadius: 12, padding: '22px 24px', display: 'flex', flexDirection: 'column', gap: 14 }}>
                  <SectionLabel>Benchmark — {benchParam}</SectionLabel>

                  <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
                    <span style={{ fontSize: 12, color: MUTED }}>Iterations:</span>
                    {[5, 10, 25, 50].map(n => (
                      <button key={n} onClick={() => setBenchIter(n)}
                        aria-pressed={benchIter === n}
                        aria-label={`${n} iterations`}
                        style={{
                          padding: '4px 14px', borderRadius: 7, border: BORDER, cursor: 'pointer',
                          background: benchIter === n ? `${ACCENT}10` : BG_SURF,
                          color: benchIter === n ? ACCENT : TEXT,
                          fontWeight: benchIter === n ? 700 : 400, fontSize: 12,
                          ...(benchIter === n ? { borderColor: ACCENT } : {}),
                        }}>
                        {n}
                      </button>
                    ))}
                  </div>

                  <button
                    id="bench-run-btn"
                    onClick={runDemo}
                    disabled={running}
                    aria-label={`Run benchmark for ${benchParam}, ${benchIter} iterations`}
                    style={{
                      padding: '10px 24px', borderRadius: 8, border: 'none',
                      background: running ? '#e5e7eb' : ACCENT,
                      color: running ? MUTED : '#fff',
                      fontSize: 13, fontWeight: 700, cursor: running ? 'not-allowed' : 'pointer',
                      display: 'flex', alignItems: 'center', gap: 8, alignSelf: 'flex-start',
                    }}>
                    {running && <Loader2 size={14} style={{ animation: 'spin 1s linear infinite' }} />}
                    {running ? 'Running benchmark…' : `Run Benchmark (${benchIter} iterations)`}
                  </button>

                  {opError && (
                    <div style={{ background: BG_RED, border: '1px solid #fecaca', borderRadius: 8, padding: '10px 14px', fontSize: 12, color: RED }}>
                      {opError}
                    </div>
                  )}

                  {benchResult && (
                    <>
                      <div>
                        <SectionLabel>Results — {benchResult.iterations} Iterations</SectionLabel>
                        <div style={{ overflowX: 'auto' }}>
                          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
                            <thead>
                              <tr style={{ borderBottom: BORDER }}>
                                {['Operation', 'Average', 'Minimum', 'Maximum', 'Runs'].map(h => (
                                  <th key={h} style={{ padding: '8px 12px', textAlign: 'left', fontWeight: 700, color: MUTED, fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                                    {h}
                                  </th>
                                ))}
                              </tr>
                            </thead>
                            <tbody>
                              {Object.entries(benchResult.statistics).map(([op, stat]) => (
                                <tr key={op} style={{ borderBottom: BORDER2 }}>
                                  <td style={{ padding: '8px 12px', fontWeight: 600, color: TEXT, textTransform: 'capitalize' }}>
                                    {op.replace(/_/g, ' ')}
                                  </td>
                                  <td style={{ padding: '8px 12px', fontFamily: 'monospace' }}>{stat.avg_ms.toFixed(3)} ms</td>
                                  <td style={{ padding: '8px 12px', fontFamily: 'monospace' }}>{stat.min_ms.toFixed(3)} ms</td>
                                  <td style={{ padding: '8px 12px', fontFamily: 'monospace' }}>{stat.max_ms.toFixed(3)} ms</td>
                                  <td style={{ padding: '8px 12px', color: MUTED }}>{benchResult.iterations}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </div>
                      <div style={{ fontSize: 11, color: AMBER, background: BG_AMBER, border: '1px solid #fde68a', borderRadius: 8, padding: '8px 12px' }}>
                        {benchResult.disclaimer}
                      </div>
                    </>
                  )}
                </div>
              )}
            </div>

            {/* RIGHT — algorithm info panel */}
            <div style={{ flex: '0 0 260px', minWidth: 220, display: 'flex', flexDirection: 'column', gap: 14 }}>
              <div style={{ background: BG_SURF, border: BORDER, borderRadius: 12, padding: '18px 20px' }}>
                <SectionLabel>Algorithm Details</SectionLabel>
                {currentCap ? (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                    <div>
                      <div style={{ fontSize: 16, fontWeight: 700, color: ACCENT, fontFamily: 'var(--font-heading)' }}>{currentCap.name}</div>
                      <div style={{ fontSize: 11, color: MUTED, marginTop: 2 }}>{currentCap.standard}</div>
                    </div>
                    {[
                      { label: 'Purpose', value: currentCap.purpose },
                      { label: 'Security Level', value: currentCap.security_level },
                      { label: 'Standard', value: `${currentCap.std_category} — ${currentCap.standard}` },
                      { label: 'Public Key', value: `${currentCap.pub_key_bytes} bytes` },
                      ...('ciphertext_bytes' in currentCap ? [
                        { label: 'Ciphertext', value: `${currentCap.ciphertext_bytes} bytes` },
                        { label: 'Shared Secret', value: `${currentCap.shared_secret_bytes} bytes` },
                      ] : [
                        { label: 'Max Signature', value: `${(currentCap as typeof caps.signature[number]).max_sig_bytes} bytes` },
                      ]),
                    ].map(({ label, value }) => (
                      <div key={label}>
                        <div style={{ fontSize: 9, fontWeight: 700, color: MUTED2, textTransform: 'uppercase', letterSpacing: '0.07em' }}>{label}</div>
                        <div style={{ fontSize: 12, color: TEXT, fontWeight: 500, marginTop: 1 }}>{value}</div>
                      </div>
                    ))}
                    <div>
                      <div style={{ fontSize: 9, fontWeight: 700, color: MUTED2, textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: 4 }}>Operations</div>
                      {currentCap.operations.map(op => (
                        <div key={op} style={{ display: 'flex', alignItems: 'center', gap: 5, fontSize: 11, color: GREEN, marginBottom: 2 }}>
                          <CheckCircle size={10} /> {op.replace(/_/g, ' ')}
                        </div>
                      ))}
                    </div>
                    <div>
                      <div style={{ fontSize: 9, fontWeight: 700, color: MUTED2, textTransform: 'uppercase', letterSpacing: '0.07em' }}>Implementation</div>
                      <div style={{ fontSize: 11, color: TEXT, marginTop: 2 }}>
                        {env.library} {env.library_version}
                      </div>
                      <div style={{ fontSize: 10, color: MUTED2 }}>OpenSSL backend</div>
                    </div>
                  </div>
                ) : (
                  <div style={{ fontSize: 12, color: MUTED }}>Select a parameter set to view details.</div>
                )}
              </div>

              {/* SLH-DSA notice */}
              <div style={{ background: BG_AMBER, border: '1px solid #fde68a', borderRadius: 10, padding: '12px 14px' }}>
                <div style={{ fontSize: 11, fontWeight: 700, color: AMBER, marginBottom: 4 }}>SLH-DSA Unavailable</div>
                <div style={{ fontSize: 11, color: AMBER, lineHeight: 1.5 }}>{caps.slhdsa.reason}</div>
              </div>
            </div>
          </div>

          {/* Technical details (collapsible) */}
          <div style={{ background: BG_SURF, border: BORDER, borderRadius: 12, overflow: 'hidden' }}>
            <button
              onClick={() => setShowDetails(d => !d)}
              aria-expanded={showDetails}
              style={{
                width: '100%', padding: '12px 20px', display: 'flex', alignItems: 'center',
                justifyContent: 'space-between', background: 'transparent', border: 'none',
                cursor: 'pointer', fontSize: 12, fontWeight: 600, color: TEXT,
              }}>
              Technical Details
              {showDetails ? <ChevronUp size={14} style={{ color: MUTED }} /> : <ChevronDown size={14} style={{ color: MUTED }} />}
            </button>
            {showDetails && (
              <div style={{ padding: '0 20px 16px', display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: '6px 24px', fontSize: 12 }}>
                {[
                  ['Library', `${env.library} ${env.library_version}`],
                  ['Python', env.python_version],
                  ['Platform', env.platform_system],
                  ['OpenSSL Backend', env.openssl_backend ? 'Yes' : 'No'],
                  ['ML-KEM', `FIPS 203 — ${caps.kem.length ? 'Supported' : 'Unavailable'}`],
                  ['ML-DSA', `FIPS 204 — ${caps.signature.length ? 'Supported' : 'Unavailable'}`],
                  ['SLH-DSA', `FIPS 205 — ${caps.slhdsa.available ? 'Supported' : 'Unavailable'}`],
                  ['Measurement Method', "time.perf_counter() (Python)"],
                  ['Key Material', 'Private keys and shared secrets not returned'],
                  ['Fingerprints', 'SHA-256 prefixes only'],
                ].map(([k, v]) => (
                  <div key={k} style={{ padding: '5px 0', borderBottom: BORDER2 }}>
                    <div style={{ fontSize: 10, color: MUTED2, fontWeight: 600 }}>{k}</div>
                    <div style={{ color: TEXT, fontWeight: 500 }}>{v}</div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Disclaimers */}
          <div style={{
            background: BG_SURF, border: BORDER, borderRadius: 10,
            padding: '14px 20px', display: 'flex', gap: 10,
          }}>
            <Info size={14} style={{ color: MUTED, flexShrink: 0, marginTop: 1 }} />
            <div style={{ fontSize: 11, color: MUTED, lineHeight: 1.6 }}>
              <strong>PQC Lab is a demonstration and evaluation environment.</strong>{' '}
              Performance measurements depend on hardware, operating system, runtime, implementation, system load, and benchmark methodology.
              Running a PQC demonstration does not automatically migrate a production application.
              Production migration requires protocol, interoperability, key-management, deployment, and security validation.
              QShield does not claim FIPS certification or production certification of this environment.
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}

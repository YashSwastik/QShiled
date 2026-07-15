/**
 * OnboardingPage — real project + application creation onboarding.
 *
 * Reached via "Scan Your Crypto" CTA on the landing page (/scan).
 * Step 1: Create or name a Project
 * Step 2: Define the Application with business context
 * Step 3: Confirmation → navigate to scan upload (Phase 3)
 *
 * This page calls real backend APIs. No fake data.
 */
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { ArrowLeft, ArrowRight, CheckCircle, Loader2, AlertCircle } from 'lucide-react';
import QShieldLogo from '../components/QShieldLogo';
import {
  createOrganization,
  createProject,
  createApplication,
  type BusinessCriticality,
  type Environment,
  type DataSensitivity,
  type ConfidentialityRequirement,
} from '../services/projectsApi';

// ── Types ─────────────────────────────────────────────────────────────────────

interface Step1Data {
  orgName: string;
  projectName: string;
  projectDescription: string;
}

interface Step2Data {
  appName: string;
  appDescription: string;
  tech_stack: string;
  business_criticality: BusinessCriticality;
  environment: Environment;
  internet_exposed: boolean;
  data_sensitivity: DataSensitivity;
  confidentiality_requirement: ConfidentialityRequirement;
  data_lifetime_years: number;
  owner_team: string;
}

// ── Slide animation ───────────────────────────────────────────────────────────

const EASE_OUT = [0.0, 0.0, 0.2, 1] as const;
const EASE_IN  = [0.4, 0.0, 1.0, 1] as const;

function slideProps() {
  return {
    initial: { opacity: 0, x: 32 },
    animate: { opacity: 1, x: 0, transition: { duration: 0.35, ease: EASE_OUT } },
    exit:    { opacity: 0, x: -32, transition: { duration: 0.2,  ease: EASE_IN  } },
  } as const;
}

// ── Helper components ─────────────────────────────────────────────────────────

function Field({
  label,
  children,
  hint,
}: {
  label: string;
  children: React.ReactNode;
  hint?: string;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <label className="text-sm font-medium" style={{ color: 'var(--color-text)' }}>
        {label}
      </label>
      {children}
      {hint && <p className="text-xs opacity-50">{hint}</p>}
    </div>
  );
}

const inputCls =
  'w-full rounded-xl border px-4 py-2.5 text-sm outline-none transition-colors focus:ring-2';
const inputStyle = {
  borderColor: 'rgba(25,40,55,0.2)',
  background: 'white',
  color: 'var(--color-text)',
};

function Select({
  value,
  onChange,
  options,
}: {
  value: string;
  onChange: (v: string) => void;
  options: { value: string; label: string }[];
}) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className={inputCls}
      style={inputStyle}
    >
      {options.map((o) => (
        <option key={o.value} value={o.value}>
          {o.label}
        </option>
      ))}
    </select>
  );
}

// ── Main Component ────────────────────────────────────────────────────────────

export default function OnboardingPage() {
  const navigate = useNavigate();
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [createdIds, setCreatedIds] = useState<{
    orgId?: string;
    projectId?: string;
    appId?: string;
  }>({});

  const [step1, setStep1] = useState<Step1Data>({
    orgName: '',
    projectName: '',
    projectDescription: '',
  });

  const [step2, setStep2] = useState<Step2Data>({
    appName: '',
    appDescription: '',
    tech_stack: '',
    business_criticality: 'medium',
    environment: 'production',
    internet_exposed: false,
    data_sensitivity: 'internal',
    confidentiality_requirement: 'medium_term',
    data_lifetime_years: 5,
    owner_team: '',
  });

  // ── Step 1 submit — create org + project ────────────────────────────────────
  async function handleStep1Submit(e: React.FormEvent) {
    e.preventDefault();
    if (!step1.orgName.trim() || !step1.projectName.trim()) return;
    setLoading(true);
    setError(null);
    try {
      // Generate slug from org name
      const slug = step1.orgName
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, '-')
        .replace(/^-|-$/g, '')
        .slice(0, 60) + '-' + Date.now().toString(36);

      const org = await createOrganization({ name: step1.orgName, slug });
      const project = await createProject({
        organization_id: org.id,
        name: step1.projectName,
        description: step1.projectDescription || undefined,
      });
      setCreatedIds({ orgId: org.id, projectId: project.id });
      setStep(2);
    } catch (err: unknown) {
      const e = err as { userMessage?: string };
      setError(e.userMessage ?? 'Failed to create project. Is the backend running?');
    } finally {
      setLoading(false);
    }
  }

  // ── Step 2 submit — create application ──────────────────────────────────────
  async function handleStep2Submit(e: React.FormEvent) {
    e.preventDefault();
    if (!step2.appName.trim() || !createdIds.projectId) return;
    setLoading(true);
    setError(null);
    try {
      const app = await createApplication({
        project_id: createdIds.projectId,
        name: step2.appName,
        description: step2.appDescription || undefined,
        tech_stack: step2.tech_stack || undefined,
        business_criticality: step2.business_criticality,
        environment: step2.environment,
        internet_exposed: step2.internet_exposed,
        data_sensitivity: step2.data_sensitivity,
        confidentiality_requirement: step2.confidentiality_requirement,
        data_lifetime_years: step2.data_lifetime_years,
        owner_team: step2.owner_team || undefined,
      });
      setCreatedIds((prev) => ({ ...prev, appId: app.id }));
      setStep(3);
    } catch (err: unknown) {
      const e = err as { userMessage?: string };
      setError(e.userMessage ?? 'Failed to create application.');
    } finally {
      setLoading(false);
    }
  }

  // ── Render ─────────────────────────────────────────────────────────────────
  return (
    <div
      className="min-h-dvh flex flex-col"
      style={{ background: 'var(--color-login-bg)', color: 'var(--color-text)' }}
    >
      {/* Header */}
      <header className="flex items-center justify-between px-6 py-5 border-b" style={{ borderColor: 'rgba(25,40,55,0.1)' }}>
        <a href="/" className="flex items-center gap-2 no-underline">
          <QShieldLogo size={24} color="#192837" />
          <span className="text-base font-semibold" style={{ fontFamily: 'var(--font-heading)', color: 'var(--color-text)' }}>
            QShield
          </span>
        </a>
        <div className="flex items-center gap-2 text-xs opacity-50">
          {[1, 2, 3].map((n) => (
            <span key={n} className="flex items-center gap-1">
              <span
                className="inline-flex items-center justify-center w-5 h-5 rounded-full text-[10px] font-bold"
                style={{
                  background: n <= step ? 'var(--color-accent)' : 'rgba(25,40,55,0.1)',
                  color: n <= step ? 'white' : 'inherit',
                }}
              >
                {n}
              </span>
              {n < 3 && <span>──</span>}
            </span>
          ))}
        </div>
      </header>

      {/* Content */}
      <div className="flex-1 flex items-center justify-center px-5 py-10">
        <div className="w-full" style={{ maxWidth: 520 }}>
          <AnimatePresence mode="wait">
            {/* ── Step 1: Project ── */}
            {step === 1 && (
              <motion.div key="step1" {...slideProps()}>
                <h1
                  className="text-2xl mb-1"
                  style={{ fontFamily: 'var(--font-heading)', color: 'var(--color-text)' }}
                >
                  Start your migration project
                </h1>
                <p className="text-sm opacity-60 mb-8">
                  Tell us about your organization and the migration effort you're tracking.
                </p>

                <form onSubmit={handleStep1Submit} className="flex flex-col gap-5">
                  <Field label="Organization name" hint="Your company or team name">
                    <input
                      className={inputCls}
                      style={inputStyle}
                      placeholder="e.g. Acme Financial Services"
                      value={step1.orgName}
                      onChange={(e) => setStep1((p) => ({ ...p, orgName: e.target.value }))}
                      required
                    />
                  </Field>

                  <Field label="Project name" hint="Descriptive name for this migration effort">
                    <input
                      className={inputCls}
                      style={inputStyle}
                      placeholder="e.g. PQC Readiness Q3 2025"
                      value={step1.projectName}
                      onChange={(e) => setStep1((p) => ({ ...p, projectName: e.target.value }))}
                      required
                    />
                  </Field>

                  <Field label="Description (optional)">
                    <textarea
                      className={inputCls}
                      style={{ ...inputStyle, resize: 'none' }}
                      rows={3}
                      placeholder="Scope, goals, or notes about this project"
                      value={step1.projectDescription}
                      onChange={(e) => setStep1((p) => ({ ...p, projectDescription: e.target.value }))}
                    />
                  </Field>

                  {error && (
                    <div className="flex items-center gap-2 text-sm text-red-600 bg-red-50 rounded-xl px-4 py-3">
                      <AlertCircle size={16} />
                      {error}
                    </div>
                  )}

                  <button
                    type="submit"
                    disabled={loading || !step1.orgName.trim() || !step1.projectName.trim()}
                    className="flex items-center justify-center gap-2 rounded-full py-3 text-sm font-semibold text-white border-0 cursor-pointer transition-all disabled:opacity-50"
                    style={{ background: 'var(--color-accent)' }}
                  >
                    {loading ? <Loader2 size={16} className="animate-spin" /> : null}
                    Continue
                    <ArrowRight size={16} />
                  </button>
                </form>
              </motion.div>
            )}

            {/* ── Step 2: Application ── */}
            {step === 2 && (
              <motion.div key="step2" {...slideProps()}>
                <button
                  onClick={() => setStep(1)}
                  className="flex items-center gap-1 text-sm opacity-50 hover:opacity-100 mb-6 border-0 bg-transparent cursor-pointer"
                  style={{ color: 'var(--color-text)' }}
                >
                  <ArrowLeft size={14} /> Back
                </button>

                <h1
                  className="text-2xl mb-1"
                  style={{ fontFamily: 'var(--font-heading)', color: 'var(--color-text)' }}
                >
                  Define your application
                </h1>
                <p className="text-sm opacity-60 mb-8">
                  Business context helps QShield weight your cryptographic risk correctly.
                </p>

                <form onSubmit={handleStep2Submit} className="flex flex-col gap-4">
                  <Field label="Application name">
                    <input
                      className={inputCls}
                      style={inputStyle}
                      placeholder="e.g. Payment Gateway Service"
                      value={step2.appName}
                      onChange={(e) => setStep2((p) => ({ ...p, appName: e.target.value }))}
                      required
                    />
                  </Field>

                  <Field label="Technology stack (optional)" hint="Helps with scanner configuration">
                    <input
                      className={inputCls}
                      style={inputStyle}
                      placeholder="e.g. Python, Java, Node.js"
                      value={step2.tech_stack}
                      onChange={(e) => setStep2((p) => ({ ...p, tech_stack: e.target.value }))}
                    />
                  </Field>

                  <div className="grid grid-cols-2 gap-4">
                    <Field label="Business criticality">
                      <Select
                        value={step2.business_criticality}
                        onChange={(v) => setStep2((p) => ({ ...p, business_criticality: v as BusinessCriticality }))}
                        options={[
                          { value: 'critical', label: 'Critical' },
                          { value: 'high', label: 'High' },
                          { value: 'medium', label: 'Medium' },
                          { value: 'low', label: 'Low' },
                        ]}
                      />
                    </Field>
                    <Field label="Environment">
                      <Select
                        value={step2.environment}
                        onChange={(v) => setStep2((p) => ({ ...p, environment: v as Environment }))}
                        options={[
                          { value: 'production', label: 'Production' },
                          { value: 'staging', label: 'Staging' },
                          { value: 'development', label: 'Development' },
                          { value: 'research', label: 'Research' },
                        ]}
                      />
                    </Field>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <Field label="Data sensitivity">
                      <Select
                        value={step2.data_sensitivity}
                        onChange={(v) => setStep2((p) => ({ ...p, data_sensitivity: v as DataSensitivity }))}
                        options={[
                          { value: 'top_secret', label: 'Top Secret' },
                          { value: 'restricted', label: 'Restricted (PII/PHI)' },
                          { value: 'internal', label: 'Internal' },
                          { value: 'public', label: 'Public' },
                        ]}
                      />
                    </Field>
                    <Field label="Confidentiality horizon" hint="How long must data stay secret?">
                      <Select
                        value={step2.confidentiality_requirement}
                        onChange={(v) => setStep2((p) => ({ ...p, confidentiality_requirement: v as ConfidentialityRequirement }))}
                        options={[
                          { value: 'long_term', label: 'Long-term (>10yr)' },
                          { value: 'medium_term', label: 'Medium (1–10yr)' },
                          { value: 'short_term', label: 'Short (<1yr)' },
                        ]}
                      />
                    </Field>
                  </div>

                  <div className="flex items-center gap-3">
                    <input
                      type="checkbox"
                      id="internet-exposed"
                      checked={step2.internet_exposed}
                      onChange={(e) => setStep2((p) => ({ ...p, internet_exposed: e.target.checked }))}
                      className="w-4 h-4 rounded"
                    />
                    <label htmlFor="internet-exposed" className="text-sm">
                      This application is internet-facing
                    </label>
                  </div>

                  {error && (
                    <div className="flex items-center gap-2 text-sm text-red-600 bg-red-50 rounded-xl px-4 py-3">
                      <AlertCircle size={16} />
                      {error}
                    </div>
                  )}

                  <button
                    type="submit"
                    disabled={loading || !step2.appName.trim()}
                    className="flex items-center justify-center gap-2 rounded-full py-3 text-sm font-semibold text-white border-0 cursor-pointer transition-all disabled:opacity-50 mt-2"
                    style={{ background: 'var(--color-accent)' }}
                  >
                    {loading ? <Loader2 size={16} className="animate-spin" /> : null}
                    Create Application
                    <ArrowRight size={16} />
                  </button>
                </form>
              </motion.div>
            )}

            {/* ── Step 3: Confirmation ── */}
            {step === 3 && (
              <motion.div key="step3" {...slideProps()} className="text-center flex flex-col items-center gap-6">
                <div
                  className="w-16 h-16 rounded-full flex items-center justify-center"
                  style={{ background: 'rgba(115,66,226,0.1)' }}
                >
                  <CheckCircle size={32} style={{ color: 'var(--color-accent)' }} />
                </div>

                <div>
                  <h1
                    className="text-2xl mb-2"
                    style={{ fontFamily: 'var(--font-heading)', color: 'var(--color-text)' }}
                  >
                    Project ready
                  </h1>
                  <p className="text-sm opacity-60 max-w-sm">
                    Your organization, project, and application have been created.
                    Proceed to upload source code, certificates, or config files for scanning.
                  </p>
                </div>

                <div
                  className="w-full rounded-xl p-4 text-sm text-left font-mono"
                  style={{ background: 'rgba(25,40,55,0.05)' }}
                >
                  <div className="opacity-50 mb-1 text-xs">IDs (for API use)</div>
                  <div>org: <span className="opacity-70">{createdIds.orgId}</span></div>
                  <div>project: <span className="opacity-70">{createdIds.projectId}</span></div>
                  <div>app: <span className="opacity-70">{createdIds.appId}</span></div>
                </div>

                <div className="flex gap-3 w-full">
                  <button
                    onClick={() => navigate('/dashboard')}
                    className="flex-1 rounded-full py-3 text-sm font-semibold border-0 cursor-pointer transition-all"
                    style={{ background: 'rgba(25,40,55,0.08)', color: 'var(--color-text)' }}
                  >
                    View Dashboard
                  </button>
                  <button
                    onClick={() => navigate('/upload', {
                      state: { applicationId: createdIds.appId, appName: step2.appName }
                    })}
                    className="flex-1 rounded-full py-3 text-sm font-semibold text-white border-0 cursor-pointer transition-all"
                    style={{ background: 'var(--color-accent)' }}
                  >
                    Proceed to Upload →
                  </button>
                </div>

                <p className="text-xs opacity-40">
                  Cryptographic analysis runs in the next phase after upload.
                </p>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}

/**
 * pqcLabApi.ts — Typed client for the QShield PQC Lab API.
 *
 * GET  /api/pqc-lab/capabilities   → PQCCapabilities
 * POST /api/pqc-lab/kem/demo       → KEMDemoResult
 * POST /api/pqc-lab/signature/demo → SignatureDemoResult
 * POST /api/pqc-lab/benchmark      → BenchmarkResult
 *
 * All operations are real cryptographic operations on the backend.
 * No private keys or shared secrets are returned — only fingerprints.
 */

import api from './api';

// ── Types ─────────────────────────────────────────────────────────────────────

export interface PQCEnvironment {
  library: string;
  library_version: string;
  python_version: string;
  platform: string;
  platform_system: string;
  openssl_backend: boolean;
  slhdsa_available: boolean;
}

export interface KEMCapability {
  name: string;
  std_category: string;
  standard: string;
  security_level: string;
  purpose: string;
  operations: string[];
  pub_key_bytes: number;
  ciphertext_bytes: number;
  shared_secret_bytes: number;
}

export interface SigCapability {
  name: string;
  std_category: string;
  standard: string;
  security_level: string;
  purpose: string;
  operations: string[];
  pub_key_bytes: number;
  max_sig_bytes: number;
}

export interface PQCCapabilities {
  environment: PQCEnvironment;
  kem: KEMCapability[];
  signature: SigCapability[];
  slhdsa: { available: boolean; reason: string };
  disclaimer: string;
}

export interface KEMDemoResult {
  param_set: string;
  std_category: string;
  standard: string;
  security_level: string;
  success: boolean;
  verification_message: string;
  timings_ms: {
    key_generation: number;
    encapsulation: number;
    decapsulation: number;
  };
  sizes_bytes: {
    public_key: number;
    private_key: number;
    ciphertext: number;
    shared_secret: number;
  };
  fingerprints: {
    public_key: string;
    shared_secret: string;
  };
  private_key_exposed: boolean;
  shared_secret_exposed: boolean;
  note: string;
  environment: PQCEnvironment;
}

export interface VerificationResult {
  valid: boolean;
  message: string;
}

export interface TamperVerification extends VerificationResult {
  timing_ms: number;
  is_expected_failure: boolean;
}

export interface SignatureDemoResult {
  param_set: string;
  std_category: string;
  standard: string;
  security_level: string;
  message_length_bytes: number;
  original_verification: VerificationResult;
  timings_ms: {
    key_generation: number;
    signing: number;
    verification: number;
  };
  sizes_bytes: {
    public_key: number;
    private_key: number;
    signature: number;
  };
  fingerprints: {
    public_key: string;
    signature: string;
  };
  private_key_exposed: boolean;
  tamper_verification?: TamperVerification;
  environment: PQCEnvironment;
}

export interface BenchmarkStats {
  avg_ms: number;
  min_ms: number;
  max_ms: number;
}

export interface BenchmarkResult {
  param_set: string;
  std_category: string;
  category: 'kem' | 'signature';
  iterations: number;
  statistics: Record<string, BenchmarkStats>;
  sizes_bytes: Record<string, number>;
  environment: PQCEnvironment;
  disclaimer: string;
}

// ── API calls ─────────────────────────────────────────────────────────────────

async function post<T>(path: string, body: unknown): Promise<T> {
  const response = await api.post<T>(path, body);
  return response.data;
}

export async function getCapabilities(): Promise<PQCCapabilities> {
  const response = await api.get<PQCCapabilities>('/api/pqc-lab/capabilities');
  return response.data;
}

export async function runKEMDemo(paramSet: string): Promise<KEMDemoResult> {
  return post('/api/pqc-lab/kem/demo', { param_set: paramSet });
}

export async function runSignatureDemo(
  paramSet: string,
  message: string,
  tamperVerify: boolean,
): Promise<SignatureDemoResult> {
  return post('/api/pqc-lab/signature/demo', {
    param_set: paramSet,
    message,
    tamper_verify: tamperVerify,
  });
}

export async function runBenchmark(paramSet: string, iterations: number): Promise<BenchmarkResult> {
  return post('/api/pqc-lab/benchmark', { param_set: paramSet, iterations });
}

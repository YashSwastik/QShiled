/**
 * api.ts — centralized Axios API client for QShield frontend.
 *
 * All backend calls go through this client. VITE_API_BASE_URL must point to
 * the deployed QShield backend.
 */
import axios from 'axios';

const BASE_URL = import.meta.env.VITE_API_BASE_URL;

export const api = axios.create({
  baseURL: BASE_URL,
  headers: { 'Content-Type': 'application/json' },
  timeout: 15_000,
});

// ── Request interceptor — add auth token when available ──────────────────────
api.interceptors.request.use((config) => {
  // Token support placeholder (Phase auth)
  return config;
});

// ── Response interceptor — normalize errors ───────────────────────────────────
api.interceptors.response.use(
  (res) => res,
  (err) => {
    // Attach a user-friendly message
    const detail =
      err.response?.data?.detail ??
      err.response?.data?.message ??
      err.message ??
      'Unknown error';
    err.userMessage = String(detail);
    return Promise.reject(err);
  }
);

export default api;

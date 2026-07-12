import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Navbar from './components/Navbar';
import LandingPage from './pages/LandingPage';
import OnboardingPage from './pages/OnboardingPage';
import UploadPage from './pages/UploadPage';
import Dashboard from './pages/Dashboard';
import DemoPage from './pages/DemoPage';

/**
 * App — root router.
 *
 * Route map:
 *   /                → Landing page (hero)
 *   /scan            → Project + Application onboarding (Phase 1/2)
 *   /upload          → Secure file upload (Phase B)
 *   /app/dashboard   → Dashboard (Phase 5 placeholder)
 *   /demo            → PQC demo (Phase 7 placeholder)
 */

/** Wrapper that places the Navbar above any page that needs it */
function WithNav({ children }: { children: React.ReactNode }) {
  return (
    <div className="relative">
      {/* Navbar sits absolutely over the video on landing, stacked elsewhere */}
      <div className="absolute top-0 left-0 right-0 z-10">
        <Navbar />
      </div>
      {children}
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Landing — Navbar overlaid on video bg */}
        <Route
          path="/"
          element={
            <WithNav>
              <LandingPage />
            </WithNav>
          }
        />

        {/* Onboarding — create project + application */}
        <Route path="/scan" element={<OnboardingPage />} />

        {/* Upload — secure file ingestion (Phase B) */}
        <Route path="/upload" element={<UploadPage />} />

        {/* Placeholder routes */}
        <Route path="/app/dashboard" element={<Dashboard />} />
        <Route path="/demo" element={<DemoPage />} />

        {/* 404 catch-all */}
        <Route
          path="*"
          element={
            <div className="min-h-dvh flex flex-col items-center justify-center gap-4 px-6 text-center"
                 style={{ background: 'var(--color-login-bg)', color: 'var(--color-text)' }}>
              <h1 className="font-heading text-3xl m-0" style={{ fontFamily: 'var(--font-heading)' }}>
                404
              </h1>
              <p className="opacity-60 m-0">Page not found.</p>
              <a href="/" className="text-sm no-underline" style={{ color: 'var(--color-accent)' }}>
                ← Back to QShield
              </a>
            </div>
          }
        />
      </Routes>
    </BrowserRouter>
  );
}

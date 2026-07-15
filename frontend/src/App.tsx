import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Navbar from './components/Navbar';
import LandingPage from './pages/LandingPage';
import OnboardingPage from './pages/OnboardingPage';
import UploadPage from './pages/UploadPage';
import Dashboard from './pages/Dashboard';
import DemoPage from './pages/DemoPage';
import InventoryPage from './pages/InventoryPage';
import FindingDetailPage from './pages/FindingDetailPage';
import RiskPage from './pages/RiskPage';
import RecommendationsPage from './pages/RecommendationsPage';
import RoadmapPage from './pages/RoadmapPage';

/**
 * App — root router.
 *
 * Route map:
 *   /                               → Landing page
 *   /scan                           → Project + Application onboarding
 *   /upload                         → Secure file upload
 *   /inventory/:scanId              → Crypto Inventory (CBOM)
 *   /inventory/:scanId/finding/:id  → Finding detail
 *   /risk/:scanId                   → Quantum Migration Risk Analysis
 *   /recommendations/:scanId        → Migration Recommendations
 *   /roadmap/:scanId                → Migration Roadmap
 *   /dashboard                     → Executive Dashboard
 *   /app/dashboard                  → redirects to /dashboard (alias)
 *   /demo                           → PQC demo (placeholder)
 */

function WithNav({ children }: { children: React.ReactNode }) {
  return (
    <div className="relative">
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

        {/* Upload — secure file ingestion */}
        <Route path="/upload" element={<UploadPage />} />

        {/* Crypto Inventory (CBOM) */}
        <Route path="/inventory/:scanId" element={<InventoryPage />} />

        {/* Finding detail */}
        <Route path="/inventory/:scanId/finding/:findingId" element={<FindingDetailPage />} />

        {/* Risk Analysis */}
        <Route path="/risk/:scanId" element={<RiskPage />} />

        {/* Migration Recommendations */}
        <Route path="/recommendations/:scanId" element={<RecommendationsPage />} />

        {/* Migration Roadmap */}
        <Route path="/roadmap/:scanId" element={<RoadmapPage />} />

        {/* Dashboard — executive overview */}
        <Route path="/dashboard" element={<Dashboard />} />
        {/* Backward-compat alias for /app/dashboard links already in the wild */}
        <Route path="/app/dashboard" element={<Dashboard />} />
        <Route path="/demo" element={<DemoPage />} />

        {/* 404 catch-all */}
        <Route
          path="*"
          element={
            <div
              className="min-h-dvh flex flex-col items-center justify-center gap-4 px-6 text-center"
              style={{ background: 'var(--color-login-bg)', color: 'var(--color-text)' }}
            >
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

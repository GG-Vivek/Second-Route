import { Suspense, lazy } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { Loader2 } from 'lucide-react'
import { AppShell } from '@/components/shell'
import { ErrorBoundary } from '@/components/ui'
import { HomePage } from '@/pages/HomePage'
import { HealthPage } from '@/pages/HealthPage'
import { UnitsListPage } from '@/pages/UnitsListPage'
import { UnitDetailPage } from '@/pages/UnitDetailPage'
import { NewIntakePage } from '@/pages/NewIntakePage'
import { NewInspectionPage } from '@/pages/NewInspectionPage'
import { DecisionPage } from '@/pages/decision/DecisionPage'
import { BacktestPage } from '@/pages/BacktestPage'

// The analytics page draws its charts with Recharts, which is a large
// library and is needed on one route only. It is fetched when the route is
// opened rather than with the rest of the application.
const AnalyticsPage = lazy(() => import('@/pages/AnalyticsPage'))

function Loading() {
  return (
    <div className="flex items-center justify-center py-24">
      <Loader2 className="size-6 animate-spin text-muted-foreground" aria-hidden="true" />
    </div>
  )
}

export function App() {
  return (
    <AppShell>
      <ErrorBoundary>
        <Suspense fallback={<Loading />}>
          <Routes>
            <Route index element={<HomePage />} />
            <Route path="status" element={<HealthPage />} />
            <Route path="units" element={<UnitsListPage />} />
            <Route path="units/:id" element={<UnitDetailPage />} />
            <Route path="intake/new" element={<NewIntakePage />} />
            <Route path="units/:id/inspection/new" element={<NewInspectionPage />} />
            <Route path="units/:id/decision" element={<DecisionPage />} />
            <Route path="backtest" element={<BacktestPage />} />
            <Route path="analytics" element={<AnalyticsPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Suspense>
      </ErrorBoundary>
    </AppShell>
  )
}

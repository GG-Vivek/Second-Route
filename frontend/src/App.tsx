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
import { SignUpChooserPage } from '@/pages/auth/SignUpChooserPage'
import { RetailerSignUpPage } from '@/pages/auth/RetailerSignUpPage'
import { UserSignUpPage } from '@/pages/auth/UserSignUpPage'
import { SignInPage } from '@/pages/auth/SignInPage'
import { WelcomePage } from '@/pages/welcome/WelcomePage'

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

/**
 * The operator console's pages, inside the application shell.
 */
function ConsoleRoutes() {
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

/**
 * The application. The landing page, the sign-in and the sign-up pages
 * stand on their own, with no shell around them; everything else is the
 * console.
 */
export function App() {
  return (
    <Routes>
      <Route path="welcome" element={<WelcomePage />} />
      <Route path="signup" element={<SignUpChooserPage />} />
      <Route path="signup/retailer" element={<RetailerSignUpPage />} />
      <Route path="signup/user" element={<UserSignUpPage />} />
      <Route path="signin" element={<SignInPage />} />
      <Route path="*" element={<ConsoleRoutes />} />
    </Routes>
  )
}

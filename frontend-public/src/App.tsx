import { Suspense } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { Loader2 } from 'lucide-react'
import { ErrorBoundary } from '@design-system/components/ui'

import { StorefrontHeader } from '@/components/StorefrontHeader'
import { ListingPage } from '@/pages/ListingPage'
import { ListingsPage } from '@/pages/ListingsPage'

/** What is shown while a route is being fetched. */
function Loading() {
  return (
    <div className="flex items-center justify-center py-24">
      <Loader2 className="size-6 animate-spin text-muted-foreground" aria-hidden="true" />
      <span className="sr-only">Loading</span>
    </div>
  )
}

/**
 * The shop window.
 *
 * Two routes: the window itself, and the page for one device.
 */
export function App() {
  return (
    <div className="storefront flex min-h-screen flex-col">
      <ErrorBoundary>
        <StorefrontHeader />
        <main className="flex-1">
          <Suspense fallback={<Loading />}>
            <Routes>
              <Route index element={<ListingsPage />} />
              <Route path="device/:id" element={<ListingPage />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </Suspense>
        </main>
        <footer className="border-t border-border px-6 py-8 text-xs text-muted-foreground">
          <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3">
            <span>SecondRoute. Inspected, priced, ready.</span>
            <span>
              Every device is inspected before it is listed. The price is an estimate, not a
              promise.
            </span>
          </div>
        </footer>
      </ErrorBoundary>
    </div>
  )
}

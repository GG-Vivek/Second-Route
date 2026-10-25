import { Suspense } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { Loader2 } from 'lucide-react'
import { ErrorBoundary } from '@design-system/components/ui'
import { ShaderBackdrop } from '@design-system/components/visual'
import { useTheme } from '@design-system/theme'

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
 * Two routes: the window itself, and the page for one device. Both stand
 * on the same mesh gradient, which belongs to the frame rather than to
 * either page: a buyer who clicks through from the window should not drop
 * out of the room the window was in (F11.8).
 *
 * The frame isolates its own stacking context, so the gradient paints over
 * the frame's background and under the header, the listings and the footer.
 */
export function App() {
  const { resolvedTheme } = useTheme()

  return (
    <div className="storefront relative isolate flex min-h-screen flex-col">
      <ShaderBackdrop
        palette={resolvedTheme === 'dark' ? 'dark' : 'light'}
        className="-z-10"
      />
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

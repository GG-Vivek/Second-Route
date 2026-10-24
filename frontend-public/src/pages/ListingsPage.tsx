import { useEffect, useMemo, useState, type ReactNode } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Search, X } from 'lucide-react'
import { useTheme } from '@design-system/theme'
import { Badge, Callout, EmptyState, Skeleton } from '@design-system/components/ui'
import { ShaderBackdrop, GlassPanel, LiquidGlassFilter } from '@design-system/components/visual'

import { ListingCard } from '@/components/ListingCard'
import { categoryIcon } from '@/components/categoryIcons'
import { describeFailure } from '@/api/client'
import { getListings } from '@/api/listings'

/** How many devices are shown at a time. */
const PAGE_SIZE = 12

/** How long the search waits for the reader to stop typing, in milliseconds. */
const SEARCH_DELAY_MS = 250

/** A value that follows another one, once it has settled for a moment. */
function useSettled<T>(value: T, delay: number): T {
  const [settled, setSettled] = useState(value)
  useEffect(() => {
    const timer = window.setTimeout(() => setSettled(value), delay)
    return () => window.clearTimeout(timer)
  }, [value, delay])
  return settled
}

/**
 * The window: the devices that are for sale (F11.3, F11.5).
 *
 * The top of the page is the pitch, set over the animated gradient. Under it
 * the reader picks a kind of device, or searches for a model. The search waits
 * until the reader has stopped typing, so the window is not asked a question
 * for every letter.
 */
export function ListingsPage() {
  const { resolvedTheme } = useTheme()
  const [search, setSearch] = useState('')
  const [category, setCategory] = useState<string | undefined>(undefined)
  const [shown, setShown] = useState(PAGE_SIZE)
  const settledSearch = useSettled(search.trim(), SEARCH_DELAY_MS)

  const query = useQuery({
    queryKey: ['public-listings', category, settledSearch],
    queryFn: () =>
      getListings({ category, search: settledSearch || undefined, limit: 100 }),
  })

  const items = useMemo(() => query.data?.items ?? [], [query.data])
  const visible = items.slice(0, shown)
  const filtersOn = Boolean(category) || search.trim().length > 0

  const choose = (key: string | undefined) => {
    setCategory(key)
    setShown(PAGE_SIZE)
  }

  return (
    <div>
      {/* The pitch, over the gradient. */}
      <section className="relative isolate overflow-hidden">
        <ShaderBackdrop palette={resolvedTheme === 'dark' ? 'dark' : 'light'} className="-z-10" />
        <LiquidGlassFilter />
        <div className="mx-auto max-w-6xl px-6 pb-10 pt-14 sm:pt-20">
          <h1 className="max-w-2xl text-4xl font-semibold leading-[1.05] tracking-tight sm:text-5xl">
            Refurbished, inspected, priced.
          </h1>
          <p className="mt-4 max-w-xl text-sm text-muted-foreground sm:text-base">
            Every device here has been inspected, tested and priced from the market before it is
            offered. The photographs are of the device you are buying.
          </p>

          <GlassPanel refract className="mt-8 flex max-w-xl flex-wrap items-center gap-2 p-2">
            <div className="relative min-w-0 flex-1">
              <Search
                className="pointer-events-none absolute left-3.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground"
                aria-hidden="true"
              />
              <input
                type="search"
                value={search}
                onChange={(event) => {
                  setSearch(event.target.value)
                  setShown(PAGE_SIZE)
                }}
                placeholder="Search a model, a colour, a size"
                aria-label="Search for a model"
                className="h-11 w-full rounded-xl bg-transparent pl-10 pr-3 text-sm outline-none placeholder:text-muted-foreground focus-visible:ring-2 focus-visible:ring-ring"
              />
            </div>
            {filtersOn && (
              <button
                type="button"
                onClick={() => {
                  setSearch('')
                  choose(undefined)
                }}
                className="inline-flex items-center gap-1 rounded-full px-3 py-2 text-xs text-muted-foreground hover:text-foreground"
              >
                <X className="size-3" aria-hidden="true" />
                Clear
              </button>
            )}
          </GlassPanel>
        </div>
      </section>

      <div className="mx-auto max-w-6xl px-6 pb-16">
        {/* The kinds of device on sale. */}
        <div className="mb-8 flex flex-wrap items-center gap-2" role="group" aria-label="Kinds of device">
          <CategoryChip active={category === undefined} onClick={() => choose(undefined)} label="Everything" />
          {(query.data?.categories ?? []).map((item) => {
            const Icon = categoryIcon(item.key)
            return (
              <CategoryChip
                key={item.key}
                active={category === item.key}
                onClick={() => choose(category === item.key ? undefined : item.key)}
                label={item.label}
                count={item.count}
                icon={<Icon className="size-3.5" aria-hidden="true" />}
              />
            )
          })}
          {query.data && (
            <Badge variant="outline" className="ml-auto">
              {query.data.total} {query.data.total === 1 ? 'device' : 'devices'}
            </Badge>
          )}
        </div>

        {/* The prices are modelled. The page has to say so. */}
        {query.data?.synthetic && (
          <Callout tone="caution" title="These prices are modelled" className="mb-8">
            <p>
              This is a demonstration. The prices on this page come from a model rather than from a
              real market, and the devices are generated ones. Nothing here is for sale.
            </p>
          </Callout>
        )}

        {/* The devices. */}
        {query.isLoading ? (
          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {Array.from({ length: 6 }, (_, index) => (
              <Skeleton key={index} className="h-80" />
            ))}
          </div>
        ) : query.isError ? (
          <Callout tone="warning" title="The shop could not be reached">
            <p>{describeFailure(query.error)}</p>
          </Callout>
        ) : items.length === 0 ? (
          <EmptyState
            title={filtersOn ? 'Nothing matches that' : 'Nothing is on the window'}
            description={
              filtersOn
                ? 'Try a different model, or clear the filter.'
                : 'Devices appear here as soon as they have been inspected and priced.'
            }
          />
        ) : (
          <>
            <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
              {visible.map((listing) => (
                <ListingCard key={listing.id} listing={listing} />
              ))}
            </div>

            {visible.length < items.length && (
              <div className="mt-12 flex justify-center">
                <button
                  type="button"
                  onClick={() => setShown((count) => count + PAGE_SIZE)}
                  className="rounded-full bg-secondary px-6 py-2.5 text-sm font-medium text-secondary-foreground transition-opacity hover:opacity-90"
                >
                  Show more
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}

interface CategoryChipProps {
  active: boolean
  onClick: () => void
  label: string
  count?: number
  icon?: ReactNode
}

/** One kind of device, as a chip the reader can pick. */
function CategoryChip({ active, onClick, label, count, icon }: CategoryChipProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      className={
        active
          ? 'inline-flex items-center gap-1.5 rounded-full bg-primary px-3.5 py-2 text-xs font-medium text-primary-foreground shadow-sm'
          : 'glass-card inline-flex items-center gap-1.5 rounded-full px-3.5 py-2 text-xs font-medium text-muted-foreground transition-colors hover:text-foreground'
      }
    >
      {icon}
      {label}
      {count !== undefined && <span className="tabular opacity-70">{count}</span>}
    </button>
  )
}

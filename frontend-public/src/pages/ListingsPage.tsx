import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Search, X } from 'lucide-react'
import { Badge, Callout, EmptyState, Skeleton } from '@design-system/components/ui'

import { ListingCard } from '@/components/ListingCard'
import { describeFailure } from '@/api/client'
import { getListings } from '@/api/listings'

/** How many devices are shown at a time. */
const PAGE_SIZE = 12

/**
 * The window: the devices that are for sale.
 *
 * The filter is in the page rather than in the address, so that the
 * first thing a reader sees is the devices and not the controls. The
 * family is in the address, because a family is a thing worth sending
 * somebody a link to.
 */
export function ListingsPage() {
  const [search, setSearch] = useState('')
  const [family, setFamily] = useState<string | undefined>(undefined)
  const [shown, setShown] = useState(PAGE_SIZE)

  const query = useQuery({
    queryKey: ['public-listings', family, search],
    queryFn: () => getListings({ family, search: search || undefined, limit: 100 }),
  })

  const items = useMemo(() => query.data?.items ?? [], [query.data])
  const visible = items.slice(0, shown)

  const filtersOn = Boolean(family) || search.length > 0

  return (
    <div className="mx-auto max-w-6xl px-6 py-10">
      {/* The pitch. */}
      <div className="mb-8 max-w-2xl">
        <h1 className="text-3xl font-semibold tracking-tight">Refurbished, inspected, priced.</h1>
        <p className="mt-3 text-sm text-muted-foreground">
          Every device on this page has been inspected, tested and priced from the market
          before it is offered. The photographs are of the device you are buying.
        </p>
      </div>

      {/* The prices are modelled. The page has to say so. */}
      {query.data?.synthetic && (
        <Callout tone="caution" title="These prices are modelled" className="mb-8">
          <p>
            This is a demonstration. The prices on this page come from a model rather than from
            a real market, and the devices are generated ones. Nothing here is for sale.
          </p>
        </Callout>
      )}

      {/* The filter. */}
      <div className="mb-6 flex flex-wrap items-center gap-3">
        <div className="relative">
          <Search
            className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground"
            aria-hidden="true"
          />
          <input
            type="search"
            value={search}
            onChange={(event) => {
              setSearch(event.target.value)
              setShown(PAGE_SIZE)
            }}
            placeholder="Search for a model"
            aria-label="Search for a model"
            className="h-10 w-56 rounded-lg bg-background pl-9 pr-3 text-sm ring-1 ring-border outline-none placeholder:text-muted-foreground focus-visible:ring-2 focus-visible:ring-ring"
          />
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() => {
              setFamily(undefined)
              setShown(PAGE_SIZE)
            }}
            className={
              family === undefined
                ? 'rounded-full bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground'
                : 'rounded-full px-3 py-1.5 text-xs font-medium text-muted-foreground ring-1 ring-border hover:text-foreground'
            }
          >
            Everything
          </button>
          {(query.data?.families ?? []).map((name) => (
            <button
              key={name}
              type="button"
              onClick={() => {
                setFamily(name === family ? undefined : name)
                setShown(PAGE_SIZE)
              }}
              className={
                family === name
                  ? 'rounded-full bg-primary px-3 py-1.5 text-xs font-medium text-primary-foreground'
                  : 'rounded-full px-3 py-1.5 text-xs font-medium text-muted-foreground ring-1 ring-border hover:text-foreground'
              }
            >
              {name}
            </button>
          ))}
        </div>

        {filtersOn && (
          <button
            type="button"
            onClick={() => {
              setFamily(undefined)
              setSearch('')
              setShown(PAGE_SIZE)
            }}
            className="inline-flex items-center gap-1 text-xs text-muted-foreground underline-offset-4 hover:underline"
          >
            <X className="size-3" aria-hidden="true" />
            Clear
          </button>
        )}

        {query.data && (
          <Badge variant="outline" className="ml-auto">
            {query.data.total} {query.data.total === 1 ? 'device' : 'devices'}
          </Badge>
        )}
      </div>

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
            <div className="mt-10 flex justify-center">
              <button
                type="button"
                onClick={() => setShown((count) => count + PAGE_SIZE)}
                className="rounded-full bg-secondary px-5 py-2.5 text-sm font-medium text-secondary-foreground transition-opacity hover:opacity-90"
              >
                Show more
              </button>
            </div>
          )}
        </>
      )}
    </div>
  )
}

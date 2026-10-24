import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { ArrowLeft, Check, X as Cross } from 'lucide-react'
import { Badge, Callout, Skeleton } from '@design-system/components/ui'

import { describeFailure } from '@/api/client'
import { getListing } from '@/api/listings'
import { formatMoney } from '@/types/decision'

/**
 * One device, in full.
 *
 * The photographs, the price, what was tested and what is in the box.
 * The price is an estimate and the page says so, because a price that
 * came from a model is not the same as a price somebody set.
 */
export function ListingPage() {
  const { id } = useParams<{ id: string }>()
  const [photo, setPhoto] = useState(0)

  const query = useQuery({
    queryKey: ['public-listing', id],
    queryFn: () => getListing(id ?? ''),
    enabled: Boolean(id),
  })

  if (query.isLoading) {
    return (
      <div className="mx-auto max-w-6xl px-6 py-10">
        <Skeleton className="h-96" />
      </div>
    )
  }

  if (query.isError) {
    return (
      <div className="mx-auto max-w-2xl px-6 py-20">
        <Callout tone="warning" title="That device could not be shown">
          <p>{describeFailure(query.error)}</p>
          <p className="mt-3">
            <Link to="/" className="underline underline-offset-4">
              Back to the window
            </Link>
          </p>
        </Callout>
      </div>
    )
  }

  const listing = query.data
  if (!listing) {
    return (
      <div className="mx-auto max-w-2xl px-6 py-20">
        <Callout tone="warning" title="That device could not be shown">
          <p>It is no longer on the window.</p>
        </Callout>
      </div>
    )
  }

  const photos = listing.photos.length > 0 ? listing.photos : listing.photo ? [listing.photo] : []
  const current = photos[Math.min(photo, photos.length - 1)]

  return (
    <div className="mx-auto max-w-6xl px-6 py-10">
      <Link
        to="/"
        className="inline-flex items-center gap-1.5 text-sm text-muted-foreground underline-offset-4 hover:text-foreground hover:underline"
      >
        <ArrowLeft className="size-4" aria-hidden="true" />
        Everything
      </Link>

      <div className="mt-6 grid gap-10 lg:grid-cols-[1.2fr_1fr]">
        {/* The photographs. */}
        <div>
          <div className="listing-photo rounded-xl">
            {current ? (
              <img
                src={current.url}
                alt={current.alt}
                width={960}
                height={720}
                className="size-full object-cover"
              />
            ) : (
              <div className="grid size-full place-items-center text-xs text-muted-foreground">
                No photograph
              </div>
            )}
          </div>

          {photos.length > 1 && (
            <div className="mt-3 flex flex-wrap gap-2">
              {photos.map((item, index) => (
                <button
                  key={item.url}
                  type="button"
                  onClick={() => setPhoto(index)}
                  aria-label={`Show photograph ${index + 1}`}
                  aria-current={index === photo}
                  className={
                    index === photo
                      ? 'size-16 overflow-hidden rounded-lg ring-2 ring-ring'
                      : 'size-16 overflow-hidden rounded-lg ring-1 ring-border opacity-70 hover:opacity-100'
                  }
                >
                  <img src={item.url} alt="" className="size-full object-cover" />
                </button>
              ))}
            </div>
          )}
        </div>

        {/* The device. */}
        <div className="flex flex-col gap-6">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant="lime">{listing.condition}</Badge>
              <Badge variant="outline">Grade {listing.grade}</Badge>
              {listing.in_stock && <Badge variant="teal">In stock</Badge>}
            </div>
            <h1 className="mt-3 text-2xl font-semibold tracking-tight">{listing.title}</h1>
            <p className="mt-1 text-sm text-muted-foreground">{listing.summary}</p>
            <p className="mt-1 text-xs text-muted-foreground">
              {listing.category_label} · {listing.color} · {listing.year}
            </p>
          </div>

          <div className="rounded-xl bg-card p-5 ring-1 ring-border">
            <p className="text-3xl font-semibold tabular">
              {formatMoney(listing.price.amount)}
            </p>
            <p className="mt-1 text-xs text-muted-foreground">
              An estimated resale price, not an asking price somebody has set.
              {listing.price.as_of && (
                <> Priced from market data as of {new Date(listing.price.as_of).toLocaleString()}.</>
              )}
            </p>
            {listing.price.source.startsWith('synthetic') && (
              <p className="mt-3 text-xs text-muted-foreground">
                This is a demonstration price. It comes from a model, not from a market.
              </p>
            )}
          </div>

          {listing.highlights.length > 0 && (
            <section>
              <h2 className="text-sm font-semibold">What to know</h2>
              <ul className="mt-2 space-y-1.5 text-sm text-muted-foreground">
                {listing.highlights.map((line) => (
                  <li key={line} className="flex gap-2">
                    <span aria-hidden="true" className="text-lime">
                      ·
                    </span>
                    {line}
                  </li>
                ))}
              </ul>
            </section>
          )}

          {listing.checks.length > 0 && (
            <section>
              <h2 className="text-sm font-semibold">What was tested</h2>
              <ul className="mt-2 divide-y divide-border rounded-xl ring-1 ring-border">
                {listing.checks.map((check) => (
                  <li
                    key={check.name}
                    className="flex items-center gap-2 px-3 py-2 text-sm"
                  >
                    {check.passed ? (
                      <Check className="size-4 text-teal" aria-hidden="true" />
                    ) : (
                      <Cross className="size-4 text-orange" aria-hidden="true" />
                    )}
                    <span className="capitalize">{check.name}</span>
                    <span className="ml-auto text-xs text-muted-foreground">
                      {check.passed ? 'Passed' : 'Failed'}
                    </span>
                  </li>
                ))}
              </ul>
            </section>
          )}

          {listing.accessories.length > 0 && (
            <section>
              <h2 className="text-sm font-semibold">In the box</h2>
              <div className="mt-2 flex flex-wrap gap-2">
                {listing.accessories.map((item) => (
                  <Badge key={item} variant="secondary" className="capitalize">
                    {item}
                  </Badge>
                ))}
              </div>
            </section>
          )}
        </div>
      </div>
    </div>
  )
}

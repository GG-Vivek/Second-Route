import { Link } from 'react-router-dom'
import { Camera, BatteryCharging } from 'lucide-react'
import { Badge } from '@design-system/components/ui'
import { formatMoney } from '@/types/decision'
import type { Listing } from '@/api/listings'

/**
 * The grade, in a colour.
 *
 * The good grades are the calm ones and the poor ones are the loud
 * ones. A reader scanning the window should be able to see the one
 * device that is not good without reading a word.
 */
function gradeVariant(grade: string): 'teal' | 'lime' | 'orange' | 'red' {
  switch (grade) {
    case 'A':
      return 'teal'
    case 'B':
      return 'lime'
    case 'C':
      return 'orange'
    default:
      return 'red'
  }
}

/**
 * One device, on the window.
 *
 * The photograph, the name, the condition and the price. Nothing else:
 * the rest is on the device's own page.
 */
export function ListingCard({ listing }: { listing: Listing }) {
  return (
    <Link
      to={`/device/${listing.id}`}
      className="group flex flex-col overflow-hidden rounded-xl bg-card text-card-foreground ring-1 ring-border transition-shadow hover:shadow-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
    >
      <div className="listing-photo">
        {listing.photo ? (
          <img
            src={listing.photo.url}
            alt={listing.photo.alt}
            loading="lazy"
            width={640}
            height={480}
          />
        ) : (
          <div className="grid size-full place-items-center text-xs text-muted-foreground">
            No photograph
          </div>
        )}
      </div>

      <div className="flex flex-1 flex-col gap-3 p-4">
        <div className="flex items-start justify-between gap-3">
          <h3 className="text-sm font-semibold leading-snug group-hover:underline">
            {listing.title}
          </h3>
          <Badge variant={gradeVariant(listing.grade)}>{listing.condition}</Badge>
        </div>

        <p className="text-xs text-muted-foreground">
          {listing.color} · {listing.ram_gb} GB memory · {listing.storage_gb}
        </p>

        <div className="mt-auto flex items-end justify-between gap-3 pt-1">
          <div>
            <p className="text-lg font-semibold tabular">
              {formatMoney(listing.price.amount)}
            </p>
            <p className="text-[11px] text-muted-foreground">estimated resale price</p>
          </div>
          <div className="flex items-center gap-2 text-[11px] text-muted-foreground">
            {listing.battery_health_pct && (
              <span className="inline-flex items-center gap-1">
                <BatteryCharging className="size-3" aria-hidden="true" />
                {listing.battery_health_pct}%
              </span>
            )}
            {listing.photo_count > 0 && (
              <span className="inline-flex items-center gap-1">
                <Camera className="size-3" aria-hidden="true" />
                {listing.photo_count}
              </span>
            )}
          </div>
        </div>
      </div>
    </Link>
  )
}

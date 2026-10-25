import { Link } from 'react-router-dom'
import { Camera, BatteryCharging, MessageCircle } from 'lucide-react'
import { Badge } from '@design-system/components/ui'
import { formatMoney } from '@/types/decision'
import type { Listing } from '@/api/listings'
import { categoryIcon } from '@/components/categoryIcons'
import { getWhatsAppBuyUrl } from '@/utils/whatsapp'

/**
 * The grade, in a colour.
 *
 * The good grades are the calm ones and the poor ones are the loud ones. A
 * reader scanning the window should be able to see the one device that is not
 * good without reading a word.
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
 * One device, on the window (F11.3).
 *
 * The photograph, the kind of device, the name, the condition and the price.
 * The line under the name is written for the device: a phone's storage and
 * colour, a television's size, never a memory figure for a thing that has none.
 */
export function ListingCard({ listing }: { listing: Listing }) {
  const Icon = categoryIcon(listing.category)

  return (
    <Link
      to={`/device/${listing.id}`}
      className="group glass-card flex flex-col overflow-hidden rounded-2xl transition duration-300 hover:-translate-y-0.5 hover:shadow-xl focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
    >
      <div className="listing-photo relative">
        {listing.photo ? (
          <img src={listing.photo.url} alt={listing.photo.alt} loading="lazy" width={640} height={480} />
        ) : (
          <div className="grid size-full place-items-center text-xs text-muted-foreground">No photograph</div>
        )}
        <span className="absolute left-3 top-3 inline-flex items-center gap-1.5 rounded-full bg-background/75 px-2.5 py-1 text-[11px] font-medium text-foreground backdrop-blur">
          <Icon className="size-3.5" aria-hidden="true" />
          {listing.category_label}
        </span>
      </div>

      <div className="flex flex-1 flex-col gap-3 p-5">
        <div className="flex items-start justify-between gap-3">
          <h3 className="text-sm font-semibold leading-snug group-hover:underline">{listing.title}</h3>
          <Badge variant={gradeVariant(listing.grade)}>{listing.condition}</Badge>
        </div>

        <p className="text-xs leading-relaxed text-muted-foreground">{listing.summary}</p>

        <div className="mt-auto flex items-end justify-between gap-3 pt-2">
          <div>
            <p className="text-lg font-semibold tabular">{formatMoney(listing.price.amount)}</p>
            <p className="text-[11px] text-muted-foreground">estimated resale price</p>
          </div>
          <button
            type="button"
            onClick={(e) => {
              e.preventDefault()
              e.stopPropagation()
              window.open(getWhatsAppBuyUrl(listing), '_blank', 'noopener,noreferrer')
            }}
            className="inline-flex items-center gap-1.5 rounded-full bg-primary px-3.5 py-1.5 text-xs font-semibold text-primary-foreground shadow-sm transition-all hover:bg-primary/85 hover:shadow active:scale-95"
            aria-label={`Buy ${listing.title} on WhatsApp`}
          >
            <MessageCircle className="size-3.5" aria-hidden="true" />
            Buy
          </button>
        </div>

        {(listing.battery_health_pct || listing.photo_count > 0) && (
          <div className="flex items-center gap-3 border-t border-border/40 pt-2 text-[11px] text-muted-foreground">
            {listing.battery_health_pct && (
              <span className="inline-flex items-center gap-1">
                <BatteryCharging className="size-3" aria-hidden="true" />
                {listing.battery_health_pct}% battery
              </span>
            )}
            {listing.photo_count > 0 && (
              <span className="inline-flex items-center gap-1">
                <Camera className="size-3" aria-hidden="true" />
                {listing.photo_count} photos
              </span>
            )}
          </div>
        )}
      </div>
    </Link>
  )
}

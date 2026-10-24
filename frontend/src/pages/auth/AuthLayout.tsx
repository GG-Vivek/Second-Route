import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { useTheme } from '@/theme'
import { ShaderBackdrop, GlassPanel, LiquidGlassFilter, LiquidLogo } from '@/components/visual'

export interface AuthLayoutProps {
  title: string
  lead?: string
  children: ReactNode
  /** Links under the form, such as "Already have an account?". */
  footer?: ReactNode
}

/**
 * The frame every sign-in and sign-up page sits in (F11.5, F11.6).
 *
 * The mesh gradient is the room; the form is a glass panel in it. The brand
 * and a short statement of what the product does sit alongside, so a person
 * arriving cold knows what the account is for before they fill anything in.
 */
export function AuthLayout({ title, lead, children, footer }: AuthLayoutProps) {
  const { resolvedTheme } = useTheme()

  return (
    <div className="relative min-h-screen overflow-hidden bg-background text-foreground">
      <ShaderBackdrop palette={resolvedTheme === 'dark' ? 'dark' : 'light'} />
      <LiquidGlassFilter />

      <div className="relative mx-auto grid min-h-screen max-w-6xl items-center gap-12 px-6 py-12 lg:grid-cols-[1fr_minmax(0,28rem)]">
        <div className="hidden lg:block">
          <Link to="/" className="inline-flex items-center gap-3 text-sm font-semibold tracking-tight">
            <LiquidLogo size={36} />
            SecondRoute
          </Link>
          <h2 className="mt-10 max-w-md text-4xl font-semibold leading-tight tracking-tight">
            One return in. One decision out.
          </h2>
          <p className="mt-4 max-w-md text-sm text-muted-foreground">
            Every returned device is inspected, valued and sent to the channel that pays the most,
            with the reasons written down. Accounts keep each retailer's stock and decisions apart.
          </p>
        </div>

        <GlassPanel refract className="p-8 sm:p-10">
          <div className="lg:hidden mb-6 flex items-center gap-2 text-sm font-semibold">
            <LiquidLogo size={24} />
            SecondRoute
          </div>
          <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
          {lead && <p className="mt-2 text-sm text-muted-foreground">{lead}</p>}
          <div className="mt-8">{children}</div>
          {footer && <div className="mt-8 border-t border-border pt-6 text-sm text-muted-foreground">{footer}</div>}
        </GlassPanel>
      </div>
    </div>
  )
}

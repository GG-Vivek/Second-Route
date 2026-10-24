import { Link } from 'react-router-dom'
import { Store, UserPlus, ArrowRight } from 'lucide-react'
import { AuthLayout } from './AuthLayout'

/**
 * Where a sign-up begins: a retailer, or a person who works for one.
 *
 * The two are different accounts. A retailer owns its stock and its
 * decisions; a person joins one with its code and inspects for it.
 */
export function SignUpChooserPage() {
  return (
    <AuthLayout
      title="Create an account"
      lead="Who are you signing up as?"
      footer={
        <p>
          Already have an account?{' '}
          <Link to="/signin" className="font-medium text-foreground underline-offset-4 hover:underline">
            Sign in
          </Link>
        </p>
      }
    >
      <div className="grid gap-3">
        <Link
          to="/signup/retailer"
          className="group flex items-start gap-4 rounded-xl bg-background/60 p-5 ring-1 ring-border transition-colors hover:ring-ring focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <span className="grid size-10 shrink-0 place-items-center rounded-lg bg-lime-container text-lime-on">
            <Store className="size-5" aria-hidden="true" />
          </span>
          <span className="flex-1">
            <span className="block text-sm font-semibold">I run a retailer</span>
            <span className="mt-1 block text-xs text-muted-foreground">
              Create your organisation. You become its administrator and can invite your staff.
            </span>
          </span>
          <ArrowRight className="mt-1 size-4 text-muted-foreground transition-transform group-hover:translate-x-0.5" aria-hidden="true" />
        </Link>

        <Link
          to="/signup/user"
          className="group flex items-start gap-4 rounded-xl bg-background/60 p-5 ring-1 ring-border transition-colors hover:ring-ring focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <span className="grid size-10 shrink-0 place-items-center rounded-lg bg-teal-container text-teal-on">
            <UserPlus className="size-5" aria-hidden="true" />
          </span>
          <span className="flex-1">
            <span className="block text-sm font-semibold">I work for a retailer</span>
            <span className="mt-1 block text-xs text-muted-foreground">
              Join your retailer with the code it gave you, as an inspector.
            </span>
          </span>
          <ArrowRight className="mt-1 size-4 text-muted-foreground transition-transform group-hover:translate-x-0.5" aria-hidden="true" />
        </Link>
      </div>
    </AuthLayout>
  )
}

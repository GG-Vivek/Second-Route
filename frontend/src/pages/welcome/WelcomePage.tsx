import { Link } from 'react-router-dom'
import { ArrowRight, ClipboardCheck, Scale, Search, ShoppingBag, Store, TrendingUp } from 'lucide-react'
import { useTheme } from '@/theme'
import { ButtonLink } from '@/components/ui'
import { Reveal } from '@/components/motion'
import { GlassPanel, LiquidGlassFilter, LiquidLogo, ShaderBackdrop } from '@/components/visual'
import { SHOP_WINDOW } from './shopWindow'

/** The three moves a return makes, in the order it makes them. */
const STEPS = [
  {
    icon: Search,
    title: 'Intake and inspection',
    body: 'Photographs of the four angles and of the label, the serial, the condition, and a battery reading — or none at all, because a television has none.',
  },
  {
    icon: Scale,
    title: 'The decision',
    body: 'Five channels — refurbish, open-box, parts, recycle, vendor return — each priced by a Monte Carlo over what the market actually paid, each with its own chance of being the best one.',
  },
  {
    icon: ClipboardCheck,
    title: 'The record',
    body: 'The reason, the threshold, and the conditions that would flip it. Accept the recommendation or override it with a reason of your own; either way it is written down.',
  },
] as const

/** What the engine is judged on, which is the point of building it. */
const MEASURED = [
  {
    icon: TrendingUp,
    title: 'Net recovered per return',
    body: 'Against what the partner would have recovered without the engine. The one number the product exists to move.',
  },
  {
    icon: Scale,
    title: 'Regret and calibration',
    body: 'What a decision cost against the best that could have been done, and whether the confidence it showed was earned.',
  },
  {
    icon: ClipboardCheck,
    title: 'A source and an as-of on every number',
    body: 'No price, no cost and no metric without where it came from and when it was true. Modelled figures say that they are modelled.',
  },
] as const

/**
 * The landing page (F11.10).
 *
 * The first thing a person who has never seen the product reads: what it
 * does, what it is measured against, and two doors out of the page — a
 * retailer goes to the console's sign-up, a buyer goes to the shop
 * window. Sign-up and sign-in are in the header, in the hero and at the
 * foot, so nobody has to scroll to find the way in.
 *
 * The sections reveal themselves as the reader scrolls, which is the
 * motion F11.9 allows: no dependency, and nothing hidden from a reader
 * who has asked for less of it. `Reveal` decides that; this page only
 * says which parts of it arrive together.
 */
export function WelcomePage() {
  const { resolvedTheme } = useTheme()

  return (
    <div className="relative isolate min-h-screen bg-background text-foreground">
      <ShaderBackdrop
        palette={resolvedTheme === 'dark' ? 'dark' : 'light'}
        // Behind everything on the page and above the surface it sits on:
        // the frame isolates its own stacking context, so a negative index
        // paints above the background here and below the text (F11.8).
        className="-z-10"
      />
      <LiquidGlassFilter />

      <header className="sticky top-0 z-10 border-b border-border/60 bg-background/70 backdrop-blur-md">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-6">
          <Link
            to="/welcome"
            className="inline-flex items-center gap-2.5 text-sm font-semibold tracking-tight"
          >
            <LiquidLogo size={26} />
            SecondRoute
          </Link>
          <nav aria-label="Accounts" className="flex items-center gap-2">
            <ButtonLink href="/signin" variant="ghost">
              Sign in
            </ButtonLink>
            <ButtonLink href="/signup">Create an account</ButtonLink>
          </nav>
        </div>
      </header>

      <main>
        {/* The hero: what the product is, and the two ways in. */}
        <Reveal
          as="section"
          className="mx-auto max-w-6xl px-6 pt-20 pb-16 text-center sm:pt-28"
          aria-labelledby="hero"
        >
          <p className="text-xs font-medium uppercase tracking-[0.24em] text-muted-foreground">
            The disposition engine for returned electronics
          </p>
          <h1
            id="hero"
            className="mx-auto mt-6 max-w-3xl text-4xl font-semibold leading-[1.05] tracking-tight sm:text-6xl"
          >
            One return in. One decision out.
          </h1>
          <p className="mx-auto mt-6 max-w-2xl text-base leading-relaxed text-muted-foreground sm:text-lg">
            Every returned device is inspected, valued against what the market actually paid, and
            sent to the channel that pays the most — with the reasons written down, so a decision
            can be argued with instead of trusted.
          </p>
          <div className="mt-9 flex flex-wrap items-center justify-center gap-3">
            <ButtonLink href="/signup" size="lg">
              Create an account
            </ButtonLink>
            <ButtonLink href="/signin" size="lg" variant="outline">
              Sign in
            </ButtonLink>
          </div>
        </Reveal>

        {/* How a return becomes a decision. */}
        <Reveal as="section" className="mx-auto max-w-6xl px-6 py-12" aria-labelledby="how">
          <h2 id="how" className="text-center text-2xl font-semibold tracking-tight sm:text-3xl">
            How a return becomes a decision
          </h2>
          <div className="mt-8 grid gap-5 md:grid-cols-3">
            {STEPS.map((step, index) => (
              <GlassPanel key={step.title} className="rounded-3xl p-6">
                <div className="flex items-center gap-3">
                  <span className="inline-flex size-9 items-center justify-center rounded-2xl bg-primary/15 text-primary">
                    <step.icon className="size-5" aria-hidden="true" />
                  </span>
                  <span className="text-xs font-medium text-muted-foreground">
                    Step {index + 1}
                  </span>
                </div>
                <h3 className="mt-4 text-base font-semibold tracking-tight">{step.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{step.body}</p>
              </GlassPanel>
            ))}
          </div>
        </Reveal>

        {/* What the decision is measured against. */}
        <Reveal as="section" className="mx-auto max-w-6xl px-6 py-12" aria-labelledby="measured">
          <h2 id="measured" className="text-center text-2xl font-semibold tracking-tight sm:text-3xl">
            What the decision is measured against
          </h2>
          <div className="mt-8 grid gap-5 md:grid-cols-3">
            {MEASURED.map((item) => (
              <GlassPanel key={item.title} className="rounded-3xl p-6">
                <item.icon className="size-5 text-lime" aria-hidden="true" />
                <h3 className="mt-4 text-base font-semibold tracking-tight">{item.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{item.body}</p>
              </GlassPanel>
            ))}
          </div>
        </Reveal>

        {/* The two doors: a retailer into the console, a buyer to the window. */}
        <Reveal as="section" className="mx-auto max-w-6xl px-6 py-12" aria-labelledby="who">
          <h2 id="who" className="text-center text-2xl font-semibold tracking-tight sm:text-3xl">
            Who it is for
          </h2>
          <div className="mt-8 grid gap-5 md:grid-cols-2">
            <GlassPanel refract className="rounded-3xl p-7">
              <span className="inline-flex items-center gap-2 text-xs font-medium uppercase tracking-[0.18em] text-muted-foreground">
                <Store className="size-4 text-teal" aria-hidden="true" />
                For a retailer
              </span>
              <h3 className="mt-4 text-xl font-semibold tracking-tight">
                Returns are stock until somebody decides what they are.
              </h3>
              <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
                Inspect, decide, override, and see how often the engine was right — for your
                organisation only, with every decision kept as it was made.
              </p>
              <div className="mt-6 flex flex-wrap items-center gap-3">
                <ButtonLink href="/signup/retailer">Create a retailer account</ButtonLink>
                <Link
                  to="/signup/user"
                  className="text-sm font-medium text-foreground underline-offset-4 hover:underline"
                >
                  Join one with its code
                </Link>
              </div>
            </GlassPanel>

            <GlassPanel refract className="rounded-3xl p-7">
              <span className="inline-flex items-center gap-2 text-xs font-medium uppercase tracking-[0.18em] text-muted-foreground">
                <ShoppingBag className="size-4 text-teal" aria-hidden="true" />
                For a buyer
              </span>
              <h3 className="mt-4 text-xl font-semibold tracking-tight">
                Every device the engine has cleared, graded and priced.
              </h3>
              <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
                The shop window is where a retailer's stock goes once it has been judged: the
                grade, the grade's reason, and the price — modelled, and labelled as modelled.
              </p>
              <div className="mt-6 flex flex-wrap items-center gap-3">
                <ButtonLink href={SHOP_WINDOW} external variant="secondary">
                  Browse the shop window
                  <ArrowRight className="size-4" aria-hidden="true" />
                </ButtonLink>
              </div>
            </GlassPanel>
          </div>
        </Reveal>

        {/* The way in, again, for a reader who read to the end. */}
        <Reveal as="section" className="mx-auto max-w-6xl px-6 py-14 text-center" aria-labelledby="start">
          <GlassPanel className="rounded-3xl px-6 py-12 sm:px-12">
            <h2 id="start" className="text-2xl font-semibold tracking-tight sm:text-3xl">
              Start with one return.
            </h2>
            <p className="mx-auto mt-3 max-w-xl text-sm leading-relaxed text-muted-foreground">
              An account is a retailer and its people: an administrator who signs up, and
              inspectors who join with the code the retailer gave them.
            </p>
            <div className="mt-7 flex flex-wrap items-center justify-center gap-3">
              <ButtonLink href="/signup" size="lg">
                Create an account
              </ButtonLink>
              <ButtonLink href="/signin" size="lg" variant="outline">
                Sign in
              </ButtonLink>
            </div>
          </GlassPanel>
        </Reveal>
      </main>

      <footer className="border-t border-border/60 py-8">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-6 text-xs text-muted-foreground">
          <span>SecondRoute. One return in, one disposition instruction out.</span>
          <span>Prices in the window are modelled, and the window says so.</span>
        </div>
      </footer>
    </div>
  )
}

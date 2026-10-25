import { Link } from 'react-router-dom'
import { ArrowRight, CheckCircle2, ClipboardCheck, Scale, Search, ShieldCheck, ShoppingBag, Sparkles, Store, TrendingUp } from 'lucide-react'
import { useTheme } from '@/theme'
import { ButtonLink } from '@/components/ui'
import { ThemeToggle } from '@/components/shell'
import { Reveal } from '@/components/motion'
import { GlassPanel, HeroInspectionCard, LiquidGlassFilter, LiquidLogo, ShaderBackdrop } from '@/components/visual'
import { SHOP_WINDOW } from './shopWindow'

/** The three moves a return makes, in the order it makes them. */
const STEPS = [
  {
    icon: Search,
    step: '01',
    title: 'Intake and inspection',
    body: 'Photographs of the four angles and of the label, the serial, the condition, and a battery reading — or none at all, because a television has none.',
    tag: 'Computer Vision & Specs',
  },
  {
    icon: Scale,
    step: '02',
    title: 'The decision',
    body: 'Five channels — refurbish, open-box, parts, recycle, vendor return — each priced by a Monte Carlo over what the market actually paid, each with its own chance of being the best one.',
    tag: 'Monte Carlo Pricing',
  },
  {
    icon: ClipboardCheck,
    step: '03',
    title: 'The record',
    body: 'The reason, the threshold, and the conditions that would flip it. Accept the recommendation or override it with a reason of your own; either way it is written down.',
    tag: 'Immutable Audit Trail',
  },
] as const

/** What the engine is judged on, which is the point of building it. */
const MEASURED = [
  {
    icon: TrendingUp,
    title: 'Net recovered per return',
    body: 'Against what the partner would have recovered without the engine. The one number the product exists to move.',
    metric: '+$84 avg recovery lift',
  },
  {
    icon: Scale,
    title: 'Regret and calibration',
    body: 'What a decision cost against the best that could have been done, and whether the confidence it showed was earned.',
    metric: 'Brier calibration score',
  },
  {
    icon: ShieldCheck,
    title: 'A source and an as-of on every number',
    body: 'No price, no cost and no metric without where it came from and when it was true. Modelled figures say that they are modelled.',
    metric: '100% provenance audit',
  },
] as const

/**
 * The landing page (F11.10).
 *
 * Designed with cues from react-three-fiber, shadergradient, liquid-glass-js,
 * liquid-logo, and theatre-js:
 *
 * - Liquid fluid backdrop with mouse distortion and soft domain warping
 * - Dynamic liquid glass panels with interactive specular tracking
 * - 3D disposition hologram visualizer in the hero with cursor tilt
 * - Fluid reactive brand logo with organic ripple
 * - Staggered Theatre-style choreography across sections
 */
export function WelcomePage() {
  const { resolvedTheme } = useTheme()

  return (
    <div className="relative isolate min-h-screen bg-background text-foreground selection:bg-primary/20 selection:text-primary">
      <ShaderBackdrop
        palette={resolvedTheme === 'dark' ? 'dark' : 'light'}
        // Behind everything on the page and above the surface it sits on:
        // the frame isolates its own stacking context, so a negative index
        // paints above the background here and below the text (F11.8).
        className="-z-10"
      />
      <LiquidGlassFilter />

      <header className="sticky top-0 z-30 border-b border-border/60 bg-background/70 backdrop-blur-md transition-colors">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-6">
          <Link
            to="/welcome"
            className="group inline-flex items-center gap-2.5 text-sm font-semibold tracking-tight transition-opacity hover:opacity-90"
          >
            <LiquidLogo size={28} />
            <span className="font-semibold tracking-tight">SecondRoute</span>
          </Link>
          <div className="flex items-center gap-2.5">
            <ThemeToggle />
            <nav aria-label="Accounts" className="flex items-center gap-2">
              <ButtonLink href="/signin" variant="ghost">
                Sign in
              </ButtonLink>
              <ButtonLink href="/signup">Create an account</ButtonLink>
            </nav>
          </div>
        </div>
      </header>

      <main>
        {/* The hero: what the product is, and the two ways in. */}
        <Reveal
          as="section"
          className="mx-auto max-w-6xl px-6 pt-16 pb-16 text-center sm:pt-24"
          aria-labelledby="hero"
        >
          <div className="inline-flex items-center gap-2 rounded-full border border-primary/30 bg-primary/10 px-3.5 py-1 text-xs font-semibold tracking-wide text-primary shadow-sm backdrop-blur-sm">
            <Sparkles className="size-3.5" aria-hidden="true" />
            <span>The disposition engine for returned electronics</span>
          </div>

          <h1
            id="hero"
            className="mx-auto mt-6 max-w-3xl text-4xl font-semibold leading-[1.08] tracking-tight sm:text-6xl"
          >
            One return in.{' '}
            <span className="bg-gradient-to-r from-primary via-teal to-lime bg-clip-text text-transparent">
              One decision out.
            </span>
          </h1>

          <p className="mx-auto mt-6 max-w-2xl text-base leading-relaxed text-muted-foreground sm:text-lg">
            Every returned device is inspected, valued against what the market actually paid, and
            sent to the channel that pays the most — with the reasons written down, so a decision
            can be argued with instead of trusted.
          </p>

          <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
            <ButtonLink href="/signup" size="lg" className="shadow-lg shadow-primary/20">
              Create an account
              <ArrowRight className="size-4" aria-hidden="true" />
            </ButtonLink>
            <ButtonLink href="/signin" size="lg" variant="outline">
              Sign in
            </ButtonLink>
          </div>

          {/* Interactive 3D Disposition Hologram Card (react-three-fiber + liquid-glass) */}
          <HeroInspectionCard />
        </Reveal>

        {/* How a return becomes a decision. */}
        <Reveal as="section" className="mx-auto max-w-6xl px-6 py-14" aria-labelledby="how">
          <div className="text-center">
            <span className="text-xs font-semibold uppercase tracking-widest text-primary">Process</span>
            <h2 id="how" className="mt-1 text-2xl font-semibold tracking-tight sm:text-3xl">
              How a return becomes a decision
            </h2>
          </div>

          <div className="mt-10 grid gap-6 md:grid-cols-3">
            {STEPS.map((step) => (
              <GlassPanel
                key={step.title}
                className="flex flex-col justify-between rounded-3xl p-7 transition-transform hover:-translate-y-1.5"
              >
                <div>
                  <div className="flex items-center justify-between">
                    <span className="inline-flex size-10 items-center justify-center rounded-2xl border border-primary/30 bg-primary/15 text-primary shadow-sm">
                      <step.icon className="size-5" aria-hidden="true" />
                    </span>
                    <span className="font-mono text-xs font-semibold text-muted-foreground">
                      Step {step.step}
                    </span>
                  </div>

                  <h3 className="mt-5 text-lg font-semibold tracking-tight">{step.title}</h3>
                  <p className="mt-2.5 text-sm leading-relaxed text-muted-foreground">{step.body}</p>
                </div>

                <div className="mt-6 border-t border-border/40 pt-4">
                  <span className="inline-flex items-center gap-1.5 text-[11px] font-mono text-primary">
                    <CheckCircle2 className="size-3" aria-hidden="true" />
                    {step.tag}
                  </span>
                </div>
              </GlassPanel>
            ))}
          </div>
        </Reveal>

        {/* What the decision is measured against. */}
        <Reveal as="section" className="mx-auto max-w-6xl px-6 py-14" aria-labelledby="measured">
          <div className="text-center">
            <span className="text-xs font-semibold uppercase tracking-widest text-primary">Accountability</span>
            <h2 id="measured" className="mt-1 text-2xl font-semibold tracking-tight sm:text-3xl">
              What the decision is measured against
            </h2>
          </div>

          <div className="mt-10 grid gap-6 md:grid-cols-3">
            {MEASURED.map((item) => (
              <GlassPanel
                key={item.title}
                className="flex flex-col justify-between rounded-3xl p-7 transition-transform hover:-translate-y-1.5"
              >
                <div>
                  <span className="inline-flex size-10 items-center justify-center rounded-2xl border border-lime/30 bg-lime/15 text-lime shadow-sm">
                    <item.icon className="size-5" aria-hidden="true" />
                  </span>
                  <h3 className="mt-5 text-lg font-semibold tracking-tight">{item.title}</h3>
                  <p className="mt-2.5 text-sm leading-relaxed text-muted-foreground">{item.body}</p>
                </div>

                <div className="mt-6 border-t border-border/40 pt-4">
                  <span className="font-mono text-xs font-medium text-lime">{item.metric}</span>
                </div>
              </GlassPanel>
            ))}
          </div>
        </Reveal>

        {/* The two doors: a retailer into the console, a buyer to the window. */}
        <Reveal as="section" className="mx-auto max-w-6xl px-6 py-14" aria-labelledby="who">
          <div className="text-center">
            <span className="text-xs font-semibold uppercase tracking-widest text-primary">Access</span>
            <h2 id="who" className="mt-1 text-2xl font-semibold tracking-tight sm:text-3xl">
              Who it is for
            </h2>
          </div>

          <div className="mt-10 grid gap-6 md:grid-cols-2">
            <GlassPanel refract className="rounded-3xl p-8 transition-transform hover:-translate-y-1.5">
              <span className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.18em] text-primary">
                <Store className="size-4 text-primary" aria-hidden="true" />
                For a retailer
              </span>
              <h3 className="mt-4 text-xl font-semibold tracking-tight sm:text-2xl">
                Returns are stock until somebody decides what they are.
              </h3>
              <p className="mt-3 text-sm leading-relaxed text-muted-foreground sm:text-base">
                Inspect, decide, override, and see how often the engine was right — for your
                organisation only, with every decision kept as it was made.
              </p>
              <div className="mt-7 flex flex-wrap items-center gap-3">
                <ButtonLink href="/signup/retailer">Create a retailer account</ButtonLink>
                <Link
                  to="/signup/user"
                  className="text-sm font-medium text-foreground underline-offset-4 hover:underline"
                >
                  Join one with its code
                </Link>
              </div>
            </GlassPanel>

            <GlassPanel refract className="rounded-3xl p-8 transition-transform hover:-translate-y-1.5">
              <span className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.18em] text-teal">
                <ShoppingBag className="size-4 text-teal" aria-hidden="true" />
                For a buyer
              </span>
              <h3 className="mt-4 text-xl font-semibold tracking-tight sm:text-2xl">
                Every device the engine has cleared, graded and priced.
              </h3>
              <p className="mt-3 text-sm leading-relaxed text-muted-foreground sm:text-base">
                The shop window is where a retailer's stock goes once it has been judged: the
                grade, the grade's reason, and the price — modelled, and labelled as modelled.
              </p>
              <div className="mt-7 flex flex-wrap items-center gap-3">
                <ButtonLink href={SHOP_WINDOW} external variant="secondary">
                  Browse the shop window
                  <ArrowRight className="size-4" aria-hidden="true" />
                </ButtonLink>
              </div>
            </GlassPanel>
          </div>
        </Reveal>

        {/* The way in, again, for a reader who read to the end. */}
        <Reveal as="section" className="mx-auto max-w-6xl px-6 py-16 text-center" aria-labelledby="start">
          <GlassPanel className="relative overflow-hidden rounded-3xl px-6 py-14 sm:px-12">
            <div className="pointer-events-none absolute -top-24 left-1/2 size-72 -translate-x-1/2 rounded-full bg-primary/10 blur-3xl" />
            <h2 id="start" className="text-2xl font-semibold tracking-tight sm:text-4xl">
              Start with one return.
            </h2>
            <p className="mx-auto mt-4 max-w-xl text-sm leading-relaxed text-muted-foreground sm:text-base">
              An account is a retailer and its people: an administrator who signs up, and
              inspectors who join with the code the retailer gave them.
            </p>
            <div className="mt-8 flex flex-wrap items-center justify-center gap-3">
              <ButtonLink href="/signup" size="lg" className="shadow-lg shadow-primary/20">
                Create an account
              </ButtonLink>
              <ButtonLink href="/signin" size="lg" variant="outline">
                Sign in
              </ButtonLink>
            </div>
          </GlassPanel>
        </Reveal>
      </main>

      <footer className="border-t border-border/60 py-8 backdrop-blur-sm">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-6 text-xs text-muted-foreground">
          <span>SecondRoute. One return in, one disposition instruction out.</span>
          <span>Prices in the window are modelled, and the window says so.</span>
        </div>
      </footer>
    </div>
  )
}

import { lazy, Suspense, useMemo, useState } from 'react'
import { CheckCircle2, ChevronRight, Cpu, Layers, Sparkles, TrendingUp } from 'lucide-react'
import { supportsWebGL } from '../../three/webgl'
import { cn } from '@/utils/cn'
import { GlassPanel } from './LiquidGlass'

const HeroPrismCanvas = lazy(() => import('../../three/HeroPrismCanvas'))

interface ChannelStat {
  name: string
  label: string
  recovery: string
  confidence: number
  isBest?: boolean
  detail: string
  flipNote: string
}

const CHANNELS_DATA: ChannelStat[] = [
  {
    name: 'Refurbish',
    label: 'Refurbish',
    recovery: '$412.50',
    confidence: 94,
    isBest: true,
    detail: 'Grade A screen restoration + battery replacement. Verified margin: +$144.50 vs baseline.',
    flipNote: 'Flips to Open-Box if replacement part cost exceeds $118.',
  },
  {
    name: 'Open-Box',
    label: 'Open-Box',
    recovery: '$340.00',
    confidence: 72,
    detail: 'Clean cosmetic grade, original box intact. Immediate resale with zero bench labor.',
    flipNote: 'Flips to Refurbish if Grade A refurbished secondary market premium rises 12%.',
  },
  {
    name: 'Parts',
    label: 'Parts Harvest',
    recovery: '$195.00',
    confidence: 45,
    detail: 'OLED panel & camera module harvest for internal technician repair stock.',
    flipNote: 'Flips to Recycle if cosmetic housing damage compromises motherboard brackets.',
  },
  {
    name: 'Vendor Return',
    label: 'Vendor Return',
    recovery: '$160.00',
    confidence: 20,
    detail: 'Vendor credit memo agreement (RMA). Guaranteed flat reimbursement tier.',
    flipNote: 'Flips to Parts if harvested component spot values increase past RMA limit.',
  },
  {
    name: 'Recycle',
    label: 'Recycle',
    recovery: '$24.00',
    confidence: 5,
    detail: 'Certified e-waste smelting and precious metal recovery batch.',
    flipNote: 'Terminal fallback when physical unit fails safety inspection.',
  },
]

function Hero2DFallback({ activeChannel }: { activeChannel: string }) {
  const current = CHANNELS_DATA.find((c) => c.name === activeChannel) ?? CHANNELS_DATA[0]

  return (
    <div className="flex size-full flex-col items-center justify-center p-6 text-center">
      <div className="relative flex size-36 items-center justify-center rounded-3xl border border-primary/20 bg-primary/5 p-4 shadow-inner">
        <Cpu className="size-16 text-primary/80" aria-hidden="true" />
        <div className="absolute inset-0 rounded-3xl border border-primary/40 animate-pulse" />
      </div>
      <p className="mt-4 text-xs font-mono tracking-wider uppercase text-primary">
        Channel Active: {current.label}
      </p>
      <p className="text-xl font-bold tracking-tight text-foreground">{current.recovery}</p>
    </div>
  )
}

export function HeroInspectionCard() {
  const hasWebGL = useMemo(() => supportsWebGL(), [])
  const [activeChannel, setActiveChannel] = useState('Refurbish')

  const current = CHANNELS_DATA.find((c) => c.name === activeChannel) ?? CHANNELS_DATA[0]

  return (
    <GlassPanel refract className="mt-12 overflow-hidden rounded-3xl border border-border/80 text-left shadow-2xl">
      {/* Top telemetry bar */}
      <div className="flex flex-wrap items-center justify-between border-b border-border/60 bg-muted/20 px-6 py-3.5 text-xs">
        <div className="flex items-center gap-2.5">
          <span className="relative flex size-2.5">
            <span className="absolute inline-flex size-full animate-ping rounded-full bg-primary opacity-75" />
            <span className="relative inline-flex size-2.5 rounded-full bg-primary" />
          </span>
          <span className="font-mono font-medium tracking-tight text-foreground">
            DISPOSITION SCANNER: <span className="text-muted-foreground">iPhone 14 Pro 128GB</span>
          </span>
        </div>
        <div className="flex items-center gap-4 text-muted-foreground font-mono">
          <span className="hidden sm:inline">SERIAL: F17K8***9M</span>
          <span className="inline-flex items-center gap-1 text-primary">
            <Sparkles className="size-3.5" aria-hidden="true" />
            MONTE CARLO (10k RUNS)
          </span>
        </div>
      </div>

      <div className="grid gap-6 p-6 lg:grid-cols-12 lg:gap-8 lg:p-8">
        {/* 3D Visualization Canvas (pmndrs/react-three-fiber inspired) */}
        <div className="relative flex h-72 w-full flex-col items-center justify-center overflow-hidden rounded-2xl border border-border/50 bg-background/40 sm:h-80 lg:col-span-7">
          <div className="pointer-events-none absolute top-3 left-3 z-10 flex items-center gap-2 rounded-full border border-border/40 bg-background/60 px-2.5 py-1 text-[11px] font-mono text-muted-foreground backdrop-blur-md">
            <Layers className="size-3 text-primary" aria-hidden="true" />
            <span>Interactive 3D Prism</span>
          </div>

          {hasWebGL ? (
            <Suspense fallback={<Hero2DFallback activeChannel={activeChannel} />}>
              <HeroPrismCanvas
                activeChannel={activeChannel}
                onSelectChannel={setActiveChannel}
              />
            </Suspense>
          ) : (
            <Hero2DFallback activeChannel={activeChannel} />
          )}

          <div className="pointer-events-none absolute right-3 bottom-3 z-10 text-[10px] font-mono text-muted-foreground/70">
            Drag / move cursor to tilt device
          </div>
        </div>

        {/* Live Channel Decisions & Confidence */}
        <div className="flex flex-col justify-between space-y-4 lg:col-span-5">
          <div>
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                Channel Evaluation
              </span>
              <span className="inline-flex items-center gap-1 rounded-full bg-primary/15 px-2.5 py-0.5 text-xs font-semibold text-primary">
                <CheckCircle2 className="size-3" aria-hidden="true" />
                Optimal Channel: Refurbish
              </span>
            </div>

            {/* Channel selection tabs */}
            <div className="mt-3.5 space-y-1.5" role="tablist" aria-label="Disposition Channels">
              {CHANNELS_DATA.map((ch) => {
                const isSelected = ch.name === activeChannel
                return (
                  <button
                    key={ch.name}
                    type="button"
                    role="tab"
                    aria-selected={isSelected}
                    onClick={() => setActiveChannel(ch.name)}
                    className={cn(
                      'group flex w-full items-center justify-between rounded-xl px-3.5 py-2 text-left text-sm transition-all duration-200',
                      isSelected
                        ? 'border border-primary/40 bg-primary/10 text-foreground font-semibold shadow-sm'
                        : 'border border-transparent bg-background/30 text-muted-foreground hover:bg-background/60 hover:text-foreground',
                    )}
                  >
                    <div className="flex items-center gap-2">
                      <span
                        className={cn(
                          'size-2 rounded-full transition-transform duration-200',
                          isSelected ? 'bg-primary scale-125' : 'bg-muted-foreground/40 group-hover:bg-muted-foreground',
                        )}
                      />
                      <span>{ch.label}</span>
                    </div>
                    <div className="flex items-center gap-3 font-mono">
                      <span className={cn('text-xs font-medium', isSelected ? 'text-primary' : 'text-muted-foreground')}>
                        {ch.confidence}% conf
                      </span>
                      <span className={cn('text-sm font-semibold', isSelected ? 'text-foreground' : 'text-muted-foreground')}>
                        {ch.recovery}
                      </span>
                    </div>
                  </button>
                )
              })}
            </div>
          </div>

          {/* Active channel details card */}
          <div className="rounded-2xl border border-border/70 bg-background/50 p-4 backdrop-blur-sm">
            <div className="flex items-baseline justify-between">
              <div>
                <p className="text-xs font-mono uppercase text-muted-foreground">Expected Net Recovery</p>
                <p className="text-2xl font-bold tracking-tight text-foreground">{current.recovery}</p>
              </div>
              {current.isBest && (
                <div className="text-right">
                  <span className="inline-flex items-center gap-1 text-xs font-semibold text-lime">
                    <TrendingUp className="size-3" aria-hidden="true" />
                    +$144.50 lift
                  </span>
                  <p className="text-[11px] text-muted-foreground font-mono">+53.9% vs baseline</p>
                </div>
              )}
            </div>

            <p className="mt-2.5 text-xs leading-relaxed text-muted-foreground">
              {current.detail}
            </p>

            <div className="mt-3 flex items-start gap-1.5 border-t border-border/40 pt-2.5 text-[11px] leading-tight text-muted-foreground">
              <ChevronRight className="mt-0.5 size-3 shrink-0 text-primary" aria-hidden="true" />
              <span>
                <strong className="text-foreground">Flip condition:</strong> {current.flipNote}
              </span>
            </div>
          </div>
        </div>
      </div>
    </GlassPanel>
  )
}

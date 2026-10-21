import {
  createContext,
  useContext,
  useId,
  useMemo,
  useRef,
  useState,
  type KeyboardEvent,
  type ReactNode,
} from 'react'
import { cn } from '@/utils/cn'

type TabsVariant = 'default' | 'line'

interface TabsContextValue {
  value: string
  setValue: (value: string) => void
  variant: TabsVariant
  baseId: string
  orientation: 'horizontal' | 'vertical'
}

const TabsContext = createContext<TabsContextValue | null>(null)

function useTabs(component: string): TabsContextValue {
  const context = useContext(TabsContext)
  if (context === null) {
    throw new Error(`${component} must be used within a Tabs`)
  }
  return context
}

export interface TabsProps {
  children: ReactNode
  /** The selected tab. Leave it out to let the tabs manage their own. */
  value?: string
  /** The tab to start on, when the tabs manage their own. */
  defaultValue?: string
  /** Called when the selection changes. */
  onValueChange?: (value: string) => void
  variant?: TabsVariant
  orientation?: 'horizontal' | 'vertical'
  className?: string
}

/**
 * The tabs.
 *
 * The default variant is a pill list. The line variant puts a two pixel
 * underline under the active tab, which fades in rather than jumping.
 */
export function Tabs({
  children,
  value,
  defaultValue,
  onValueChange,
  variant = 'default',
  orientation = 'horizontal',
  className,
}: TabsProps) {
  const baseId = useId()
  const [internal, setInternal] = useState(defaultValue ?? '')
  const current = value ?? internal

  const context = useMemo<TabsContextValue>(
    () => ({
      value: current,
      setValue: (next: string) => {
        if (value === undefined) setInternal(next)
        onValueChange?.(next)
      },
      variant,
      baseId,
      orientation,
    }),
    [current, value, onValueChange, variant, baseId, orientation]
  )

  return (
    <TabsContext.Provider value={context}>
      <div className={cn('space-y-4', className)} data-orientation={orientation}>
        {children}
      </div>
    </TabsContext.Provider>
  )
}

export function TabsList({ className, children }: { className?: string; children: ReactNode }) {
  const { variant } = useTabs('TabsList')
  return (
    <div
      role="tablist"
      className={cn(
        'inline-flex w-fit items-center justify-center rounded-full p-1 text-muted-foreground',
        variant === 'default' ? 'bg-muted' : 'gap-1 bg-transparent',
        className
      )}
    >
      {children}
    </div>
  )
}

export function TabsTrigger({
  value,
  className,
  children,
}: {
  value: string
  className?: string
  children: ReactNode
}) {
  const { value: selected, setValue, variant, baseId } = useTabs('TabsTrigger')
  const active = selected === value
  const ref = useRef<HTMLButtonElement>(null)

  const onKeyDown = (event: KeyboardEvent<HTMLButtonElement>) => {
    const list = ref.current?.closest('[role="tablist"]')
    if (!list) return
    const tabs = Array.from(list.querySelectorAll<HTMLButtonElement>('[role="tab"]'))
    const index = tabs.indexOf(event.currentTarget)
    if (index === -1) return

    let next = -1
    if (event.key === 'ArrowRight' || event.key === 'ArrowDown') {
      next = (index + 1) % tabs.length
    } else if (event.key === 'ArrowLeft' || event.key === 'ArrowUp') {
      next = (index - 1 + tabs.length) % tabs.length
    } else if (event.key === 'Home') {
      next = 0
    } else if (event.key === 'End') {
      next = tabs.length - 1
    }

    if (next !== -1) {
      event.preventDefault()
      tabs[next].focus()
      setValue(tabs[next].dataset.value ?? '')
    }
  }

  return (
    <button
      ref={ref}
      type="button"
      role="tab"
      id={`${baseId}-tab-${value}`}
      aria-controls={`${baseId}-panel-${value}`}
      aria-selected={active}
      data-active={active ? '' : undefined}
      data-value={value}
      tabIndex={active ? 0 : -1}
      onClick={() => setValue(value)}
      onKeyDown={onKeyDown}
      className={cn(
        'relative inline-flex h-8 flex-1 items-center justify-center gap-2 rounded-full',
        'border border-transparent px-3 py-1 text-sm font-medium',
        'text-foreground/60 transition-colors hover:text-foreground',
        'focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50',
        'data-[active]:text-foreground',
        variant === 'default' &&
          'data-[active]:bg-background data-[active]:text-foreground dark:data-[active]:border-input dark:data-[active]:bg-input/30',
        variant === 'line' &&
          'after:absolute after:inset-x-0 after:bottom-[-5px] after:h-0.5 after:bg-foreground after:opacity-0 after:transition-opacity data-[active]:after:opacity-100',
        className
      )}
    >
      {children}
    </button>
  )
}

export function TabsContent({
  value,
  className,
  children,
}: {
  value: string
  className?: string
  children: ReactNode
}) {
  const { value: selected, baseId } = useTabs('TabsContent')
  if (selected !== value) return null
  return (
    <div
      role="tabpanel"
      id={`${baseId}-panel-${value}`}
      aria-labelledby={`${baseId}-tab-${value}`}
      tabIndex={0}
      className={cn('outline-none', className)}
    >
      {children}
    </div>
  )
}

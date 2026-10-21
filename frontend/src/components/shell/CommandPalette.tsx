import { useEffect, useMemo, useRef, useState, type KeyboardEvent } from 'react'
import { createPortal } from 'react-dom'
import { useNavigate } from 'react-router-dom'
import { CornerDownLeft, Search } from 'lucide-react'
import { cn } from '@/utils/cn'
import { useFocusTrap } from '@/components/ui'
import { matchesCommand, type Command } from '@/components/shell/navigation'

export interface CommandPaletteProps {
  open: boolean
  onClose: () => void
  /** The commands on offer. */
  commands: Command[]
}

/**
 * The command palette.
 *
 * Everything the application can do is in here, so that the person who
 * uses it all day never has to reach for the mouse. The search matches on
 * the label, the explanation and the keywords.
 */
export function CommandPalette({ open, onClose, commands }: CommandPaletteProps) {
  const navigate = useNavigate()
  const [query, setQuery] = useState('')
  const [activeIndex, setActiveIndex] = useState(0)
  const inputRef = useRef<HTMLInputElement>(null)
  const listRef = useRef<HTMLDivElement>(null)
  const containerRef = useFocusTrap(open, onClose)

  const results = useMemo(
    () => commands.filter((command) => matchesCommand(command, query)),
    [commands, query]
  )

  // Start from a clean slate every time it opens.
  useEffect(() => {
    if (!open) return
    setQuery('')
    setActiveIndex(0)
  }, [open])

  useEffect(() => {
    if (!open) return
    // The search field takes the focus straight away, so that the reader
    // can type without reaching for the pointer, and so that the arrow
    // keys and the enter key reach the palette.
    inputRef.current?.focus()
  }, [open])

  // Keep the highlighted row in view as the selection moves.
  useEffect(() => {
    if (!open) return
    const active = listRef.current?.querySelector<HTMLElement>('[data-active="true"]')
    // Not every environment has a layout engine, and one that does not
    // will not scroll the row into view either.
    if (typeof active?.scrollIntoView === 'function') {
      active.scrollIntoView({ block: 'nearest' })
    }
  }, [activeIndex, open])

  const run = (command: Command) => {
    onClose()
    if (command.to) navigate(command.to)
    command.action?.()
  }

  const onKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.key === 'ArrowDown') {
      event.preventDefault()
      setActiveIndex((current) => (results.length === 0 ? 0 : (current + 1) % results.length))
    } else if (event.key === 'ArrowUp') {
      event.preventDefault()
      setActiveIndex((current) =>
        results.length === 0 ? 0 : (current - 1 + results.length) % results.length
      )
    } else if (event.key === 'Enter') {
      event.preventDefault()
      const command = results[activeIndex]
      if (command) run(command)
    }
  }

  if (!open) return null

  return createPortal(
    <div className="fixed inset-0 z-50 flex items-start justify-center p-4 pt-[10vh]">
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        aria-hidden="true"
        onMouseDown={onClose}
      />
      <div
        ref={containerRef}
        role="dialog"
        aria-modal="true"
        aria-label="Search the application"
        onKeyDown={onKeyDown}
        className="relative flex w-full max-w-xl flex-col overflow-hidden rounded-4xl border bg-popover shadow-2xl animate-scale-in"
      >
        <div className="flex items-center gap-3 border-b px-4">
          <Search className="size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(event) => {
              setQuery(event.target.value)
              setActiveIndex(0)
            }}
            placeholder="Search the application"
            aria-label="Type to search"
            className="h-12 flex-1 bg-transparent text-sm outline-none placeholder:text-muted-foreground"
          />
          <kbd className="rounded-md bg-muted px-1.5 py-0.5 font-sans text-xs text-muted-foreground">
            Esc
          </kbd>
        </div>

        <div ref={listRef} className="max-h-[22rem] overflow-y-auto p-2" role="listbox">
          {results.length === 0 ? (
            <p className="px-3 py-8 text-center text-sm text-muted-foreground">
              Nothing matches “{query}”.
            </p>
          ) : (
            results.map((command, index) => {
              const Icon = command.icon
              const active = index === activeIndex
              return (
                <button
                  key={command.id}
                  type="button"
                  role="option"
                  aria-selected={active}
                  data-active={active ? 'true' : undefined}
                  onMouseEnter={() => setActiveIndex(index)}
                  onClick={() => run(command)}
                  className={cn(
                    'flex w-full items-center gap-3 rounded-2xl px-3 py-2.5 text-left transition-colors',
                    active ? 'bg-lime-container text-on-primary-container' : 'text-foreground'
                  )}
                >
                  {Icon && <Icon className="size-4 shrink-0" aria-hidden="true" />}
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-sm font-medium">{command.label}</span>
                    {command.hint && (
                      <span
                        className={cn(
                          'block truncate text-xs',
                          active ? 'text-on-primary-container/70' : 'text-muted-foreground'
                        )}
                      >
                        {command.hint}
                      </span>
                    )}
                  </span>
                  {command.shortcut && (
                    <span
                      className={cn(
                        'shrink-0 font-mono text-xs',
                        active ? 'text-on-primary-container/70' : 'text-muted-foreground'
                      )}
                    >
                      {command.shortcut}
                    </span>
                  )}
                </button>
              )
            })
          )}
        </div>

        <div className="flex items-center gap-4 border-t px-4 py-2 text-xs text-muted-foreground">
          <span className="flex items-center gap-1.5">
            <CornerDownLeft className="size-3" aria-hidden="true" />
            to choose
          </span>
          <span>↑↓ to move</span>
          <span>esc to close</span>
        </div>
      </div>
    </div>,
    document.body
  )
}

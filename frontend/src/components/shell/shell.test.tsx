import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { ThemeProvider } from '@/theme'
import { OfflineProvider } from '@/offline'
import { AppShell } from '@/components/shell/AppShell'
import { CommandPalette } from '@/components/shell/CommandPalette'
import { Sidebar } from '@/components/shell/Sidebar'
import { ThemeToggle } from '@/components/shell/ThemeToggle'
import { navigation, type Command } from '@/components/shell/navigation'

function Wrapper({ children }: { children: ReactNode }) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <OfflineProvider autoSync={false}>
          <MemoryRouter initialEntries={['/']}>{children}</MemoryRouter>
        </OfflineProvider>
      </ThemeProvider>
    </QueryClientProvider>
  )
}

const COMMANDS: Command[] = [
  { id: 'go-units', label: 'Units', hint: 'Every returned unit', to: '/units' },
  { id: 'go-analytics', label: 'Analytics', hint: 'How wrong the engine was', to: '/analytics' },
  { id: 'do-thing', label: 'Do the thing', hint: 'Something specific', action: () => undefined },
]

describe('Sidebar', () => {
  it('lists every destination', () => {
    render(
      <Wrapper>
        <Sidebar />
      </Wrapper>,
    )

    for (const item of navigation) {
      expect(screen.getByRole('link', { name: new RegExp(item.name, 'i') })).toBeInTheDocument()
    }
  })

  it('marks the current destination', () => {
    render(
      <Wrapper>
        <Routes>
          <Route path="/" element={<Sidebar />} />
          <Route path="/units" element={<Sidebar />} />
        </Routes>
      </Wrapper>,
    )

    // The router starts at the dashboard.
    expect(screen.getByRole('link', { name: /dashboard/i })).toHaveAttribute('aria-current', 'page')
    expect(screen.getByRole('link', { name: /units/i })).not.toHaveAttribute('aria-current')
  })

  it('narrows and widens on demand', async () => {
    render(
      <Wrapper>
        <Sidebar />
      </Wrapper>,
    )

    const sidebar = screen.getByTestId('sidebar')
    expect(sidebar).toHaveAttribute('data-collapsed', 'false')

    await userEvent.click(screen.getByRole('button', { name: /narrow the sidebar/i }))
    expect(sidebar).toHaveAttribute('data-collapsed', 'true')
  })
})

describe('ThemeToggle', () => {
  it('switches between the two themes', async () => {
    render(
      <Wrapper>
        <ThemeToggle />
      </Wrapper>,
    )

    const button = screen.getByTestId('theme-toggle')
    expect(button).toHaveAttribute('aria-label', 'Switch to dark mode')

    await userEvent.click(button)
    await waitFor(() => {
      expect(screen.getByTestId('theme-toggle')).toHaveAttribute(
        'aria-label',
        'Switch to light mode'
      )
    })
  })
})

describe('CommandPalette', () => {
  it('is closed until it is opened', () => {
    render(
      <Wrapper>
        <CommandPalette open={false} onClose={vi.fn()} commands={COMMANDS} />
      </Wrapper>,
    )
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('lists the commands when it is open', () => {
    render(
      <Wrapper>
        <CommandPalette open onClose={vi.fn()} commands={COMMANDS} />
      </Wrapper>,
    )

    expect(screen.getByRole('option', { name: /units/i })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: /do the thing/i })).toBeInTheDocument()
  })

  it('narrows the list as the reader types', async () => {
    render(
      <Wrapper>
        <CommandPalette open onClose={vi.fn()} commands={COMMANDS} />
      </Wrapper>,
    )

    await userEvent.type(screen.getByLabelText(/type to search/i), 'analytic')
    expect(screen.getByRole('option', { name: /analytics/i })).toBeInTheDocument()
    expect(screen.queryByRole('option', { name: /do the thing/i })).not.toBeInTheDocument()
  })

  it('runs the highlighted command when the enter key is pressed', async () => {
    const action = vi.fn()
    render(
      <Wrapper>
        <CommandPalette
          open
          onClose={vi.fn()}
          commands={[{ id: 'do-thing', label: 'Do the thing', action }]}
        />
      </Wrapper>,
    )

    await userEvent.keyboard('{Enter}')
    expect(action).toHaveBeenCalled()
  })

  it('moves the highlight with the arrow keys', async () => {
    render(
      <Wrapper>
        <CommandPalette open onClose={vi.fn()} commands={COMMANDS} />
      </Wrapper>,
    )

    const first = screen.getByRole('option', { name: /units/i })
    expect(first).toHaveAttribute('aria-selected', 'true')

    await userEvent.keyboard('{ArrowDown}')
    expect(screen.getByRole('option', { name: /analytics/i })).toHaveAttribute(
      'aria-selected',
      'true'
    )
  })

  it('says when nothing matches', async () => {
    render(
      <Wrapper>
        <CommandPalette open onClose={vi.fn()} commands={COMMANDS} />
      </Wrapper>,
    )

    await userEvent.type(screen.getByLabelText(/type to search/i), 'zzzz')
    expect(screen.getByText(/nothing matches/i)).toBeInTheDocument()
  })
})

describe('AppShell', () => {
  it('opens the palette with the keyboard shortcut', async () => {
    render(
      <Wrapper>
        <AppShell>
          <p>The page</p>
        </AppShell>
      </Wrapper>,
    )

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()

    await userEvent.keyboard('{Meta>}k{/Meta}')
    await waitFor(() => {
      expect(screen.getByRole('dialog', { name: /search the application/i })).toBeInTheDocument()
    })
  })

  it('shows the page inside the shell', () => {
    render(
      <Wrapper>
        <AppShell>
          <p>The page</p>
        </AppShell>
      </Wrapper>,
    )

    expect(screen.getByText('The page')).toBeInTheDocument()
    expect(screen.getByTestId('sidebar')).toBeInTheDocument()
  })
})

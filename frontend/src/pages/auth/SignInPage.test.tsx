import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ThemeProvider } from '@/theme'

import { SignInPage } from '@/pages/auth/SignInPage'

vi.mock('@/api/auth', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/api/auth')>()
  return { ...actual, signIn: vi.fn() }
})

const { signIn } = await import('@/api/auth')

function renderPage() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
  return render(
    <ThemeProvider>
      <QueryClientProvider client={client}>
        <MemoryRouter initialEntries={['/signin']}>
          <Routes>
            <Route path="/signin" element={<SignInPage />} />
            <Route path="/" element={<p>The console</p>} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>
    </ThemeProvider>,
  )
}

describe('the sign-in page', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    window.localStorage.clear()
  })

  it('says what is missing rather than sending an empty form', async () => {
    const user = userEvent.setup()
    renderPage()

    await user.click(screen.getByRole('button', { name: 'Sign in' }))

    expect(await screen.findByText('Enter your email address.')).toBeInTheDocument()
    expect(signIn).not.toHaveBeenCalled()
  })

  it('signs in, remembers the organisation, and opens the console', async () => {
    const user = userEvent.setup()
    vi.mocked(signIn).mockResolvedValue({
      id: 'u1',
      email: 'ada@harbour.example',
      display_name: 'Ada',
      role: 'admin',
      org_id: 'org-42',
      organisation_name: 'Harbour Electronics',
    })
    renderPage()

    await user.type(screen.getByLabelText(/^Email/), 'ada@harbour.example')
    await user.type(screen.getByLabelText(/^Password/), 'correct horse 42')
    await user.click(screen.getByRole('button', { name: 'Sign in' }))

    await waitFor(() => expect(screen.getByText('The console')).toBeInTheDocument())
    expect(signIn).toHaveBeenCalledWith({ email: 'ada@harbour.example', password: 'correct horse 42' })
    expect(window.localStorage.getItem('secondroute-org')).toBe('org-42')
  })

  it('reports a wrong password in words that do not say which part was wrong', async () => {
    const user = userEvent.setup()
    vi.mocked(signIn).mockRejectedValue({ response: { status: 401, data: { detail: 'x' } } })
    renderPage()

    await user.type(screen.getByLabelText(/^Email/), 'ada@harbour.example')
    await user.type(screen.getByLabelText(/^Password/), 'wrong pass 1')
    await user.click(screen.getByRole('button', { name: 'Sign in' }))

    expect(
      await screen.findByText('The email address or the password is not right.'),
    ).toBeInTheDocument()
    expect(window.localStorage.getItem('secondroute-org')).toBeNull()
  })
})

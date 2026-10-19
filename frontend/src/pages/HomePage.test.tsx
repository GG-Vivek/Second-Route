import React from 'react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import { HomePage } from './HomePage'
import { api } from '@/api/client'

// Mock the API client
vi.mock('@/api/client', () => ({
  api: {
    get: vi.fn(),
  },
}))

const mockApiGet = vi.mocked(api.get)

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  })

  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        {children}
      </BrowserRouter>
    </QueryClientProvider>
  )
}

describe('HomePage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders loading state initially', () => {
    mockApiGet.mockResolvedValueOnce(
      new Promise(() => {}) // Never resolves to keep loading state
    )

    render(<HomePage />, { wrapper: createWrapper() })

    expect(screen.getByText('SecondRoute Dashboard')).toBeInTheDocument()
    expect(screen.getByText('System Status')).toBeInTheDocument()
    expect(screen.getByText('LOADING...')).toBeInTheDocument()
  })

  it('renders healthy status when API returns healthy', async () => {
    mockApiGet.mockResolvedValueOnce({
      status: 'healthy',
      version: '0.1.0',
      environment: 'development',
      checks: {
        database: 'ok',
        redis: 'ok',
      },
    })

    render(<HomePage />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText('HEALTHY')).toBeInTheDocument()
    })

    expect(screen.getByText('Version: 0.1.0')).toBeInTheDocument()
    expect(screen.getByText('Env: development')).toBeInTheDocument()
  })

  it('renders degraded status when API returns degraded', async () => {
    mockApiGet.mockResolvedValueOnce({
      status: 'degraded',
      version: '0.1.0',
      environment: 'development',
      checks: {
        database: 'ok',
        redis: 'failed',
      },
    })

    render(<HomePage />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText('DEGRADED')).toBeInTheDocument()
    })
  })

  it('renders error state when API fails', async () => {
    mockApiGet.mockRejectedValueOnce(new Error('Network error'))

    render(<HomePage />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText('Error fetching health data')).toBeInTheDocument()
    })
    expect(screen.getByText('Network error')).toBeInTheDocument()
  })

  it('displays service health table', async () => {
    mockApiGet.mockResolvedValueOnce({
      status: 'healthy',
      version: '0.1.0',
      environment: 'development',
      checks: {
        database: 'ok',
        redis: 'ok',
      },
    })

    render(<HomePage />, { wrapper: createWrapper() })

    await waitFor(() => {
      expect(screen.getByText('Service Health')).toBeInTheDocument()
    })

    expect(screen.getByText('API Server')).toBeInTheDocument()
    expect(screen.getByText('PostgreSQL Database')).toBeInTheDocument()
    expect(screen.getByText('Redis Cache')).toBeInTheDocument()
  })
})
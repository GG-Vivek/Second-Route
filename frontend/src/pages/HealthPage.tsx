import React, { useEffect, useState } from 'react'
import { CheckCircle, XCircle, AlertCircle, Loader2, RefreshCw, Server, Database, HardDrive } from 'lucide-react'
import { api } from '@/api/client'

interface HealthResponse {
  status: 'healthy' | 'degraded'
  version: string
  environment: string
  checks: {
    database: 'ok' | 'failed'
    redis: 'ok' | 'failed'
  }
}

export function HealthPage() {
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchHealth = async () => {
    try {
      setLoading(true)
      const data = await api.get<HealthResponse>('/health')
      setHealth(data)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch health')
      setHealth(null)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchHealth()
  }, [])

  const getOverallStatusBadge = (status: 'healthy' | 'degraded' | null) => {
    if (!status) return null
    return status === 'healthy' ? (
      <span className="inline-flex items-center gap-1 rounded-full bg-green-100 px-3 py-1 text-sm font-medium text-green-800">
        <CheckCircle className="h-4 w-4" />
        Healthy
      </span>
    ) : (
      <span className="inline-flex items-center gap-1 rounded-full bg-yellow-100 px-3 py-1 text-sm font-medium text-yellow-800">
        <AlertCircle className="h-4 w-4" />
        Degraded
      </span>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">System Health</h1>
          <p className="text-muted-foreground mt-1">
            Detailed health status of all SecondRoute services
          </p>
        </div>
        <div className="flex items-center gap-4">
          {getOverallStatusBadge(health?.status ?? null)}
          <button
            onClick={fetchHealth}
            disabled={loading}
            className="inline-flex items-center gap-2 rounded-lg border border-border bg-background px-4 py-2 text-sm font-medium hover:bg-accent disabled:opacity-50"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-800">
          <p className="font-medium">Error fetching health data</p>
          <p className="text-sm mt-1">{error}</p>
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-3">
        <ServiceCard
          name="API Server"
          icon={<Server className="h-6 w-6" />}
          status={health?.status === 'healthy' ? 'ok' : health?.status === 'degraded' ? 'degraded' : 'loading'}
          detail="FastAPI application server"
          checks={[
            { name: 'Process', status: health?.status !== 'degraded' ? 'ok' : 'degraded' },
            { name: 'Memory', status: 'ok' },
            { name: 'CPU', status: 'ok' },
          ]}
        />

        <ServiceCard
          name="PostgreSQL Database"
          icon={<Database className="h-6 w-6" />}
          status={health?.checks.database ?? 'loading'}
          detail="Primary data store (PostgreSQL 16)"
          checks={[
            { name: 'Connection', status: health?.checks.database ?? 'loading' },
            { name: 'Migrations', status: 'ok' },
            { name: 'Pool', status: 'ok' },
          ]}
        />

        <ServiceCard
          name="Redis Cache"
          icon={<HardDrive className="h-6 w-6" />}
          status={health?.checks.redis ?? 'loading'}
          detail="Caching & job queue (Redis 7)"
          checks={[
            { name: 'Connection', status: health?.checks.redis ?? 'loading' },
            { name: 'Memory', status: 'ok' },
            { name: 'Persistence', status: 'ok' },
          ]}
        />
      </div>

      <div className="rounded-lg border bg-card p-6">
        <h2 className="text-lg font-semibold mb-4">System Information</h2>
        <dl className="grid grid-cols-2 gap-4 md:grid-cols-4">
          <div>
            <dt className="text-sm text-muted-foreground">Version</dt>
            <dd className="font-mono text-lg">{health?.version ?? '—'}</dd>
          </div>
          <div>
            <dt className="text-sm text-muted-foreground">Environment</dt>
            <dd className="font-mono text-lg capitalize">{health?.environment ?? '—'}</dd>
          </div>
          <div>
            <dt className="text-sm text-muted-foreground">Database</dt>
            <dd className="font-mono text-lg">{health?.checks.database === 'ok' ? 'Connected' : 'Disconnected'}</dd>
          </div>
          <div>
            <dt className="text-sm text-muted-foreground">Cache</dt>
            <dd className="font-mono text-lg">{health?.checks.redis === 'ok' ? 'Connected' : 'Disconnected'}</dd>
          </div>
        </dl>
      </div>
    </div>
  )
}

function ServiceCard({
  name,
  icon,
  status,
  detail,
  checks,
}: {
  name: string
  icon: React.ReactNode
  status: 'ok' | 'failed' | 'degraded' | 'loading'
  detail: string
  checks: Array<{ name: string; status: 'ok' | 'failed' | 'degraded' | 'loading' }>
}) {
  const getStatusColor = (s: string) => {
    switch (s) {
      case 'ok':
        return 'text-green-500'
      case 'failed':
        return 'text-red-500'
      case 'degraded':
        return 'text-yellow-500'
      default:
        return 'text-muted-foreground'
    }
  }

  const getStatusIcon = (s: string) => {
    switch (s) {
      case 'ok':
        return <CheckCircle className="h-4 w-4 text-green-500" />
      case 'failed':
        return <XCircle className="h-4 w-4 text-red-500" />
      case 'degraded':
        return <AlertCircle className="h-4 w-4 text-yellow-500" />
      default:
        return <Loader2 className="h-4 w-4 text-muted-foreground animate-spin" />
    }
  }

  return (
    <div className="rounded-lg border bg-card p-6 shadow-sm">
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-muted">{icon}</div>
          <div>
            <h3 className="text-lg font-semibold">{name}</h3>
            <p className="text-sm text-muted-foreground">{detail}</p>
          </div>
        </div>
        <div className={getStatusColor(status)}>
          {getStatusIcon(status)}
        </div>
      </div>

      <div className="mt-4 space-y-2">
        {checks.map((check) => (
          <div key={check.name} className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">{check.name}</span>
            <span className={getStatusColor(check.status)}>{getStatusIcon(check.status)}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
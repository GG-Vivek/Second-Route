import React, { useEffect, useState } from 'react'
import { CheckCircle, XCircle, AlertCircle, Loader2, Server, Database, HardDrive } from 'lucide-react'
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

export function HomePage() {
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function fetchHealth() {
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

    fetchHealth()
    const interval = setInterval(fetchHealth, 30000) // Refresh every 30s
    return () => clearInterval(interval)
  }, [])

  const getOverallStatusIcon = (status: 'healthy' | 'degraded' | null) => {
    if (!status || loading) return <Loader2 className="h-8 w-8 text-muted-foreground animate-spin" />
    return status === 'healthy' ? (
      <CheckCircle className="h-8 w-8 text-green-500" />
    ) : (
      <AlertCircle className="h-8 w-8 text-yellow-500" />
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">SecondRoute Dashboard</h1>
        <p className="text-muted-foreground mt-1">
          Decision engine for returned electronics
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        {/* Overall Status Card */}
        <div className="md:col-span-2">
          <div className="rounded-lg border bg-card p-6 shadow-sm">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-xl font-semibold">System Status</h2>
                <p className="text-muted-foreground mt-1">
                  Real-time health monitoring of all services
                </p>
              </div>
              <div className={health?.status === 'healthy' ? 'text-green-500' : 'text-yellow-500'}>
                {getOverallStatusIcon(health?.status ?? null)}
              </div>
            </div>
            <div className="mt-4 flex items-center gap-4 text-sm">
              <span className={health?.status === 'healthy' ? 'text-green-600 font-medium' : 'text-yellow-600 font-medium'}>
                {health?.status?.toUpperCase() ?? 'LOADING...'}
              </span>
              <span className="text-muted-foreground">
                Version: {health?.version ?? '—'}
              </span>
              <span className="text-muted-foreground">
                Env: {health?.environment ?? '—'}
              </span>
            </div>
          </div>
        </div>

        {/* Quick Stats Card */}
        <div className="rounded-lg border bg-card p-6 shadow-sm">
          <h3 className="font-semibold">Quick Actions</h3>
          <div className="mt-4 space-y-2">
            <LinkCard
              title="New Return Intake"
              description="Log a returned unit"
              href="/intake"
              icon={<Server className="h-4 w-4" />}
              disabled={true}
            />
            <LinkCard
              title="View Inspections"
              description="Browse inspection records"
              href="/inspections"
              icon={<Database className="h-4 w-4" />}
              disabled={true}
            />
            <LinkCard
              title="Decision Engine"
              description="Get disposition recommendations"
              href="/decisions"
              icon={<HardDrive className="h-4 w-4" />}
              disabled={true}
            />
          </div>
        </div>
      </div>

      {/* Service Health Details */}
      <div>
        <h2 className="text-xl font-semibold mb-4">Service Health</h2>
        <div className="rounded-lg border bg-card shadow-sm overflow-hidden">
          <table className="w-full">
            <thead className="bg-muted/50">
              <tr>
                <th className="px-4 py-3 text-left text-sm font-medium text-muted-foreground">Service</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-muted-foreground">Status</th>
                <th className="px-4 py-3 text-left text-sm font-medium text-muted-foreground">Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              <ServiceRow
                name="API Server"
                icon={<Server className="h-4 w-4" />}
                status={health?.status === 'healthy' ? 'ok' : health?.status === 'degraded' ? 'degraded' : 'loading'}
                detail="FastAPI application server"
              />
              <ServiceRow
                name="PostgreSQL Database"
                icon={<Database className="h-4 w-4" />}
                status={health?.checks.database ?? 'loading'}
                detail="Primary data store"
              />
              <ServiceRow
                name="Redis Cache"
                icon={<HardDrive className="h-4 w-4" />}
                status={health?.checks.redis ?? 'loading'}
                detail="Caching & job queue"
              />
            </tbody>
          </table>
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-800">
          <p className="font-medium">Error fetching health data</p>
          <p className="text-sm mt-1">{error}</p>
        </div>
      )}
    </div>
  )
}

function ServiceRow({
  name,
  icon,
  status,
  detail,
}: {
  name: string
  icon: React.ReactNode
  status: 'ok' | 'failed' | 'degraded' | 'loading'
  detail: string
}) {
  const getStatusBadge = () => {
    switch (status) {
      case 'ok':
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-green-100 px-2.5 py-0.5 text-xs font-medium text-green-800">
            <CheckCircle className="h-3 w-3" />
            Healthy
          </span>
        )
      case 'failed':
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-red-100 px-2.5 py-0.5 text-xs font-medium text-red-800">
            <XCircle className="h-3 w-3" />
            Failed
          </span>
        )
      case 'degraded':
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-yellow-100 px-2.5 py-0.5 text-xs font-medium text-yellow-800">
            <AlertCircle className="h-3 w-3" />
            Degraded
          </span>
        )
      default:
        return (
          <span className="inline-flex items-center gap-1 rounded-full bg-gray-100 px-2.5 py-0.5 text-xs font-medium text-gray-800">
            <Loader2 className="h-3 w-3 animate-spin" />
            Checking...
          </span>
        )
    }
  }

  return (
    <tr className="hover:bg-muted/50">
      <td className="px-4 py-3">
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-muted">{icon}</div>
          <div>
            <p className="font-medium">{name}</p>
            <p className="text-sm text-muted-foreground">{detail}</p>
          </div>
        </div>
      </td>
      <td className="px-4 py-3">{getStatusBadge()}</td>
      <td className="px-4 py-3 text-sm text-muted-foreground">
        {status === 'ok' && 'Operational'}
        {status === 'failed' && 'Connection failed'}
        {status === 'degraded' && 'Partial functionality'}
        {status === 'loading' && 'Checking...'}
      </td>
    </tr>
  )
}

function LinkCard({
  title,
  description,
  href,
  icon,
  disabled,
}: {
  title: string
  description: string
  href: string
  icon: React.ReactNode
  disabled?: boolean
}) {
  return (
    <a
      href={href}
      className={`flex items-center gap-3 rounded-lg p-3 transition-colors ${
        disabled
          ? 'text-muted-foreground bg-muted/50 cursor-not-allowed'
          : 'hover:bg-accent text-foreground'
      }`}
      aria-disabled={disabled}
    >
      <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-muted">{icon}</div>
      <div>
        <p className="font-medium text-sm">{title}</p>
        <p className="text-xs text-muted-foreground">{description}</p>
      </div>
    </a>
  )
}
import axios, { AxiosError, AxiosInstance, InternalAxiosRequestConfig } from 'axios'
import { getRequestId } from '@/utils/requestId'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1'

/**
 * Where the organisation comes from.
 *
 * Outside production the backend accepts the tenant in a header, so that a
 * developer can use the application without a login. Inside production the
 * header is ignored and the tenant comes from the token, which the login
 * flow will set.
 */
const ORG_STORAGE_KEY = 'secondroute-org'

/** The organisation the requests are made on behalf of. */
export function getOrgId(): string | null {
  try {
    const stored = window.localStorage.getItem(ORG_STORAGE_KEY)
    if (stored) return stored
  } catch {
    // A browser that will not read storage falls back to the environment.
  }
  return import.meta.env.VITE_ORG_ID || null
}

/** Remember the organisation the requests are made on behalf of. */
export function setOrgId(orgId: string | null): void {
  try {
    if (orgId) {
      window.localStorage.setItem(ORG_STORAGE_KEY, orgId)
    } else {
      window.localStorage.removeItem(ORG_STORAGE_KEY)
    }
  } catch {
    // The organisation is still taken from the environment.
  }
}

class ApiClient {
  private client: AxiosInstance

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    })

    // Request interceptor
    this.client.interceptors.request.use(
      (config: InternalAxiosRequestConfig) => {
        // Add request ID for tracing
        const requestId = getRequestId()
        if (requestId) {
          config.headers['X-Request-ID'] = requestId
        }
        // Name the tenant, when there is one to name.
        const orgId = getOrgId()
        if (orgId) {
          config.headers['X-Org-Id'] = orgId
        }
        return config
      },
      (error) => Promise.reject(error)
    )

    // Response interceptor
    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError) => {
        // Handle common errors
        if (error.response?.status === 401) {
          // Handle unauthorized - could redirect to login
          console.warn('Unauthorized request')
        }
        return Promise.reject(error)
      }
    )
  }

  async get<T>(url: string, params?: Record<string, unknown>): Promise<T> {
    const response = await this.client.get<T>(url, { params })
    return response.data
  }

  async post<T>(url: string, data?: unknown): Promise<T> {
    const response = await this.client.post<T>(url, data)
    return response.data
  }

  async put<T>(url: string, data?: unknown): Promise<T> {
    const response = await this.client.put<T>(url, data)
    return response.data
  }

  async patch<T>(url: string, data?: unknown): Promise<T> {
    const response = await this.client.patch<T>(url, data)
    return response.data
  }

  async delete<T>(url: string): Promise<T> {
    const response = await this.client.delete<T>(url)
    return response.data
  }
}

export const api = new ApiClient()
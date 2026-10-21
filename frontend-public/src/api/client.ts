/**
 * The API client (Phase 10).
 *
 * The storefront talks to one endpoint family: the public listings.
 * There is no sign-in, and there is nothing to sign in with.
 */

import axios from 'axios'

/** The base address of the API. */
const API_BASE = import.meta.env.VITE_API_BASE ?? '/api/v1'

/** The HTTP client. */
export const api = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
  timeout: 15_000,
})

/**
 * The organisation the window shows.
 *
 * The deployment names it: the backend has ``PUBLIC_ORG_ID`` for it. On a
 * developer's machine there is no deployment, so the tenant is named with
 * the header, which the backend only accepts outside production.
 *
 * @returns The organisation's identifier, or null when there is none.
 */
export function getOrgId(): string | null {
  try {
    const stored = window.localStorage.getItem('secondroute-org')
    if (stored) return stored
  } catch {
    // A browser that will not read storage falls back to the environment.
  }
  return import.meta.env.VITE_ORG_ID || null
}

api.interceptors.request.use((config) => {
  const orgId = getOrgId()
  if (orgId) {
    config.headers['X-Org-Id'] = orgId
  }
  return config
})

/**
 * A readable message for a failure.
 *
 * The shop window must never show a stack trace, and it must never show
 * nothing at all: a page that says nothing is worse than a page that
 * says what went wrong.
 *
 * @param error - Whatever was thrown.
 * @returns A sentence a person can read.
 */
export function describeFailure(error: unknown): string {
  if (axios.isAxiosError(error)) {
    if (error.code === 'ECONNABORTED') {
      return 'The shop took too long to answer. Please try again.'
    }
    if (!error.response) {
      return 'The shop could not be reached. Please check your connection.'
    }
    const detail = error.response.data as { detail?: string } | undefined
    if (typeof detail?.detail === 'string' && detail.detail.length > 0) {
      return detail.detail
    }
    return `The shop answered with an error (${error.response.status}).`
  }
  if (error instanceof Error && error.message) {
    return error.message
  }
  return 'Something went wrong.'
}

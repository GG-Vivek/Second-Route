import { api } from '@/api/client'

/** The account a person has made, or has signed in to (F11.1). */
export interface Account {
  id: string
  email: string
  display_name: string
  role: string
  org_id: string | null
  organisation_name: string | null
}

/**
 * Make a retailer, with its administrator.
 *
 * @param body - The retailer's details, in the backend's field names.
 * @returns The new administrator's account.
 */
export function signUpRetailer(body: Record<string, unknown>): Promise<Account> {
  return api.post<Account>('/auth/signup/retailer', body)
}

/**
 * Join an existing retailer as an inspector.
 *
 * @param body - The person's details and the retailer's code.
 * @returns The new account.
 */
export function signUpUser(body: Record<string, unknown>): Promise<Account> {
  return api.post<Account>('/auth/signup/user', body)
}

/**
 * Sign in with an email address and a password.
 *
 * @param body - The email address and the password.
 * @returns The account, including the organisation it acts for.
 */
export function signIn(body: { email: string; password: string }): Promise<Account> {
  return api.post<Account>('/auth/signin', body)
}

/**
 * The message for a failed sign-in or sign-up, in words a person can act on.
 *
 * @param error - Whatever was thrown.
 * @returns A sentence to show.
 */
export function describeAuthFailure(error: unknown): string {
  const status = (error as { response?: { status?: number } })?.response?.status
  const detail = (error as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
  if (status === 401) return 'The email address or the password is not right.'
  if (status === 409) return 'An account already exists for that email address. Try signing in.'
  if (status === 404) return typeof detail === 'string' ? detail : 'That retailer code is not recognised.'
  if (status === 422) return 'Some of the details are not in the form we expect. Check them and try again.'
  if (!status) return 'The shop could not be reached. Check your connection and try again.'
  return 'Something went wrong on our side. Please try again.'
}

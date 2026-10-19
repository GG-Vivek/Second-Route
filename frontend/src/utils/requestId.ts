/**
 * Request ID management for client-side tracing.
 * In a real app, this would be set by the server via headers or context.
 */

let currentRequestId = ''

export function setRequestId(id: string) {
  currentRequestId = id
}

export function getRequestId(): string {
  return currentRequestId
}

export function generateRequestId(): string {
  return crypto.randomUUID()
}
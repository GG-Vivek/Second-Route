/**
 * Request ID management for client-side tracing.
 *
 * Every request carries an identifier, so that a request can be found in
 * the logs of the browser and of the server at the same time. The server
 * reads it from the header and puts it on the response and on every log
 * line it writes while the request is being handled.
 */

import { newId } from '@/utils/id'

let currentRequestId = ''

export function setRequestId(id: string) {
  currentRequestId = id
}

export function getRequestId(): string {
  return currentRequestId
}

export function generateRequestId(): string {
  return newId()
}

/**
 * Return the identifier for the request that is being made now.
 *
 * One is made for every request, so that two requests made at the same
 * moment can be told apart.
 */
export function beginRequest(): string {
  const id = generateRequestId()
  setRequestId(id)
  return id
}

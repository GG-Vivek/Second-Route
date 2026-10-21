/**
 * Identifiers that work everywhere (F9.4).
 *
 * `crypto.randomUUID` only exists in a secure context. A browser on a
 * plain address - a warehouse machine on a local network, for instance -
 * has `crypto` but not `randomUUID`, and every call would throw. The
 * offline queue writes with it, so the offline path would be dead exactly
 * where it is needed most.
 */

/**
 * Return a random identifier.
 *
 * The identifier is not a secret and does not have to be
 * unguessable; it has to be unique enough that two entries do not
 * collide.
 */
export function newId(): string {
  const source = globalThis.crypto

  if (typeof source?.randomUUID === 'function') {
    return source.randomUUID()
  }

  const bytes = new Uint8Array(16)
  if (typeof source?.getRandomValues === 'function') {
    source.getRandomValues(bytes)
  } else {
    for (let index = 0; index < bytes.length; index += 1) {
      bytes[index] = Math.floor(Math.random() * 256)
    }
  }

  // Shaped like a UUID, so that it is recognisable in a log.
  const hex = Array.from(bytes, (byte) => byte.toString(16).padStart(2, '0')).join('')
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`
}

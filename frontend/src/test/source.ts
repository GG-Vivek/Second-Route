import { existsSync, readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import process from 'node:process'

/**
 * Open a file from the source tree, from wherever the runner was started.
 *
 * Two of the suites measure a source file rather than a fixture — the
 * contrast suite reads `index.css`, the default-theme suite reads
 * `index.html` — and the suite is started from the frontend directory in
 * continuous integration and may be started by hand from the repository root.
 * Looking in both costs one line and saves an error message that blames the
 * test instead of the directory.
 *
 * `?raw` would be the obvious way to do this, but Vitest answers imports of
 * stylesheets with an empty string, which is exactly the file being measured.
 */
export function readSource(...candidates: string[]): string {
  const found = candidates.map((candidate) => resolve(process.cwd(), candidate)).find(existsSync)
  if (!found) {
    throw new Error(`none of ${candidates.join(', ')} exists under ${process.cwd()}`)
  }
  return readFileSync(found, 'utf8')
}

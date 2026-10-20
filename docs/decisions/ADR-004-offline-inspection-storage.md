# ADR-004: Offline inspection storage and the fake-indexeddb test shim

## Status
Accepted

## Context
Phase 5 feature F5.5 requires inspectors to complete inspections without a
network connection, and to have those inspections reach the server once the
connection returns. The requirements are:

- Inspection drafts are stored locally, so a crash, a forced disconnect, or a
  browser restart never loses the inspector's work.
- Completed inspections queue while offline and sync on reconnect.
- Conflicts are resolved by last write, and both versions are kept in the
  audit log.

The plan mandates IndexedDB for offline drafts, and `idb` (a thin promise
wrapper over IndexedDB) is already a frontend dependency. The open question
was how to test the IndexedDB code path.

The backend's acceptance criterion ("no data lost in a forced-disconnect
test") is only meaningful if the client-side persistence is genuinely
exercised. A test that replaces IndexedDB with an in-memory map verifies the
queue logic but not the schema, the indexes, or the read/write behaviour of
the real store.

jsdom, the test environment used by Vitest here, does not implement
IndexedDB. Without a shim, every test touching the offline store has to
either skip itself or stub the storage layer out entirely.

## Decision
We will use `fake-indexeddb` (Apache-2.0) as a **dev-only** dependency to
provide a spec-compliant IndexedDB implementation in the test environment.

It is added to `devDependencies` only, so it never reaches the production
bundle. The offline store itself is written against the real `idb` API and
the real IndexedDB API; the shim only replaces the browser's implementation
of that API during tests.

We will also keep the queue and draft logic free of direct `indexedDB` calls
and behind narrow, individually testable functions, so the logic can be
tested without a database at all when a test does not need persistence.

## Consequences
### Positive
- The IndexedDB schema, the indexes, and the read/write behaviour are
  covered by real tests rather than mocked away.
- No production bundle impact: the shim is a development dependency.
- Apache-2.0 is a permissive licence that satisfies the project's
  free-and-open-source-only constraint.

### Negative
- One more dependency in the lockfile, which must be kept current.
- Tests now depend on the shim's fidelity to the IndexedDB spec. A
  divergence between the shim and a real browser would not be caught.

### Neutral
- The backend and the frontend now share the term "offline created" but not
  a schema; the flag crosses the API as a plain boolean.

## Alternatives Considered
| Alternative | Pros | Cons | Why Not Chosen |
|-------------|------|------|----------------|
| No new dependency; test the queue logic against an in-memory map | No new dependency; tests stay fast | The real IndexedDB path is untested; schema mistakes reach production | The schema is the part most likely to break in a browser, and it is exactly what an in-memory map would not exercise |
| Write an in-repo IndexedDB mock | No new dependency | A hand-written mock is a second implementation to maintain, and drifts from the spec | The mock would cost more maintenance than the shim it replaces |
| Test against a real browser (Playwright) | Highest fidelity | Playwright is a large dependency and a much slower test loop; the F5.5 store logic does not need a full browser to be trustworthy | The extra fidelity does not buy anything for a two-store IndexedDB schema, and the test loop cost is real |

## Implementation Notes
- `fake-indexeddb` is added to `frontend/package.json` under
  `devDependencies`.
- It is loaded once for the whole test run through
  `frontend/src/test/fakeIndexedDb.ts`, which is registered as an extra
  `setupFiles` entry in `frontend/vite.config.ts`.
- The offline module lives in `frontend/src/offline/`:
  - `db.ts` — the IndexedDB schema and connection
  - `drafts.ts` — draft read/write/delete
  - `queue.ts` — the submission queue and the sync loop
  - `submit.ts` — the decision between sending now and queueing
  - `OfflineProvider.tsx` — React state for connectivity and queue depth
- The backend marks a synced inspection with `offline_created = true` and
  records every conflicting write in the audit log, so the "both versions
  are kept" requirement is satisfied server-side.

## Related ADRs
- [ADR-001: Technology stack](ADR-001-technology-stack.md)
- [ADR-002: Decision engine](ADR-002-decision-engine.md)

## References
- PLAN.md, F5.5 "Offline inspection"
- `fake-indexeddb` on npm — Apache-2.0
- W3C IndexedDB Database API specification

---

*Date: 2026-10-20*
*Author: ai-minimax-m3.1-flash-ses_ea89089b7ffexWYy0yBa3OF4Wm*
*Reviewers: human-<github-handle>*

# ADR-006: The design system and the spatial decision console

## Status
Accepted

## Context
Every phase of SecondRoute is built and the application works end to end. What
it does not have is a surface worth using. The frontend is a light-mode
shadcn/Tailwind application assembled page by page: every banner, every badge,
every card is a hand-rolled variant of the same rounded rectangle. Six
different red-and-amber alert blocks exist across six pages. The fonts are
loaded from a third-party CDN at runtime, which the offline requirement in
F5.5 forbids. The charts on the analytics page are hand-drawn bars rather than
the Recharts library that is already installed and unused.

The decision card is the product. It answers one question — what should happen
to this unit — and it currently answers it with a table and a confidence bar.
The one thing an operator cannot see is the thing the engine cares about most:
**how much the channels' net values overlap**. Overlap is what makes the
confidence low. Overlap is what turns a recommendation into `SAFE_DEFAULT`.
Overlap is reduced to a single percentage.

Three constraints shape this decision.

**Every number has a source.** A visualisation that approximates a
distribution from a mean and a standard deviation would invent a shape the
engine never sampled. The engine draws 10,000 Monte Carlo samples per
channel; the samples are real, they are reproducible, and they must be what
the picture shows.

**Nothing loads from a third party at runtime.** The pilot runs behind a
customer's network. A font from a CDN is a dependency on the internet being
up, and an HDRI environment map fetched at render time is worse.

**Nothing may fail silently.** The application is used on a warehouse floor.
A blank rectangle where a chart should be is a failure the operator cannot
diagnose.

## Decision
We will rebuild the user interface on the pmndrs design language — the
Material Design 3 system that the react-three-fiber documentation and the
rest of the pmndrs ecosystem use — and we will render the decision's channel
distributions spatially with react-three-fiber.

**The design language.** The tokens are the pmndrs MD3 set: a warm neutral
ramp seeded from lime `#CAF543`, hairline borders, an elevation model where a
1px ring does the edge work rather than a shadow, radii on a 10px base
multiplier, Inter for prose and Inconsolata for code and numerals only, and a
150ms transition on a single easing curve. The chrome uses lime as its only
saturated colour. The application ships **dark by default** with a working
light mode, because the accent has to read against the surface and because
the pmndrs mark itself is a render on black.

**The spatial decision console.** The channel landscape is a ridgeline plot:
net value on the horizontal axis, one ridge per channel receding into depth,
probability density as height. The recommended channel is lime; the others are
neutral. Overlap between the leading ridges is visible as geometry rather
than asserted as a number.

**The 3D view is an enhancement over a 2D one, not a replacement.** The
landscape is built first as a two-dimensional SVG ridgeline — accessible,
printable, testable without a GPU — and the react-three-fiber scene is layered
on top of the same data behind a lazy boundary. When WebGL is missing or
fails, the 2D view is what the operator sees. There is never a blank
rectangle and never a silent failure.

**The distributions are real.** A new endpoint replays a stored decision from
its input snapshot and returns the binned density of the engine's own Monte
Carlo draws. No migration is needed, the result is deterministic, and it
cannot drift from the decision it describes.

**Everything is self-hosted.** The fonts ship as packages. No CDN, no runtime
asset fetch, no environment map from the network.

### Consequences

### Positive
- The decision card shows its most important property — the overlap between
  channels — as a shape instead of a percentage.
- One set of tokens and one set of primitives replace six hand-rolled
  variants of the same idea.
- The application works offline and air-gapped, as Phase 5 requires.
- Every new visual is covered by a test that does not need a GPU.

### Negative
- react-three-fiber v8 is the React 18 line and it is no longer maintained.
  It is pinned exactly and isolated behind one lazy import boundary so that
  the eventual React 19 upgrade is a bounded change.
- `three` must be pinned below 0.186, which removed the shadow map type
  react-three-fiber v8 selects by default.
- The 3D layer adds roughly 265KB gzipped to the bundle when it is loaded.
  It is code-split, so the rest of the application does not pay for it.
- A design system has to be maintained. Adding a primitive is cheap;
  changing a token is cheap; drifting away from the tokens is not.

### Neutral
- The colours, radii and type scale are not invented. They are the pmndrs
  tokens, which means a future reader can look them up.
- The analytics page starts using Recharts, which is already a dependency and
  was already paid for.

## Alternatives Considered

| Alternative | Pros | Cons | Why Not Chosen |
|-------------|------|------|----------------|
| Keep the current UI and restyle it | Smallest diff, no new dependencies | The structure is the problem: six variants of the same banner, hand-drawn charts, CDN fonts. A restyle would have to keep working around all of it | The layout, the component vocabulary and the data presentation all change; there is nothing left to keep |
| Build the spatial view with two-dimensional SVG only | No WebGL, no bundle cost, fully accessible | Loses the depth cue that makes overlap legible; less distinctive | Kept as the first slice and as the fallback. It is the floor, not the ceiling |
| Adopt react-three-fiber v9 and upgrade to React 19 | The maintained line | A coordinated React major upgrade across the whole application, four package bumps, and a React 19 migration across every component and every test | Deferred. The 3D layer is isolated so this can be done later without a rewrite |
| Approximate the distributions from the mean and the standard deviation | No backend change, tiny payload | Invents a shape the engine never sampled. The engine samples from log-normal price and cost factors, so a normal approximation is visibly wrong in the tails | Rejected. The engine's own samples are available and are reproducible, so there is no reason to approximate |
| Store the density histogram in the decisions table | One read, no replay cost | A schema migration and a column that must be kept in step with the engine's output | The replay path already exists for reproducibility, and it cannot drift from the decision |
| Fetch an HDRI environment map from the pmndrs CDN | Better looking renders | A third-party network call at render time, which the offline and air-gapped requirements forbid | Lights only, no environment map |

## Implementation Notes

**Tokens.** The palette is expressed as red, green and blue channels so that
Tailwind's opacity modifiers work — `ring-foreground/10`, `bg-primary/5`. The
colour ramp is the pmndrs MD3 output for the lime seed and the warm neutral
seed, not a hand-picked set of hexes.

**Fonts.** `@fontsource-variable/inter` and `@fontsource-variable/inconsolata`,
both SIL OFL 1.1, replace the Google Fonts link. They register as
`"Inter Variable"` and `"Inconsolata Variable"`; the Tailwind font stacks must
quote those names.

**The 3D boundary.** All WebGL code lives under `frontend/src/three/` and is
reached only through a dynamic `import()`. A support probe checks for a WebGL
context before the canvas is mounted. The probe is not optional: react-three-
fiber v8 catches a context-creation failure in an internal error boundary and
renders nothing, without logging, which is exactly the silent failure the
project forbids.

**Testing the 3D layer.** `@react-three/test-renderer` asserts against the
scene graph without a GPU. It exposes `create()`, not `render()`. Component
tests mock the canvas boundary.

**The distribution endpoint.** `GET /api/v1/decisions/{id}/distribution`
replays the decision from its stored snapshot using the same path as the
existing reproducibility endpoint, then bins the draws. The response carries
the snapshot hash so the caller can prove which decision the picture belongs
to.

## Related ADRs
- [ADR-001: Technology Stack Selection](ADR-001-technology-stack.md)
- [ADR-002: Decision Engine Design](ADR-002-decision-engine.md)
- [ADR-004: Offline inspection storage and the fake-indexeddb test shim](ADR-004-offline-inspection-storage.md)
- [ADR-005: The feedback loop analytics](ADR-005-feedback-loop-analytics.md)

## References
- pmndrs design system — <https://github.com/pmndrs/design-system>
- pmndrs documentation template — <https://github.com/pmndrs/docs>
- react-three-fiber — <https://github.com/pmndrs/react-three-fiber>
- Material Design 3 colour roles — <https://m3.material.io/styles/color-system/roles>

---

*Date: 2026-10-21*
*Author: ai-minimax-m3.1-flash-ses_ea3fe5877ffewBwwUBDer1x75Z*
*Reviewers: [pending]*

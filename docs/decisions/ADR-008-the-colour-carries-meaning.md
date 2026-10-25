# ADR-008: The colour carries meaning, and the light theme is the face

## Status
Accepted — amends [ADR-006](ADR-006-design-system-and-spatial-decision-console.md)

## Context

ADR-006 built the design system on two choices that this phase revisits. It
shipped the application **dark by default**, because the accent has to read
against the surface and because the pmndrs mark itself is a render on black.
And it made **lime the only saturated colour in the chrome**, with the rest of
the surface in a warm neutral ramp.

Both choices were right for the moment they were made, and both have since met
their limits.

The palette that followed grew past the chrome. F11.5 drew an animated mesh
gradient whose four colours are a warm base, a lime, a teal and a sand. F11.6
put frosted glass and a liquid mark on the account pages. The token set
already defines **seven accent hues and five callout roles in both themes** —
lime, teal, cyan, purple, orange, yellow, red, and note, tip, important,
warning, caution — and almost none of it is ever drawn: charts, statuses,
category chips, badges and the channel landscape all render in lime on a warm
neutral, so a page has one colour and a reader has no way to tell two series
apart by looking.

Reviewed against five references — react-three-fiber, shadergradient,
liquid-glass-js, liquid-logo and theatre — the surface has three defects that
are visible in a screenshot and none of them is a missing component:

1. **The application opens dark, and the dark is black.** `--background` is
   `#141311`, which is a warm near-black: the page reads as a screen switched
   off rather than as a colour. On a warehouse display, and on most laptops,
   that is the whole first impression.
2. **The three-dimensional landscape is a black rectangle.** The stage the
   ridges are drawn on has no floor, no light of its own and no colour of its
   own, so a reader sees a dark panel with two thin curves in it — which is
   precisely the silent blank that ADR-006 and the plan's risk list forbid.
3. **Nothing moves.** Every transition is 150ms on one curve. The reference
   surfaces earn their feel from choreography — things arriving in order,
   settling, responding to a pointer — and none of that needs a library.

The direction is: open in light, keep a dark that is visibly of a hue, let the
existing accents carry meaning instead of lime carrying everything, and give
the application motion that costs nothing to ship.

## Decision

### 1. The light theme is the default face

A first run, with no stored preference, opens **light**: warm off-white
surfaces, lime on light. The dark theme stays as a real choice, remembered like
any other preference. ADR-006's reasoning is not discarded — it is relocated:
the accent still reads against the surface it is drawn on, in both themes; the
pmndrs mark still renders on black in the identity artwork; and the gradient
backdrop has a palette for each theme, as F11.5 already wrote.

### 2. The dark theme is an ink, not a black

The dark tokens are re-toned onto a deep teal ink — a background with a hue in
it rather than a warm grey near zero — and the ramp above it (card, popover,
muted, accent, hairline) follows the same hue. No surface in either theme
resolves to pure black, and the shader backdrop's dark palette is re-based on
the same ink so the two agree.

### 3. Colour carries meaning; lime stays the brand

The saturated hues are not decoration and are not free to be sprinkled. One
rule, used everywhere and testable:

| Hue | Means |
|---|---|
| lime | the brand, the recommended thing, the value that was actually recovered |
| teal | the measured thing: a baseline, an observation, a reference |
| cyan | a third series when two are not enough |
| orange | a caution: stale, ageing, needs attention |
| red | destructive or missing |
| purple | an estimate or a model artefact |
| yellow | the synthetic badge, as it already is |

Charts, statuses, category chips and the channel landscape all read by that
rule, in both themes. This supersedes "lime is the chrome's only saturated
colour": lime is the only saturated *brand* colour; the others appear only
where they say something.

Two things are deliberately outside the rule, and each has a logic of its
own. The **grade ramp on the shop window** is a quality scale rather than a
data hue: the good grades are drawn calm and the poor ones loud, so a buyer
scanning the window sees the one device that is not good without reading a
word. And the **category chips** are left uncoloured: a category is not a
statement about the data, and thirteen hues across a filter row would be
thirteen colours saying nothing.

### 4. The contrast suite measures the real tokens

`contrast.test.ts` measured a copy of the token values pasted into the test,
so a colour could be changed in `index.css` and the suite would keep passing
against numbers nothing on the page uses any more. It now parses the stylesheet
and measures what is actually declared, per theme. A pair that fails is a
failing test, as F9.1 always said.

### 5. Motion is written, not installed

Entrance choreography, a route transition, and hover and press states, built
from CSS keyframes and the Web Animations API. One duration and one curve for
short things, a slower one for arrival, and `prefers-reduced-motion` switching
the whole lot off — which the global reduced-motion rule in `index.css`
already does for anything driven by CSS.

No motion library is added. The five references are used for what they are
worth as references: the scene craft of react-three-fiber, the gradient of
shadergradient, the refraction of liquid-glass-js, the wobbling mark of
liquid-logo, and the *choreography* of theatre — sequences, stagger, arrival —
expressed in this codebase's own idioms.

### 6. The backdrop and the glass are application-wide

The gradient and the frosted panels leave the account pages and become the
frame of the console and the floor of the shop window, behind the content, in
both themes, with the CSS fallback where WebGL is unavailable and a still
frame where the reader has asked for less motion (both already implemented in
F11.5, now simply used more widely).

## Consequences

### Positive
- The first impression is a product with a palette, not a dark utility.
- A reader can tell two series apart in a chart, a stale source from a fresh
  one, and one category of device from another, without reading a legend.
- The landscape reads as a scene: coloured ridges on a floor, framed.
- Motion costs nothing to download and nothing to disable.
- The contrast gate measures reality, so future palette changes are checked
  rather than assumed.

### Negative
- Three themes' worth of screenshots change (console dark, console light,
  storefront dark, storefront light), and the visual baselines have to be
  regenerated on every machine that compares them.
- "Colour means something" is a rule that can be broken later. It is only
  enforced by review unless a test is written for each site.
- A light default is a change from what the plan has said since Phase 8. The
  plan and ADR-006 are amended here so that a future reader finds one story.
- Deep teal ink is a taste. If a customer wants the old near-black, it is one
  token block away.

### Neutral
- The token *names* do not change, so the component layer is untouched by the
  re-tone; only the values move.
- No dependency, no migration, no API change.

## Alternatives Considered

| Alternative | Pros | Cons | Why Not Chosen |
|-------------|------|------|----------------|
| Keep dark by default and only re-tone it | No change in behaviour | The complaint is that the product reads as black; a re-toned black on the first run is still a dark first impression | Rejected. Light becomes the default; dark remains one click away |
| Add `@theatre/core` for the choreography | A real timeline and a Studio authoring tool | ~40kB, a Studio dev dependency, an authoring workflow for sequences that are four keyframes long, and an ADR to justify it | Rejected. The sequences here are short and code-authored; CSS and the Web Animations API do them in a fraction of a kilobyte |
| Add `framer-motion` | Pleasant React API for entrances and layout | A new runtime dependency for animations the browser already has | Rejected, same reason |
| Pick new hexes for the dark theme by eye | Fast | ADR-006's tokens are generated, not hand-picked, and hand-picked hexes are how the six duplicate banners of Phase 8 happened | Rejected. The existing token structure is re-based, and the contrast suite decides whether a value stands |
| Give every card its own hue | Colourful | Colour that means nothing is noise, and it competes with the one hue that does mean something | Rejected. The hue table in Decision 3 is the discipline |
| Recolour the charts only | Small diff | Leaves the default theme, the landscape and the shop window out of the same story | Rejected. One palette, both applications, both themes |

## Implementation Notes

**Where the default lives.** Two places agree on it: the inline script in
`frontend/index.html`, which runs before the first paint, and the
`defaultPreference` prop of `ThemeProvider`. Both say `light`; the stored
preference still wins.

**The ink.** The dark block in `index.css` keeps every token name and changes
every value in one ramp: background, card, popover, muted, accent, surfaces 2
to 4, border, input, outline and hairline, all on the same hue. The primary
lime, the callout roles and the seven accents keep their contrast relationships
and are re-checked by the suite.

**Parsing the stylesheet.** The suite reads `frontend/src/index.css`, extracts
the `:root` and `.dark` declarations, and resolves the pairs by token name. The
pair list stays in the test because the *pairing* — which foreground sits on
which background — is a design decision; only the numbers come from the file.

**The hue rule.** Each site that draws several series maps an identifier to a
token name through one small function with its own test (the channels of the
landscape, the series of a chart, the categories of the window), so the mapping
is written once and can be reviewed once.

## Related ADRs
- [ADR-006: The design system and the spatial decision console](ADR-006-design-system-and-spatial-decision-console.md)
- [ADR-007: The shop window is a separate application](ADR-007-the-shop-window-is-a-separate-application.md)

## References
- react-three-fiber — <https://github.com/pmndrs/react-three-fiber>
- shadergradient — <https://github.com/ruucm/shadergradient>
- liquid-glass-js — <https://github.com/dashersw/liquid-glass-js>
- liquid-logo — <https://github.com/collidingScopes/liquid-logo>
- theatre — <https://github.com/theatre-js/theatre>
- Material Design 3 colour roles — <https://m3.material.io/styles/color-system/roles>

---

*Date: 2026-10-24*
*Author: ai-mimo-ses_e90b81ea6ffe*
*Reviewers: [pending]*

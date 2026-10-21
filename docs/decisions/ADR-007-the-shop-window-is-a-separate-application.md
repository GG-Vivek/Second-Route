# ADR-007: The shop window is a separate application

## Status
Accepted

## Context

SecondRoute is an operator's console. It takes a return in, inspects it,
decides what should happen to it, and shows the decision. Every screen in it
is for staff: the decision card, the channel landscape, the analytics, the
backtest.

None of it is for a buyer. A buyer wants to know what is for sale, what it
looks like, what it costs and whether it works. Every one of those questions
has an answer in the data already — the units, the inspections, the
photographs, the decisions — and none of them was ever assembled into
something a person could read.

The operator's console is not the place for it. Three reasons, and the third
is the one that decided it.

**The audience is different.** The console is behind a sign-in and behind the
operator's navigation. A shop window is walked past by people who will never
know the word "disposition".

**The data is different.** The console shows the serial number, the reason the
device came back, the notes the operator wrote, the cost of handling it, the
engine's confidence and the flip conditions. None of that is a buyer's
business, and the buyer must not be able to read it either.

**The shape is different.** The console is a set of tools: filters, tables,
charts, an audit log. A shop window is one page with photographs on it. They
do not want to be the same application, and pretending otherwise makes both
of them worse.

## Decision

We will build the shop window as a **separate application** in
`frontend-public/`, served on its own port, reading a new public endpoint.

**The endpoint is the only door.** `GET /api/v1/public/listings` and
`GET /api/v1/public/listings/{id}` are the only endpoints in the system that
are meant to be read by anybody at all. There is no sign-in: a browser on a
train can call them. What comes back is a listing and nothing else — no
serial, no return reason, no notes, no cost breakdown, no confidence, no
organisation. The price on a listing is the expected **sale price**, not the
net: the net is the margin, and the margin is the business's own business.

**A listing is a device that is being sold.** The engine recommends a channel
for every unit, and only the resale channels put a price on the window. Only
the **latest** decision counts: a unit whose first decision said to sell it
and whose second said to recycle it is being recycled. A unit that has been
sold, recycled or given away has gone.

**The tenant is named by the deployment.** `PUBLIC_ORG_ID` decides whose stock
the window shows. A caller cannot choose: a shop window shows one shop's
stock. Outside production the development header is still honoured, so that a
developer can point a window at their own data.

**The design system is shared, not copied.** The tokens, the nineteen
primitives and the theme provider live in `frontend/src` and are reached
through a path alias, so the shop window and the console cannot drift apart.
The Tailwind scale is imported rather than copied for the same reason. The
bundle the storefront produces is self-contained, so the two applications can
still be deployed apart — the storefront's Docker image carries the shared
source with it.

**Photographs say whether they may be published.** One of the four angles the
inspection form takes is a photograph of the label on the bottom of the
device, and the label carries the serial number. The serial was not in the
response, but it was in the picture. A photograph now carries a `published`
flag, and the window only shows the photographs that may be published.

**The price says what it is.** The price is a modelled expectation, not an
asking price somebody set, and the window says so — on the page when the
prices are synthetic, and on the device's own page always. AGENTS.md requires
that synthetic and real are never mixed without explicit separation, and a
shop window that quietly shows a modelled price as if it were a real one is
exactly that failure.

## Consequences

**The operator's application does not change.** The storefront reads the
shared source; the console keeps everything it had. The only coupling is the
alias, and it is one-directional.

**The shared design system cannot become two design systems.** That is the
point. The cost is that the shared source lives in the console's directory
rather than in a package of its own, and a copy of the Tailwind scale would
have been worse than the coupling. If a third application appears, the shared
source should move to `packages/design-system/` and both applications should
depend on it.

**Two deployments.** The window is public and the console is not, so they can
be secured, measured and scaled apart: the console behind a sign-in on one
host, the window on another. The staging stack builds them into two volumes
and Caddy serves them from two hosts.

**The public endpoint is a contract.** Anything that is added to a listing is
added to what the public can read. The tests in `tests/phase10/` assert the
absence of the business's fields, so a field that leaks is a failing test
rather than a surprise.

**A photograph of a serial number is still a photograph of a serial number.**
The `published` flag closes the hole the seed opened, and the flag is
per-photograph and default-on. In production the operator must choose which
photographs are published; nothing forces them to.

**Known limitations.**
- The window shows the operator's photographs without a second crop or
  render. A photograph of a customer, or of a label that is not the device's
  own, would be published. The flag is the mitigation; a marking step in the
  photograph pipeline is the real one.
- There is no basket and no checkout. A buyer can see a device and cannot buy
  it. The second is a separate piece of work and it is not a small one.
- The price is the engine's expected sale price, which is a market estimate
  and not a price the business has committed to. A real shop would set the
  price and let the engine tell it whether that was wise.

## Alternatives considered

**One application, two shells.** The same React application with a public
route and a router that decides which shell to show. Rejected: the two
audiences want different data, and one application that fetches the union of
what both audiences may read is one application that may read too much. The
public surface would be whatever the operator's surface did not happen to
hide.

**The console's pages, restyled for buyers.** Rejected: the console's data
model is the operator's. The serial, the notes and the costs are in it, and a
restyle does not take them out.

**Serving the window from the backend as server-rendered HTML.** Rejected: it
would be a second rendering model, a second design system implementation and
a second place for the tokens to live. The shop window deserves the same
care as the console, and that means the same primitives.

**Copying the design system into `frontend-public/`.** Rejected: two copies
of the token set are two token sets that disagree, and the disagreement is
found by a customer looking at the shop window.

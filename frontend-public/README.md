# The storefront

The shop window. A separate application, on its own port, that shows the
devices that are for sale to anybody at all.

It is not the operator's console with the serial number hidden. It is a
different audience, a different set of data and a different shape, and
ADR-007 records the decision.

## Running it

```bash
# The API has to be running.
cd ../backend && .venv/bin/uvicorn secondroute.api.main:app --port 8000

# And this.
npm install
npm run dev
```

It is then on <http://localhost:5174>.

## What it reads

Two endpoints, and nothing else:

| Endpoint | What it answers |
|---|---|
| `GET /api/v1/public/listings` | The devices that are on sale |
| `GET /api/v1/public/listings/{id}` | One device, with its photographs and its test results |

Both are public. There is no sign-in, and there is no operator's surface
behind them.

A listing carries the name, the condition, the photographs, the tests, the
accessories and the price. It carries no serial number, no return reason, no
operator's note, no cost breakdown, no confidence and no organisation. The
tests in `backend/tests/phase10/` assert the absence of those, so a field
that leaks is a failing test rather than a surprise.

## Whose stock it shows

`PUBLIC_ORG_ID` decides. The deployment names the organisation, not the
caller: a shop window shows one shop's stock.

Outside production the backend also honours the `X-Org-Id` header, so a
developer can point the window at their own data. The storefront sends the
header when `VITE_ORG_ID` is set in `.env`.

```bash
VITE_PROXY_TARGET=http://127.0.0.1:8000
VITE_ORG_ID=29b1eb4b-d353-4193-b173-538175757067
```

## The design system

The tokens, the nineteen primitives, the theme provider and the Tailwind
scale live in `../frontend/src` and are reached through a path alias in
`vite.config.ts`. They are shared rather than copied, because two copies of
the token set are two token sets that disagree, and the disagreement is found
by a customer looking at the shop window.

The bundle this produces is self-contained, so the two applications can be
deployed apart: the container image carries the shared source with it.

## The tests

```bash
npm run test:run       # the unit tests
npm run test:e2e       # the visual suite
npm run lint
```

The visual suite is hermetic. The API is answered with fixtures and the
photographs with a picture, so the screenshots are the same whatever is in
the database.

## The photographs

The window shows the photographs the inspection took. One of the four angles
is a photograph of the label on the bottom of the device, and the label
carries the serial number, so that photograph is marked as not publishable
and the window does not show it.

A photograph says whether it may be published. In production the operator
chooses.

/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL: string
  /** Where the Vite dev server forwards the API to. */
  readonly VITE_PROXY_TARGET: string
  /**
   * The organisation the development server acts on behalf of.
   *
   * Outside production the backend accepts the tenant in this header, so
   * that the application can be used without a login. It is ignored in
   * production.
   */
  readonly VITE_ORG_ID: string
  /**
   * Where the shop window is served from.
   *
   * The window is another application — it is the public storefront, and
   * in development it is served on another port. A page that sends a
   * reader there has to be told the address rather than guess it.
   */
  readonly VITE_SHOP_URL?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}

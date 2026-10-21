/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Where the API is, when it is not on the same origin. */
  readonly VITE_API_BASE?: string
  /** Where the Vite dev server forwards the API to. */
  readonly VITE_PROXY_TARGET: string
  /**
   * The organisation the development server acts on behalf of.
   *
   * Outside production the backend accepts the tenant in this header, so
   * that the storefront can be used without a deployment naming one. It
   * is ignored in production.
   */
  readonly VITE_ORG_ID: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}

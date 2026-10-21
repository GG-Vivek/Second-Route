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
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}

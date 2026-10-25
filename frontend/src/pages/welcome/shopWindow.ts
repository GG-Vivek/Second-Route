/**
 * Where the shop window is served from (F11.10).
 *
 * The window is another application on another origin, so a page that
 * sends a reader there links out of this one rather than routing within
 * it. In development it is the second Vite server; in the compose stack
 * it is the storefront service. The address is configuration, not
 * something a page should guess at the point where it renders.
 */
export const SHOP_WINDOW = import.meta.env.VITE_SHOP_URL || 'http://localhost:5174'

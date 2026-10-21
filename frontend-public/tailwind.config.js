/**
 * The Tailwind configuration for the storefront (Phase 10).
 *
 * The scale is the operator application's, imported rather than copied:
 * the shop window and the console have to look like one product. Only
 * the list of places the class names can appear is different, because
 * the storefront also uses the primitives from the shared design
 * system, which live one directory up.
 */

import admin from '../frontend/tailwind.config.js'

/** @type {import('tailwindcss').Config} */
export default {
  ...admin,
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}',
    // The shared design system.
    '../frontend/src/components/ui/**/*.{ts,tsx}',
    '../frontend/src/theme/**/*.{ts,tsx}',
  ],
}

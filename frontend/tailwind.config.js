/**
 * The Tailwind configuration (F8.1).
 *
 * The scales here are the pmndrs ones: a radius scale on a ten pixel base,
 * the seven brand accents, the five callout roles, a hairline-first
 * elevation model, and a single transition curve.
 *
 * Every colour is read from a CSS custom property so that the light and the
 * dark themes share one class name and the alpha modifiers keep working.
 */

/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        border: "rgb(var(--border) / <alpha-value>)",
        input: "rgb(var(--input) / <alpha-value>)",
        ring: "rgb(var(--ring) / <alpha-value>)",
        outline: "rgb(var(--outline) / <alpha-value>)",
        background: "rgb(var(--background) / <alpha-value>)",
        foreground: "rgb(var(--foreground) / <alpha-value>)",
        primary: {
          DEFAULT: "rgb(var(--primary) / <alpha-value>)",
          foreground: "rgb(var(--primary-foreground) / <alpha-value>)",
          container: "rgb(var(--primary-container) / <alpha-value>)",
          "on-container": "rgb(var(--on-primary-container) / <alpha-value>)",
        },
        secondary: {
          DEFAULT: "rgb(var(--secondary) / <alpha-value>)",
          foreground: "rgb(var(--secondary-foreground) / <alpha-value>)",
        },
        destructive: {
          DEFAULT: "rgb(var(--destructive) / <alpha-value>)",
          foreground: "rgb(var(--destructive-foreground) / <alpha-value>)",
        },
        muted: {
          DEFAULT: "rgb(var(--muted) / <alpha-value>)",
          foreground: "rgb(var(--muted-foreground) / <alpha-value>)",
        },
        accent: {
          DEFAULT: "rgb(var(--accent) / <alpha-value>)",
          foreground: "rgb(var(--accent-foreground) / <alpha-value>)",
        },
        popover: {
          DEFAULT: "rgb(var(--popover) / <alpha-value>)",
          foreground: "rgb(var(--popover-foreground) / <alpha-value>)",
        },
        card: {
          DEFAULT: "rgb(var(--card) / <alpha-value>)",
          foreground: "rgb(var(--card-foreground) / <alpha-value>)",
        },
        surface: {
          2: "rgb(var(--surface-2) / <alpha-value>)",
          3: "rgb(var(--surface-3) / <alpha-value>)",
          4: "rgb(var(--surface-4) / <alpha-value>)",
        },
        code: {
          DEFAULT: "rgb(var(--code-background) / <alpha-value>)",
          foreground: "rgb(var(--code-foreground) / <alpha-value>)",
        },

        /* The seven brand accents. */
        lime: {
          DEFAULT: "rgb(var(--lime) / <alpha-value>)",
          container: "rgb(var(--lime-container) / <alpha-value>)",
          on: "rgb(var(--on-lime) / <alpha-value>)",
        },
        teal: {
          DEFAULT: "rgb(var(--teal) / <alpha-value>)",
          container: "rgb(var(--teal-container) / <alpha-value>)",
          on: "rgb(var(--on-teal) / <alpha-value>)",
        },
        cyan: {
          DEFAULT: "rgb(var(--cyan) / <alpha-value>)",
          container: "rgb(var(--cyan-container) / <alpha-value>)",
          on: "rgb(var(--on-cyan) / <alpha-value>)",
        },
        purple: {
          DEFAULT: "rgb(var(--purple) / <alpha-value>)",
          container: "rgb(var(--purple-container) / <alpha-value>)",
          on: "rgb(var(--on-purple) / <alpha-value>)",
        },
        orange: {
          DEFAULT: "rgb(var(--orange) / <alpha-value>)",
          container: "rgb(var(--orange-container) / <alpha-value>)",
          on: "rgb(var(--on-orange) / <alpha-value>)",
        },
        yellow: {
          DEFAULT: "rgb(var(--yellow) / <alpha-value>)",
          container: "rgb(var(--yellow-container) / <alpha-value>)",
          on: "rgb(var(--on-yellow) / <alpha-value>)",
        },
        red: {
          DEFAULT: "rgb(var(--red) / <alpha-value>)",
          container: "rgb(var(--red-container) / <alpha-value>)",
          on: "rgb(var(--on-red) / <alpha-value>)",
        },

        /* The five callout roles. */
        note: {
          DEFAULT: "rgb(var(--note) / <alpha-value>)",
          container: "rgb(var(--note-container) / <alpha-value>)",
          "on-container": "rgb(var(--on-note-container) / <alpha-value>)",
        },
        tip: {
          DEFAULT: "rgb(var(--tip) / <alpha-value>)",
          container: "rgb(var(--tip-container) / <alpha-value>)",
          "on-container": "rgb(var(--on-tip-container) / <alpha-value>)",
        },
        important: {
          DEFAULT: "rgb(var(--important) / <alpha-value>)",
          container: "rgb(var(--important-container) / <alpha-value>)",
          "on-container": "rgb(var(--on-important-container) / <alpha-value>)",
        },
        warning: {
          DEFAULT: "rgb(var(--warning) / <alpha-value>)",
          container: "rgb(var(--warning-container) / <alpha-value>)",
          "on-container": "rgb(var(--on-warning-container) / <alpha-value>)",
        },
        caution: {
          DEFAULT: "rgb(var(--caution) / <alpha-value>)",
          container: "rgb(var(--caution-container) / <alpha-value>)",
          "on-container": "rgb(var(--on-caution-container) / <alpha-value>)",
        },
      },
      borderRadius: {
        xs: "var(--radius-xs)",
        sm: "var(--radius-sm)",
        md: "var(--radius-md)",
        lg: "var(--radius-lg)",
        xl: "var(--radius-xl)",
        "2xl": "var(--radius-2xl)",
        "3xl": "var(--radius-3xl)",
        "4xl": "var(--radius-4xl)",
      },
      fontFamily: {
        sans: ['"Inter Variable"', 'Inter', 'system-ui', 'sans-serif'],
        mono: ['"Inconsolata Variable"', 'Inconsolata', 'ui-monospace', 'monospace'],
      },
      fontSize: {
        // The pmndrs type scale, in the Tailwind v4 defaults.
        xs: ["0.75rem", { lineHeight: "1rem" }],
        sm: ["0.875rem", { lineHeight: "1.25rem" }],
        base: ["1rem", { lineHeight: "1.5rem" }],
        lg: ["1.125rem", { lineHeight: "1.75rem" }],
        xl: ["1.25rem", { lineHeight: "1.75rem" }],
        "2xl": ["1.5rem", { lineHeight: "2rem" }],
        "3xl": ["1.875rem", { lineHeight: "2.25rem" }],
        "4xl": ["2.25rem", { lineHeight: "2.5rem" }],
        "5xl": ["3rem", { lineHeight: "1" }],
        "6xl": ["3.75rem", { lineHeight: "1" }],
      },
      boxShadow: {
        "2xs": "0 1px rgb(0 0 0 / 0.05)",
        xs: "0 1px 2px 0 rgb(0 0 0 / 0.05)",
        sm: "0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1)",
        md: "0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)",
        lg: "0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)",
        xl: "0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1)",
        "2xl": "0 25px 50px -12px rgb(0 0 0 / 0.25)",
      },
      transitionDuration: {
        DEFAULT: "150ms",
      },
      transitionTimingFunction: {
        DEFAULT: "cubic-bezier(0.4, 0, 0.2, 1)",
        out: "cubic-bezier(0, 0, 0.2, 1)",
        in: "cubic-bezier(0.4, 0, 1, 1)",
      },
      keyframes: {
        "fade-in": {
          from: { opacity: "0" },
          to: { opacity: "1" },
        },
        "slide-in-from-top": {
          from: { transform: "translateY(-10px)", opacity: "0" },
          to: { transform: "translateY(0)", opacity: "1" },
        },
        "scale-in": {
          from: { transform: "scale(0.96)", opacity: "0" },
          to: { transform: "scale(1)", opacity: "1" },
        },
      },
      animation: {
        "fade-in": "fade-in 150ms cubic-bezier(0, 0, 0.2, 1)",
        "slide-in-from-top": "slide-in-from-top 200ms cubic-bezier(0, 0, 0.2, 1)",
        "scale-in": "scale-in 150ms cubic-bezier(0, 0, 0.2, 1)",
      },
      spacing: {
        sidebar: "18rem",
        "sidebar-rail": "3rem",
        header: "4rem",
      },
      maxWidth: {
        prose: "56rem",
      },
    },
  },
  plugins: [],
}

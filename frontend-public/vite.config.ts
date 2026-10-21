import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'
import { fileURLToPath } from 'url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

/**
 * The storefront (Phase 10).
 *
 * This is a separate application on its own port. It reads the public
 * listings endpoint and nothing else: there is no sign-in, and the
 * operator's own surfaces are not here at all.
 *
 * The design system is shared with the operator's application rather
 * than copied. The tokens, the primitives and the theme provider live
 * in ``frontend/src`` and are reached through the aliases below, so the
 * shop window and the console cannot drift apart. The bundle this
 * produces is self-contained, so the two can still be deployed apart.
 */
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, __dirname, '')
  const apiTarget = env.VITE_PROXY_TARGET || process.env.VITE_PROXY_TARGET || 'http://backend:8000'

  // The shared source lives one directory up.
  const shared = path.resolve(__dirname, '../frontend/src')

  return {
    plugins: [react()],
    resolve: {
      // The design system is outside this application's root, so the
      // packages it imports have to be resolved from here rather than
      // from the directory the file happens to be in. Without this the
      // container build has no ``frontend/node_modules`` to find them
      // in, and a developer's machine has two copies of React.
      dedupe: [
        'react',
        'react-dom',
        'react-router-dom',
        'clsx',
        'tailwind-merge',
        'lucide-react',
      ],
      alias: [
        // The design system.
        { find: /^@design-system\/(.*)$/, replacement: `${shared}/$1` },
        { find: /^@design-system$/, replacement: shared },
        // The primitives reach for these two by the paths they have in
        // the operator's application, so they have to resolve there too.
        { find: /^@\/utils\/cn$/, replacement: `${shared}/utils/cn.ts` },
        { find: /^@\/types\/decision$/, replacement: `${shared}/types/decision.ts` },
        // This application's own code.
        { find: /^@\//, replacement: `${path.resolve(__dirname, 'src')}/` },
      ],
    },
    server: {
      port: 5174,
      host: '0.0.0.0',
      // The design system is outside this application's root.
      fs: {
        allow: [path.resolve(__dirname, '..')],
      },
      proxy: {
        '/api': {
          target: apiTarget,
          changeOrigin: true,
        },
        // The photographs.
        '/uploads': {
          target: apiTarget,
          changeOrigin: true,
        },
      },
    },
    build: {
      outDir: 'dist',
      sourcemap: true,
    },
    test: {
      globals: true,
      environment: 'jsdom',
      setupFiles: ['./src/test/setup.ts'],
      include: ['src/**/*.{test,spec}.{ts,tsx}'],
      coverage: {
        provider: 'v8',
        reporter: ['text', 'lcov', 'json', 'html'],
        reportsDirectory: './coverage',
      },
    },
  }
})

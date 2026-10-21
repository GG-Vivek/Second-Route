import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'
import { fileURLToPath } from 'url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  // Where the API is.
  //
  // In the compose stack the backend answers to the service name, and the
  // browser never resolves it: the request goes to the Vite dev server,
  // which forwards it inside the compose network. On a developer machine
  // there is no such network, so the address has to be the one the backend
  // actually listens on.
  //
  // The env file is read here rather than from ``process.env``, because
  // the config is evaluated before Vite loads the env files: a
  // ``VITE_PROXY_TARGET`` in ``frontend/.env`` would otherwise be ignored.
  const env = loadEnv(mode, __dirname, '')
  const apiTarget = env.VITE_PROXY_TARGET || process.env.VITE_PROXY_TARGET || 'http://backend:8000'

  return {
    plugins: [react()],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
      },
    },
    server: {
      port: 5173,
      host: '0.0.0.0',
      proxy: {
        '/api': {
          target: apiTarget,
          changeOrigin: true,
        },
        '/health': {
          target: apiTarget,
          changeOrigin: true,
        },
        // The photographs. Without this the development server answers
        // with the page itself, and the browser is given a document where
        // it asked for an image.
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
      setupFiles: ['./src/test/setup.ts', './src/test/fakeIndexedDb.ts'],
      include: ['src/**/*.{test,spec}.{ts,tsx}'],
      coverage: {
        provider: 'v8',
        reporter: ['text', 'lcov', 'json', 'html'],
        reportsDirectory: './coverage',
      },
    },
  }
})

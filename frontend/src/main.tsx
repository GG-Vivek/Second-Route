import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

// The fonts ship with the application. Nothing is fetched from a third
// party at runtime, which is what the offline requirement needs.
import '@fontsource-variable/inter'
import '@fontsource-variable/inconsolata'

import { OfflineProvider } from './offline'
import { ThemeProvider } from './theme'
import { App } from './App'
import './index.css'

// Create query client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
})

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <OfflineProvider>
          <BrowserRouter>
            <App />
          </BrowserRouter>
        </OfflineProvider>
      </ThemeProvider>
    </QueryClientProvider>
  </React.StrictMode>
)

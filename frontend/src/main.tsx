import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AuthProvider } from './auth/AuthContext'
import { ApiError } from './lib/api'
import App from './App'
import './index.css'

// One QueryClient for the whole app: it caches server data and powers our
// fetching/mutations (TanStack Query).
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // 4xx responses are deterministic (401 expired token, 404 no such board)
      // — retrying them just delays the error state. Network blips/5xx still
      // get two retries.
      retry: (failureCount, error) =>
        !(error instanceof ApiError && error.status < 500) && failureCount < 2,
      // Board data stays live via the WebSocket (which invalidates on every
      // event), so a refetch on each window focus/mount only adds churn — and
      // it's the refetch that could clobber an in-flight optimistic drag.
      staleTime: 30_000,
    },
  },
})

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    {/* Providers wrap the app so every component can use them:
        - QueryClientProvider -> useQuery / useMutation
        - BrowserRouter       -> routing
        - AuthProvider        -> who's logged in (our context) */}
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AuthProvider>
          <App />
        </AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
)

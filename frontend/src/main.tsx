import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AuthProvider } from './auth/AuthContext'
import App from './App'
import './index.css'

// One QueryClient for the whole app: it caches server data and powers our
// fetching/mutations (TanStack Query).
const queryClient = new QueryClient()

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

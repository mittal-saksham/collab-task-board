// Auth state for the whole app, exposed via React Context.
// Holds the current user, and login/signup/logout actions. The JWT itself lives
// in localStorage (see lib/api.ts); this context tracks the resulting User.

import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from 'react'
import type { User } from '../types'
import * as api from '../lib/api'

interface AuthValue {
  user: User | null
  isLoading: boolean // true while we check an existing token on first load
  login: (email: string, password: string) => Promise<void>
  signup: (email: string, password: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthValue | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  // Any 401 from any request (an expired token mid-session) drops the session,
  // so the user is sent to login instead of silently losing every write.
  // Registered once; apiFetch has already cleared the token when this fires.
  useEffect(() => {
    api.setOnUnauthorized(() => setUser(null))
    return () => api.setOnUnauthorized(null)
  }, [])

  // On first load: if a token exists, try to fetch the user it belongs to.
  // Only a 401 means the token is bad (apiFetch clears it); a network error or
  // 5xx — e.g. the free-tier backend cold-starting — must NOT log the user out,
  // so we keep the token and let the next reload try again.
  useEffect(() => {
    if (!api.getToken()) {
      setIsLoading(false)
      return
    }
    api
      .getMe()
      .then(setUser)
      .catch(() => {
        /* token kept unless apiFetch saw a 401 */
      })
      .finally(() => setIsLoading(false))
  }, [])

  async function login(email: string, password: string) {
    const token = await api.login(email, password)
    api.setToken(token)
    setUser(await api.getMe())
  }

  async function signup(email: string, password: string) {
    await api.signup(email, password)
    await login(email, password) // auto-login right after signing up
  }

  function logout() {
    api.setToken(null)
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, isLoading, login, signup, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

// Convenience hook: `const { user, login } = useAuth()`.
export function useAuth(): AuthValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within <AuthProvider>')
  return ctx
}

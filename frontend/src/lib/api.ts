// Tiny typed wrapper around fetch: prefixes the API base URL, attaches the JWT,
// parses JSON, and turns non-2xx responses into a thrown ApiError carrying the
// backend's `detail` message (so the UI can show it).

import type { User } from '../types'

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'
const TOKEN_KEY = 'token'

// --- token storage (localStorage, per our auth design) ---
export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}
export function setToken(token: string | null): void {
  if (token) localStorage.setItem(TOKEN_KEY, token)
  else localStorage.removeItem(TOKEN_KEY)
}

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function extractDetail(res: Response, fallback: string): Promise<string> {
  try {
    const data = await res.json()
    if (typeof data?.detail === 'string') return data.detail
  } catch {
    /* body wasn't JSON */
  }
  return fallback
}

// Generic JSON request. <T> is the expected response type.
export async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers)
  const token = getToken()
  if (token) headers.set('Authorization', `Bearer ${token}`)
  if (options.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }

  const res = await fetch(`${API_URL}${path}`, { ...options, headers })
  if (!res.ok) {
    throw new ApiError(res.status, await extractDetail(res, res.statusText))
  }
  if (res.status === 204) return undefined as T // No Content
  return (await res.json()) as T
}

// --- Auth endpoints ---

export async function login(email: string, password: string): Promise<string> {
  // The login route uses the OAuth2 password flow: form-encoded username+password.
  const body = new URLSearchParams({ username: email, password })
  const res = await fetch(`${API_URL}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body,
  })
  if (!res.ok) {
    throw new ApiError(res.status, await extractDetail(res, 'Login failed'))
  }
  const data = (await res.json()) as { access_token: string }
  return data.access_token
}

export async function signup(email: string, password: string): Promise<User> {
  return apiFetch<User>('/auth/signup', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  })
}

export async function getMe(): Promise<User> {
  return apiFetch<User>('/auth/me')
}

// A route guard. Used as a parent <Route element={<ProtectedRoute />}>; its
// nested routes only render when a user is logged in, otherwise we redirect to
// /login. <Outlet /> is where React Router renders the matched child route.

import { Navigate, Outlet } from 'react-router-dom'
import { useAuth } from './AuthContext'

export function ProtectedRoute() {
  const { user, isLoading } = useAuth()

  if (isLoading) {
    return <div className="p-8 text-slate-500">Loading…</div>
  }
  if (!user) {
    return <Navigate to="/login" replace />
  }
  return <Outlet />
}

import { Navigate, Outlet, useLocation } from 'react-router'
import Spinner from '../components/ui/Spinner'
import useAuth from '../hooks/useAuth'

/**
 * Login and register pages. Once the user is logged in, send them to the page they
 * originally asked for (saved by ProtectedRoute), or to the dashboard.
 */
export default function GuestRoute() {
  const { status } = useAuth()
  const location = useLocation()

  if (status === 'loading') return <Spinner fullPage />
  if (status === 'authenticated') return <Navigate to={location.state?.from ?? '/dashboard'} replace />
  return <Outlet />
}

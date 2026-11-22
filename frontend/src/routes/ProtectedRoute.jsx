import { Navigate, Outlet, useLocation } from 'react-router'
import Spinner from '../components/ui/Spinner'
import useAuth from '../hooks/useAuth'

/** Only logged-in users get through; everyone else is sent to /login. */
export default function ProtectedRoute() {
  const { status } = useAuth()
  const location = useLocation()

  if (status === 'loading') return <Spinner fullPage />
  if (status === 'anonymous') return <Navigate to="/login" replace state={{ from: location.pathname }} />
  return <Outlet />
}

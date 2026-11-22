import { Link, NavLink, Outlet } from 'react-router'
import Button from '../components/ui/Button'
import ThemeToggle from '../components/ui/ThemeToggle'
import useAuth from '../hooks/useAuth'

const NAV_ITEMS = [
  { to: '/dashboard', label: 'Dashboard' },
  { to: '/chat', label: 'Chat' },
  { to: '/documents', label: 'Documents' },
  { to: '/search', label: 'Search' },
  { to: '/evaluation', label: 'Evaluation' },
  { to: '/profile', label: 'Profile' },
]

export default function AppLayout() {
  const { user, logout } = useAuth()

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-30 border-b border-slate-200 bg-white/90 backdrop-blur dark:border-slate-800 dark:bg-slate-950/90">
        <div className="mx-auto flex max-w-[96rem] flex-wrap items-center gap-x-6 gap-y-2 px-4 py-3">
          <Link to="/dashboard" className="text-lg font-bold tracking-tight">
            DocuMind <span className="text-indigo-600 dark:text-indigo-400">AI</span>
          </Link>
          {/* On phones the nav moves to its own row and scrolls sideways */}
          <nav className="order-last -mx-1 flex w-full gap-1 overflow-x-auto md:order-none md:mx-0 md:w-auto">
            {NAV_ITEMS.map(({ to, label }) => (
              <NavLink
                key={to}
                to={to}
                className={({ isActive }) =>
                  `shrink-0 rounded-lg px-3 py-1.5 text-sm font-medium ${
                    isActive
                      ? 'bg-indigo-50 text-indigo-700 dark:bg-indigo-950/60 dark:text-indigo-300'
                      : 'text-slate-600 hover:bg-slate-100 dark:text-slate-400 dark:hover:bg-slate-800'
                  }`
                }
              >
                {label}
              </NavLink>
            ))}
          </nav>
          <div className="ml-auto flex items-center gap-2">
            <span className="hidden text-sm text-slate-600 lg:inline dark:text-slate-400">{user.full_name}</span>
            <ThemeToggle />
            <Button variant="secondary" onClick={logout}>
              Log out
            </Button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-[96rem] px-4 py-8">
        <Outlet />
      </main>
    </div>
  )
}

import { Link } from 'react-router'

export default function NotFoundPage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-4 px-4 text-center">
      <p className="text-6xl font-bold text-indigo-600 dark:text-indigo-400">404</p>
      <h1 className="text-2xl font-semibold">Page not found</h1>
      <Link to="/" className="rounded-lg bg-indigo-600 px-4 py-2 font-medium text-white hover:bg-indigo-700">
        Back to home
      </Link>
    </main>
  )
}

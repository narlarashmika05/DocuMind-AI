import { Link } from 'react-router'

export default function AuthCard({ title, subtitle, footer, children }) {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center px-4 py-12">
      <Link to="/" className="mb-8 text-2xl font-bold tracking-tight">
        DocuMind <span className="text-indigo-600 dark:text-indigo-400">AI</span>
      </Link>
      <section className="w-full max-w-sm rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-8 shadow-sm">
        <h1 className="text-xl font-semibold">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">{subtitle}</p>}
        <div className="mt-6">{children}</div>
      </section>
      {footer && <p className="mt-6 text-sm text-slate-600 dark:text-slate-400">{footer}</p>}
    </main>
  )
}

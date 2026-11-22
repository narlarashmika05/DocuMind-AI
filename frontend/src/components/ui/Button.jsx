import Spinner from './Spinner'

const VARIANTS = {
  primary: 'bg-indigo-600 text-white hover:bg-indigo-700',
  secondary: 'border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800',
  danger: 'text-red-600 hover:bg-red-50 dark:text-red-400 dark:hover:bg-red-950/40',
  ghost: 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800',
}

export default function Button({
  variant = 'primary',
  loading = false,
  disabled = false,
  className = '',
  children,
  ...props
}) {
  return (
    <button
      type="button"
      {...props}
      disabled={loading || disabled}
      className={`inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 disabled:cursor-not-allowed disabled:opacity-60 ${VARIANTS[variant]} ${className}`}
    >
      {loading && <Spinner className="h-4 w-4" />}
      {children}
    </button>
  )
}

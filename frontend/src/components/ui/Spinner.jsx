export default function Spinner({ fullPage = false, className = 'h-6 w-6' }) {
  const icon = (
    <svg className={`animate-spin text-indigo-600 dark:text-indigo-400 ${className}`} viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" className="opacity-25" />
      <path d="M22 12a10 10 0 0 0-10-10" stroke="currentColor" strokeWidth="4" strokeLinecap="round" />
    </svg>
  )

  if (!fullPage) return icon
  return (
    <div className="flex min-h-screen items-center justify-center" role="status" aria-label="Loading">
      {icon}
    </div>
  )
}

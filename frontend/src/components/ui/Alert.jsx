const STYLES = {
  error: 'border-red-200 bg-red-50 text-red-800 dark:border-red-900 dark:bg-red-950/40 dark:text-red-300',
  success: 'border-emerald-200 bg-emerald-50 text-emerald-800 dark:border-emerald-900 dark:bg-emerald-950/40 dark:text-emerald-300',
  warning: 'border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-900 dark:bg-amber-950/40 dark:text-amber-300',
  info: 'border-indigo-200 bg-indigo-50 text-indigo-800 dark:border-indigo-900 dark:bg-indigo-950/40 dark:text-indigo-300',
}

export default function Alert({ type = 'error', children, onClose }) {
  return (
    <div
      role={type === 'error' ? 'alert' : 'status'}
      className={`flex items-start gap-3 rounded-lg border px-4 py-3 text-sm ${STYLES[type]}`}
    >
      <div className="flex-1">{children}</div>
      {onClose && (
        <button onClick={onClose} className="font-semibold opacity-60 hover:opacity-100" aria-label="Dismiss">
          ✕
        </button>
      )}
    </div>
  )
}

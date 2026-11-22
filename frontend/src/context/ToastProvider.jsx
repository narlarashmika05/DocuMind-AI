import { useCallback, useRef, useState } from 'react'
import { ToastContext } from './toast-context'

const STYLES = {
  info: 'border-slate-200 bg-white text-slate-800 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100',
  success: 'border-emerald-200 bg-emerald-50 text-emerald-900 dark:border-emerald-900 dark:bg-emerald-950 dark:text-emerald-200',
  error: 'border-red-200 bg-red-50 text-red-900 dark:border-red-900 dark:bg-red-950 dark:text-red-200',
}
const ICONS = { info: 'ℹ', success: '✓', error: '!' }

export default function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([])
  const nextId = useRef(1)

  const dismiss = useCallback((id) => setToasts((list) => list.filter((t) => t.id !== id)), [])

  const notify = useCallback(
    (message, type = 'info') => {
      const id = nextId.current++
      setToasts((list) => [...list.slice(-3), { id, message, type }]) // at most 4 on screen
      setTimeout(() => dismiss(id), 5000)
    },
    [dismiss],
  )

  return (
    <ToastContext.Provider value={notify}>
      {children}
      <div
        className="pointer-events-none fixed bottom-4 right-4 z-50 flex w-80 max-w-[calc(100vw-2rem)] flex-col gap-2"
        aria-live="polite"
      >
        {toasts.map((toast) => (
          <div
            key={toast.id}
            role={toast.type === 'error' ? 'alert' : 'status'}
            className={`pointer-events-auto flex items-start gap-2 rounded-xl border px-4 py-3 text-sm shadow-lg ${STYLES[toast.type]}`}
          >
            <span className="font-bold" aria-hidden="true">
              {ICONS[toast.type]}
            </span>
            <span className="flex-1">{toast.message}</span>
            <button onClick={() => dismiss(toast.id)} className="opacity-60 hover:opacity-100" aria-label="Dismiss">
              ✕
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}

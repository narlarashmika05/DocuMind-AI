import { useId } from 'react'

export default function TextField({ label, hint, ...inputProps }) {
  const id = useId()
  return (
    <div>
      <label htmlFor={id} className="block text-sm font-medium text-slate-700 dark:text-slate-300">
        {label}
      </label>
      <input
        id={id}
        className="mt-1 block w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-2 text-sm shadow-sm placeholder:text-slate-400 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 disabled:bg-slate-100 dark:disabled:bg-slate-800 disabled:text-slate-500"
        {...inputProps}
      />
      {hint && <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">{hint}</p>}
    </div>
  )
}

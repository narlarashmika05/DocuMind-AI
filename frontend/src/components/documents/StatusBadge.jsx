const STYLES = {
  uploaded: 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300',
  processing: 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300',
  ready: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300',
  failed: 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300',
}

export default function StatusBadge({ status }) {
  return (
    <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ${STYLES[status] ?? STYLES.uploaded}`}>
      {status}
    </span>
  )
}

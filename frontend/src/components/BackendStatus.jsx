import { useEffect, useState } from 'react'
import { getHealth } from '../api/health'

const STATES = {
  loading: { dot: 'bg-slate-400 animate-pulse', label: 'Checking backend…' },
  ok: { dot: 'bg-emerald-500', label: 'All systems operational' },
  degraded: { dot: 'bg-amber-500', label: 'API running, database unavailable' },
  offline: { dot: 'bg-red-500', label: 'Cannot reach the backend' },
}

const INITIAL = { state: 'loading', health: null, error: '' }

async function fetchStatus() {
  try {
    const health = await getHealth()
    return { state: health.status === 'ok' ? 'ok' : 'degraded', health, error: '' }
  } catch (err) {
    return { state: 'offline', health: null, error: err.message }
  }
}

export default function BackendStatus() {
  const [{ state, health, error }, setStatus] = useState(INITIAL)

  useEffect(() => {
    let active = true // ignore the result if the component unmounted mid-request
    fetchStatus().then((result) => active && setStatus(result))
    return () => {
      active = false
    }
  }, [])

  const retry = () => {
    setStatus(INITIAL)
    fetchStatus().then(setStatus)
  }

  const { dot, label } = STATES[state]

  return (
    <section className="w-full max-w-md rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-6 shadow-sm">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">System status</h2>
        <button
          onClick={retry}
          disabled={state === 'loading'}
          className="rounded-lg px-3 py-1 text-sm font-medium text-indigo-600 dark:text-indigo-400 hover:bg-indigo-50 dark:hover:bg-indigo-950/50 disabled:opacity-50"
        >
          Refresh
        </button>
      </div>

      <div className="mt-4 flex items-center gap-3">
        <span className={`h-3 w-3 rounded-full ${dot}`} />
        <span className="font-medium">{label}</span>
      </div>

      {health && (
        <dl className="mt-5 grid grid-cols-2 gap-y-2 text-sm">
          <dt className="text-slate-500 dark:text-slate-400">API version</dt>
          <dd className="text-right font-mono">{health.version}</dd>
          <dt className="text-slate-500 dark:text-slate-400">Environment</dt>
          <dd className="text-right font-mono">{health.environment}</dd>
          <dt className="text-slate-500 dark:text-slate-400">Database</dt>
          <dd className="text-right font-mono">{health.database}</dd>
          {health.database_latency_ms != null && (
            <>
              <dt className="text-slate-500 dark:text-slate-400">DB latency</dt>
              <dd className="text-right font-mono">{health.database_latency_ms} ms</dd>
            </>
          )}
        </dl>
      )}

      {state === 'offline' && (
        <p className="mt-4 rounded-lg bg-red-50 p-3 text-sm text-red-700 dark:bg-red-950/40 dark:text-red-300">
          {error}. Is the FastAPI server running on port 8000, and is this origin listed in CORS_ORIGINS?
        </p>
      )}
    </section>
  )
}

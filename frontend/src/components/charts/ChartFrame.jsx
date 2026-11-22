import { useState } from 'react'

import { SERIES_COLORS } from './colors'

/** Title, legend (2+ series), the chart, and a "Show table" view so no information is colour-only. */
export default function ChartFrame({ title, subtitle, series, table, children }) {
  const [showTable, setShowTable] = useState(false)
  return (
    <figure className="rounded-2xl border border-slate-200 bg-[var(--chart-surface)] p-5 shadow-sm dark:border-slate-800">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <figcaption>
          <h3 className="font-semibold text-[var(--chart-text)]">{title}</h3>
          {subtitle && <p className="mt-0.5 text-sm text-[var(--chart-text-muted)]">{subtitle}</p>}
        </figcaption>
        <button
          onClick={() => setShowTable(!showTable)}
          className="rounded-lg px-2 py-1 text-xs text-[var(--chart-text-muted)] hover:bg-slate-100 dark:hover:bg-slate-800"
        >
          {showTable ? 'Show chart' : 'Show table'}
        </button>
      </div>
      {series.length > 1 && !showTable && (
        <ul className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-[var(--chart-text-muted)]">
          {series.map((s, i) => (
            <li key={s} className="flex items-center gap-1.5">
              <span className="h-2.5 w-2.5 rounded-sm" style={{ background: SERIES_COLORS[i] }} />
              {s}
            </li>
          ))}
        </ul>
      )}
      <div className="mt-3">{showTable ? table : children}</div>
    </figure>
  )
}

export function DataTable({ columns, rows }) {
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full text-sm">
        <thead>
          <tr className="border-b border-[var(--chart-grid)] text-left text-[var(--chart-text-muted)]">
            {columns.map((c) => (
              <th key={c} className="px-2 py-1.5 font-medium">
                {c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, r) => (
            <tr key={r} className="border-b border-[var(--chart-grid)] text-[var(--chart-text)]">
              {row.map((cell, c) => (
                <td key={c} className="px-2 py-1.5 tabular-nums">
                  {typeof cell === 'number' ? cell.toFixed(3) : cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

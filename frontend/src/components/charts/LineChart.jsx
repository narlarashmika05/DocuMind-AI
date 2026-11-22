import { useState } from 'react'
import ChartFrame, { DataTable } from './ChartFrame'
import { SERIES_COLORS } from './colors'

const W = 640
const H = 260
const PAD = { top: 16, right: 16, bottom: 40, left: 36 }

/** x: numbers; series: [{ label, values }] (max 3), values 0..1. Crosshair + tooltip on hover. */
export default function LineChart({ title, subtitle, x, series, xLabel }) {
  const [hover, setHover] = useState(null)
  const plotW = W - PAD.left - PAD.right
  const plotH = H - PAD.top - PAD.bottom
  const px = (i) => PAD.left + (i / Math.max(x.length - 1, 1)) * plotW // evenly spaced thresholds
  const py = (v) => PAD.top + plotH - v * plotH

  const table = <DataTable columns={[xLabel, ...series.map((s) => s.label)]} rows={x.map((v, i) => [v, ...series.map((s) => s.values[i])])} />

  return (
    <ChartFrame title={title} subtitle={subtitle} series={series.map((s) => s.label)} table={table}>
      <div className="relative">
        <svg
          viewBox={`0 0 ${W} ${H}`}
          className="w-full"
          role="img"
          aria-label={title}
          onMouseLeave={() => setHover(null)}
          onMouseMove={(event) => {
            const rect = event.currentTarget.getBoundingClientRect()
            const svgX = ((event.clientX - rect.left) / rect.width) * W
            const index = Math.round(((svgX - PAD.left) / plotW) * (x.length - 1))
            setHover(index >= 0 && index < x.length ? index : null)
          }}
        >
          {[0, 0.25, 0.5, 0.75, 1].map((t) => (
            <g key={t}>
              <line x1={PAD.left} x2={W - PAD.right} y1={py(t)} y2={py(t)} stroke="var(--chart-grid)" />
              <text x={PAD.left - 6} y={py(t) + 3} textAnchor="end" fontSize="10" fill="var(--chart-text-muted)">
                {t.toFixed(2)}
              </text>
            </g>
          ))}
          {x.map((v, i) => (
            <text key={v} x={px(i)} y={H - PAD.bottom + 16} textAnchor="middle" fontSize="10.5" fill="var(--chart-text-muted)">
              {v}
            </text>
          ))}
          <text x={W / 2} y={H - 6} textAnchor="middle" fontSize="10" fill="var(--chart-text-muted)">
            {xLabel}
          </text>
          {hover !== null && (
            <line x1={px(hover)} x2={px(hover)} y1={PAD.top} y2={PAD.top + plotH} stroke="var(--chart-text-muted)" strokeDasharray="3 3" />
          )}
          {series.map((s, i) => (
            <g key={s.label}>
              <polyline
                points={s.values.map((v, j) => `${px(j)},${py(v)}`).join(' ')}
                fill="none"
                stroke={SERIES_COLORS[i]}
                strokeWidth="2"
              />
              {s.values.map((v, j) => (
                <circle
                  key={j}
                  cx={px(j)}
                  cy={py(v)}
                  r={hover === j ? 5 : 4}
                  fill={SERIES_COLORS[i]}
                  stroke="var(--chart-surface)"
                  strokeWidth="2"
                />
              ))}
            </g>
          ))}
        </svg>
        {hover !== null && (
          <div
            className="pointer-events-none absolute top-2 z-10 -translate-x-1/2 rounded-lg border border-[var(--chart-grid)] bg-[var(--chart-surface)] px-2.5 py-1.5 text-xs shadow-md"
            style={{ left: `${(px(hover) / W) * 100}%` }}
          >
            <p className="text-[var(--chart-text-muted)]">
              {xLabel}: {x[hover]}
            </p>
            {series.map((s, i) => (
              <p key={s.label} className="flex items-center gap-1.5 text-[var(--chart-text)]">
                <span className="h-2 w-2 rounded-full" style={{ background: SERIES_COLORS[i] }} />
                {s.label}: <span className="font-semibold tabular-nums">{s.values[hover].toFixed(2)}</span>
              </p>
            ))}
          </div>
        )}
      </div>
    </ChartFrame>
  )
}

import { useState } from 'react'
import ChartFrame, { DataTable } from './ChartFrame'
import { SERIES_COLORS } from './colors'

const W = 640
const H = 260
const PAD = { top: 16, right: 8, bottom: 40, left: 36 }
const GAP = 2 // surface gap between neighbouring bars

/** Bar with a 4px rounded top, square at the baseline. */
function barPath(x, y, width, height) {
  const r = Math.min(4, width / 2, height)
  return `M${x},${y + height} V${y + r} Q${x},${y} ${x + r},${y} H${x + width - r} Q${x + width},${y} ${x + width},${y + r} V${y + height} Z`
}

/** groups: x-axis labels; series: [{ label, values }] (max 3); values 0..yMax. */
export default function GroupedBarChart({ title, subtitle, groups, series, yMax = 1, yLabel = '' }) {
  const [hover, setHover] = useState(null)
  const plotW = W - PAD.left - PAD.right
  const plotH = H - PAD.top - PAD.bottom
  const groupW = plotW / groups.length
  const barW = Math.min(36, (groupW * 0.75) / series.length)
  const y = (v) => PAD.top + plotH - (v / yMax) * plotH
  const ticks = [0, 0.25, 0.5, 0.75, 1].map((t) => t * yMax)

  const table = (
    <DataTable columns={['', ...series.map((s) => s.label)]} rows={groups.map((g, i) => [g, ...series.map((s) => s.values[i])])} />
  )

  return (
    <ChartFrame title={title} subtitle={subtitle} series={series.map((s) => s.label)} table={table}>
      <div className="relative">
        <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img" aria-label={title}>
          {ticks.map((t) => (
            <g key={t}>
              <line x1={PAD.left} x2={W - PAD.right} y1={y(t)} y2={y(t)} stroke="var(--chart-grid)" strokeWidth="1" />
              <text x={PAD.left - 6} y={y(t) + 3} textAnchor="end" fontSize="10" fill="var(--chart-text-muted)">
                {t.toFixed(2)}
              </text>
            </g>
          ))}
          {yLabel && (
            <text x={4} y={PAD.top - 4} fontSize="10" fill="var(--chart-text-muted)">
              {yLabel}
            </text>
          )}
          {groups.map((group, g) => {
            const start = PAD.left + g * groupW + (groupW - barW * series.length) / 2
            return (
              <g key={group}>
                {series.map((s, i) => {
                  const value = s.values[g] ?? 0
                  const x = start + i * barW
                  const active = hover?.g === g && hover?.i === i
                  return (
                    <g key={s.label}>
                      <path
                        d={barPath(x + GAP / 2, y(value), barW - GAP, Math.max(PAD.top + plotH - y(value), 0.5))}
                        fill={SERIES_COLORS[i]}
                        opacity={hover && !active ? 0.55 : 1}
                      />
                      {/* invisible, taller hit target */}
                      <rect
                        x={x}
                        y={PAD.top}
                        width={barW}
                        height={plotH}
                        fill="transparent"
                        onMouseEnter={() => setHover({ g, i, x: x + barW / 2, y: y(value) })}
                        onMouseLeave={() => setHover(null)}
                      />
                    </g>
                  )
                })}
                <text
                  x={PAD.left + g * groupW + groupW / 2}
                  y={H - PAD.bottom + 16}
                  textAnchor="middle"
                  fontSize="10.5"
                  fill="var(--chart-text-muted)"
                >
                  {group}
                </text>
              </g>
            )
          })}
        </svg>
        {hover && (
          <div
            className="pointer-events-none absolute z-10 -translate-x-1/2 -translate-y-full rounded-lg border border-[var(--chart-grid)] bg-[var(--chart-surface)] px-2.5 py-1.5 text-xs shadow-md"
            style={{ left: `${(hover.x / W) * 100}%`, top: `${(hover.y / H) * 100}%` }}
          >
            <p className="text-[var(--chart-text-muted)]">{groups[hover.g]}</p>
            <p className="flex items-center gap-1.5 text-[var(--chart-text)]">
              <span className="h-2 w-2 rounded-sm" style={{ background: SERIES_COLORS[hover.i] }} />
              {series[hover.i].label}: <span className="font-semibold tabular-nums">{series[hover.i].values[hover.g]?.toFixed(3)}</span>
            </p>
          </div>
        )}
      </div>
    </ChartFrame>
  )
}

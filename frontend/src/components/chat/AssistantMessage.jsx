import { useState } from 'react'
import { summarize, verdictInfo } from '../../utils/verification'

function CitationChip({ number, active, onClick }) {
  return (
    <button
      onClick={onClick}
      className={`mx-0.5 inline-flex h-5 min-w-5 items-center justify-center rounded px-1 align-text-top text-xs font-semibold ${
        active
          ? 'bg-indigo-600 text-white'
          : 'bg-indigo-100 text-indigo-700 hover:bg-indigo-200 dark:bg-indigo-900/50 dark:text-indigo-300'
      }`}
      aria-label={`Show source ${number}`}
    >
      {number}
    </button>
  )
}

function VerificationSummary({ message }) {
  const { total, checked, supported, flagged } = summarize(message.claims)
  if (!checked) return null
  const tone = flagged
    ? 'border-red-200 bg-red-50 text-red-800 dark:border-red-900 dark:bg-red-950/40 dark:text-red-300'
    : supported === total
      ? 'border-emerald-200 bg-emerald-50 text-emerald-800 dark:border-emerald-900 dark:bg-emerald-950/40 dark:text-emerald-300'
      : 'border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-900 dark:bg-amber-950/40 dark:text-amber-300'
  return (
    <div className={`mt-3 rounded-lg border px-3 py-2 text-xs ${tone}`}>
      <span className="font-semibold">
        Evidence check: {supported} of {total} statement{total > 1 ? 's' : ''} supported by the sources
      </span>
      {flagged > 0 && <span> · {flagged} not supported — treat with caution</span>}
      {message.faithfulness_score != null && (
        <span className="opacity-75"> · faithfulness {Math.round(message.faithfulness_score * 100)}%</span>
      )}
      <p className="mt-0.5 opacity-75">Automatic checks can be wrong; open the sources to confirm important facts.</p>
    </div>
  )
}

export default function AssistantMessage({ message, activeSource, onSelectSource }) {
  const [showChecks, setShowChecks] = useState(true)
  const insufficient = message.status === 'insufficient_information'
  const translated = message.details?.question_language === 'te' && message.details?.english_question

  return (
    <div className="max-w-3xl">
      <div
        className={`rounded-2xl rounded-tl-sm border px-4 py-3 shadow-sm ${
          insufficient
            ? 'border-slate-200 bg-slate-50 dark:border-slate-700 dark:bg-slate-800/60'
            : 'border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900'
        }`}
      >
        {insufficient && (
          <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">Not enough information</p>
        )}
        <p className="leading-relaxed" lang={message.language}>
          {message.claims.map((claim) => {
            const info = verdictInfo(claim.verdict)
            const highlight = showChecks && !insufficient && info.text
            return (
              <span key={claim.position}>
                <span
                  className={highlight ? `underline decoration-2 underline-offset-4 ${info.text}` : ''}
                  title={showChecks && !insufficient ? `${info.label}: ${info.help}` : undefined}
                >
                  {claim.text_display}
                </span>
                {claim.cited_numbers.map((n) => (
                  <CitationChip key={n} number={n} active={activeSource === n} onClick={() => onSelectSource(n)} />
                ))}{' '}
              </span>
            )
          })}
        </p>

        {!insufficient && showChecks && message.claims.length > 0 && (
          <ul className="mt-3 space-y-1">
            {message.claims.map((claim) => {
              const info = verdictInfo(claim.verdict)
              return (
                <li key={claim.position} className="flex items-start gap-2 text-xs">
                  <span className={`shrink-0 rounded px-1.5 py-0.5 font-semibold ${info.badge}`} title={info.help}>
                    {info.icon} {info.label}
                    {claim.confidence != null && ` · ${Math.round(claim.confidence * 100)}%`}
                  </span>
                  <span className="line-clamp-2 text-slate-600 dark:text-slate-400">{claim.text_display}</span>
                  {claim.evidence_number && (
                    <button
                      className="shrink-0 text-indigo-600 hover:underline dark:text-indigo-400"
                      onClick={() => onSelectSource(claim.evidence_number)}
                    >
                      evidence [{claim.evidence_number}]
                    </button>
                  )}
                </li>
              )
            })}
          </ul>
        )}

        {!insufficient && <VerificationSummary message={message} />}

        {message.details?.warnings?.map((warning) => (
          <p key={warning} className="mt-2 text-xs text-amber-700 dark:text-amber-400">
            ⚠ {warning}
          </p>
        ))}
      </div>

      <div className="mt-1 flex flex-wrap gap-x-3 px-1 text-xs text-slate-400">
        {message.latency_ms != null && <span>{(message.latency_ms / 1000).toFixed(1)} s</span>}
        {message.citations.length > 0 && <span>{message.citations.length} sources</span>}
        {translated && <span title="Question used for search">searched as: “{message.details.english_question}”</span>}
        {!insufficient && message.claims.length > 0 && (
          <button className="hover:text-slate-600" onClick={() => setShowChecks(!showChecks)}>
            {showChecks ? 'Hide' : 'Show'} evidence check
          </button>
        )}
      </div>
    </div>
  )
}

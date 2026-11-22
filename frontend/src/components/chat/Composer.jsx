import { useState } from 'react'
import Button from '../ui/Button'

const LANGUAGES = [
  { value: 'auto', label: 'Answer in question language' },
  { value: 'en', label: 'Answer in English' },
  { value: 'te', label: 'తెలుగులో సమాధానం (Telugu)' },
]

export default function Composer({ onSend, disabled, language, onLanguageChange, documents, scope, onScopeChange }) {
  const [text, setText] = useState('')
  const [showScope, setShowScope] = useState(false)

  function submit(event) {
    event?.preventDefault()
    const question = text.trim()
    if (!question || disabled) return
    onSend(question)
    setText('')
  }

  const readyDocs = documents.filter((d) => d.status === 'ready')
  const toggle = (id) => onScopeChange(scope.includes(id) ? scope.filter((x) => x !== id) : [...scope, id])

  return (
    <form
      onSubmit={submit}
      className="rounded-2xl border border-slate-200 bg-white p-3 shadow-sm dark:border-slate-700 dark:bg-slate-900"
    >
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' && !e.shiftKey) submit(e) // Shift+Enter = new line
        }}
        rows={2}
        maxLength={2000}
        placeholder="Ask a question about your documents… / మీ పత్రాల గురించి ప్రశ్న అడగండి…"
        className="w-full resize-none bg-transparent px-1 text-sm focus:outline-none"
        disabled={disabled}
      />
      <div className="mt-2 flex flex-wrap items-center gap-2">
        <select
          value={language}
          onChange={(e) => onLanguageChange(e.target.value)}
          className="rounded-lg border border-slate-300 bg-white px-2 py-1 text-xs dark:border-slate-600 dark:bg-slate-800"
          aria-label="Answer language"
        >
          {LANGUAGES.map((l) => (
            <option key={l.value} value={l.value}>
              {l.label}
            </option>
          ))}
        </select>

        <div className="relative">
          <button
            type="button"
            onClick={() => setShowScope(!showScope)}
            className="rounded-lg border border-slate-300 px-2 py-1 text-xs hover:bg-slate-50 dark:border-slate-600 dark:hover:bg-slate-800"
          >
            {scope.length ? `${scope.length} document${scope.length > 1 ? 's' : ''} selected` : 'All documents'} ▾
          </button>
          {showScope && (
            <div className="absolute bottom-full left-0 z-10 mb-2 max-h-64 w-72 overflow-y-auto rounded-xl border border-slate-200 bg-white p-2 shadow-lg dark:border-slate-700 dark:bg-slate-900">
              <button
                type="button"
                onClick={() => onScopeChange([])}
                className="w-full rounded px-2 py-1 text-left text-xs font-medium hover:bg-slate-100 dark:hover:bg-slate-800"
              >
                Search all documents
              </button>
              {readyDocs.length === 0 && <p className="px-2 py-1 text-xs text-slate-500">No ready documents.</p>}
              {readyDocs.map((doc) => (
                <label
                  key={doc.id}
                  className="flex cursor-pointer items-center gap-2 rounded px-2 py-1 text-xs hover:bg-slate-100 dark:hover:bg-slate-800"
                >
                  <input type="checkbox" checked={scope.includes(doc.id)} onChange={() => toggle(doc.id)} />
                  <span className="truncate">{doc.title || doc.original_filename}</span>
                </label>
              ))}
            </div>
          )}
        </div>

        <span className="ml-auto hidden text-xs text-slate-400 sm:inline">Enter to send · Shift+Enter for new line</span>
        <Button type="submit" disabled={disabled || !text.trim()}>
          Ask
        </Button>
      </div>
    </form>
  )
}

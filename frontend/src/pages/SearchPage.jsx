import { useState } from 'react'
import { Link } from 'react-router'
import { getErrorMessage } from '../api/client'
import { searchDocuments } from '../api/search'
import Alert from '../components/ui/Alert'
import Button from '../components/ui/Button'

const MODES = [
  { value: 'hybrid', label: 'Hybrid', hint: 'Meaning + keywords, fused with RRF' },
  { value: 'dense', label: 'Semantic', hint: 'Embedding similarity only' },
  { value: 'keyword', label: 'Keyword', hint: 'BM25 only' },
]

export default function SearchPage() {
  const [query, setQuery] = useState('')
  const [mode, setMode] = useState('hybrid')
  const [rerank, setRerank] = useState(true)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(event) {
    event.preventDefault()
    if (!query.trim()) return
    setLoading(true)
    setError('')
    try {
      setResult(await searchDocuments({ query, mode, rerank, topK: 8 }))
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Search</h1>
        <p className="mt-1 text-slate-600 dark:text-slate-400">
          See exactly which passages retrieval finds for a question — the context the AI answers from.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 shadow-sm">
        <div className="flex flex-col gap-3 sm:flex-row">
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Ask in English or తెలుగు…"
            className="flex-1 rounded-lg border border-slate-300 dark:border-slate-700 px-3 py-2 text-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
          />
          <Button type="submit" loading={loading}>
            Search
          </Button>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {MODES.map((m) => (
            <button
              key={m.value}
              type="button"
              title={m.hint}
              onClick={() => setMode(m.value)}
              className={`rounded-full px-3 py-1 text-sm ${
                mode === m.value ? 'bg-indigo-600 text-white' : 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-slate-200'
              }`}
            >
              {m.label}
            </button>
          ))}
          <label className="ml-2 flex items-center gap-2 text-sm text-slate-700 dark:text-slate-300">
            <input type="checkbox" checked={rerank} onChange={(e) => setRerank(e.target.checked)} />
            Rerank with cross-encoder
          </label>
        </div>
      </form>

      {error && <Alert>{error}</Alert>}

      {result && (
        <section className="space-y-3">
          <p className="text-sm text-slate-500 dark:text-slate-400">
            {result.hits.length} passages · {result.mode} · {result.latency_ms} ms
          </p>
          {result.hits.length === 0 && (
            <p className="rounded-2xl border border-dashed border-slate-300 dark:border-slate-700 px-6 py-10 text-center text-slate-500 dark:text-slate-400">
              Nothing found. Upload documents, or wait until they are Ready.
            </p>
          )}
          {result.hits.map((hit, rank) => (
            <article key={hit.chunk_id} className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 shadow-sm">
              <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm">
                <span className="font-semibold text-indigo-600 dark:text-indigo-400">#{rank + 1}</span>
                <Link
                  to={`/documents/${hit.document_id}?page=${hit.page_number}`}
                  className="font-medium hover:text-indigo-600"
                >
                  {hit.document_title} · page {hit.page_number}
                </Link>
                {hit.element_type !== 'text' && (
                  <span className="rounded-full bg-slate-100 dark:bg-slate-800 px-2 py-0.5 text-xs capitalize">{hit.element_type}</span>
                )}
                <span className="ml-auto font-mono text-xs text-slate-500 dark:text-slate-400">score {hit.score.toFixed(3)}</span>
              </div>
              <p className="mt-2 whitespace-pre-line text-sm leading-relaxed text-slate-700 dark:text-slate-300">{hit.text}</p>
            </article>
          ))}
        </section>
      )}
    </div>
  )
}

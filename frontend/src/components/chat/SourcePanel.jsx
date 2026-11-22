import { Link } from 'react-router'
import { elementImagePath, pageImagePath } from '../../api/documents'
import AuthImage from '../ui/AuthImage'
import MarkdownTable from '../ui/MarkdownTable'

function SourceCard({ citation, active, onSelect }) {
  const available = citation.document_id != null
  const isTable = citation.element_type === 'table'
  const isPicture = ['figure', 'image'].includes(citation.element_type)

  return (
    <article
      className={`rounded-xl border p-4 transition-colors ${
        active
          ? 'border-indigo-400 bg-indigo-50/60 dark:border-indigo-500 dark:bg-indigo-950/40'
          : 'border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900'
      }`}
    >
      <button onClick={onSelect} className="flex w-full items-start gap-2 text-left">
        <span className="flex h-6 min-w-6 items-center justify-center rounded bg-indigo-600 px-1 text-xs font-bold text-white">
          {citation.number}
        </span>
        <span className="min-w-0 flex-1">
          <span className="block truncate text-sm font-medium">{citation.document_title}</span>
          <span className="text-xs text-slate-500">
            Page {citation.page_number}
            {citation.element_type !== 'text' && ` · ${citation.element_type}`} · relevance{' '}
            {Math.round(citation.relevance_score * 100)}%
          </span>
        </span>
      </button>

      {active && (
        <div className="mt-3 space-y-3">
          {isPicture && available && citation.element_id && (
            <AuthImage
              path={elementImagePath(citation.document_id, citation.element_id)}
              alt={`Figure from page ${citation.page_number}`}
              className="max-h-64 w-full rounded-lg border border-slate-200 object-contain dark:border-slate-700"
            />
          )}
          {isTable ? (
            <MarkdownTable markdown={citation.snippet.replace(/^Table \(page \d+\):\n/, '')} />
          ) : (
            <p className="whitespace-pre-line text-sm leading-relaxed text-slate-700 dark:text-slate-300">
              {citation.snippet}
            </p>
          )}
          {available ? (
            <>
              <AuthImage
                path={pageImagePath(citation.document_id, citation.page_number, 1)}
                alt={`Page ${citation.page_number}`}
                className="w-full rounded-lg border border-slate-200 dark:border-slate-700"
              />
              <Link
                to={`/documents/${citation.document_id}?page=${citation.page_number}`}
                className="inline-block text-sm font-medium text-indigo-600 hover:underline dark:text-indigo-400"
              >
                Open page {citation.page_number} in the document viewer →
              </Link>
            </>
          ) : (
            <p className="text-xs text-slate-500">The original document has been deleted.</p>
          )}
        </div>
      )}
    </article>
  )
}

export default function SourcePanel({ message, activeSource, onSelectSource }) {
  if (!message?.citations?.length) {
    return (
      <p className="rounded-xl border border-dashed border-slate-300 p-6 text-center text-sm text-slate-500 dark:border-slate-700">
        Sources used for an answer appear here. Click a citation number to see the exact passage and page.
      </p>
    )
  }
  return (
    <div className="space-y-3">
      {message.citations.map((citation) => (
        <SourceCard
          key={citation.number}
          citation={citation}
          active={activeSource === citation.number}
          onSelect={() => onSelectSource(activeSource === citation.number ? null : citation.number)}
        />
      ))}
    </div>
  )
}

import { Link } from 'react-router'
import { isInProgress, stageLabel } from '../../utils/documents'
import { formatBytes, formatDate } from '../../utils/format'
import Button from '../ui/Button'
import StatusBadge from './StatusBadge'

export default function DocumentList({ documents, onView, onDelete, onReprocess, busyId }) {
  return (
    <ul className="divide-y divide-slate-100 dark:divide-slate-800 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm">
      {documents.map((doc) => (
        <li key={doc.id} className="space-y-3 px-5 py-4">
          <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
            <div className="min-w-0 flex-1">
              <Link
                to={`/documents/${doc.id}`}
                className="block truncate font-medium hover:text-indigo-600 dark:hover:text-indigo-400"
                title={doc.original_filename}
              >
                {doc.title || doc.original_filename}
              </Link>
              <p className="mt-0.5 truncate text-sm text-slate-500 dark:text-slate-400">
                {doc.title && `${doc.original_filename} · `}
                {formatBytes(doc.file_size)} · {doc.page_count ?? '—'} pages · uploaded {formatDate(doc.created_at)}
                {doc.is_scanned && ' · scanned'}
              </p>
            </div>
            <StatusBadge status={doc.status} />
            <div className="flex gap-1">
              <Button variant="ghost" onClick={() => onView(doc)}>
                PDF
              </Button>
              {doc.status === 'failed' && (
                <Button variant="ghost" onClick={() => onReprocess(doc)}>
                  Reprocess
                </Button>
              )}
              <Button variant="danger" onClick={() => onDelete(doc)} loading={busyId === doc.id}>
                Delete
              </Button>
            </div>
          </div>

          {isInProgress(doc) && (
            <div>
              <div className="flex justify-between text-xs text-slate-500 dark:text-slate-400">
                <span>{stageLabel(doc)}…</span>
                <span>{doc.progress}%</span>
              </div>
              <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
                <div className="h-full bg-indigo-500 transition-all" style={{ width: `${Math.max(doc.progress, 3)}%` }} />
              </div>
            </div>
          )}
          {doc.status === 'failed' && doc.error_message && <p className="text-sm text-red-600 dark:text-red-400">{doc.error_message}</p>}
          {doc.processing_notes && <p className="text-sm text-amber-700 dark:text-amber-400">⚠ {doc.processing_notes}</p>}
        </li>
      ))}
    </ul>
  )
}

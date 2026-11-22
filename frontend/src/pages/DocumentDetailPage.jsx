import { useEffect, useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router'
import { getErrorMessage } from '../api/client'
import { elementImagePath, getDocument, getPage, listElements, pageImagePath } from '../api/documents'
import StatusBadge from '../components/documents/StatusBadge'
import Alert from '../components/ui/Alert'
import AuthImage from '../components/ui/AuthImage'
import Button from '../components/ui/Button'
import MarkdownTable from '../components/ui/MarkdownTable'
import Spinner from '../components/ui/Spinner'

const METHOD_LABELS = {
  native: 'Text layer',
  ocr: 'OCR',
  empty: 'Blank page',
  ocr_unavailable: 'Scanned (OCR not installed)',
}

function PageContent({ documentId, pageNumber }) {
  const [data, setData] = useState({ key: null, page: null, elements: [], error: '' })
  const key = `${documentId}:${pageNumber}`

  useEffect(() => {
    let active = true
    Promise.all([getPage(documentId, pageNumber), listElements(documentId, { page: pageNumber })])
      .then(([page, elements]) => active && setData({ key, page, elements, error: '' }))
      .catch((err) => active && setData({ key, page: null, elements: [], error: getErrorMessage(err) }))
    return () => {
      active = false
    }
  }, [documentId, pageNumber, key])

  if (data.key !== key) {
    return (
      <div className="flex justify-center py-10">
        <Spinner />
      </div>
    )
  }
  if (data.error) return <Alert>{data.error}</Alert>

  return (
    <div className="space-y-6">
      <section className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 shadow-sm">
        <div className="flex items-center justify-between">
          <h2 className="font-semibold">Extracted text</h2>
          <span className="rounded-full bg-slate-100 dark:bg-slate-800 px-2.5 py-0.5 text-xs text-slate-600 dark:text-slate-400">
            {METHOD_LABELS[data.page.extraction_method] ?? data.page.extraction_method} · {data.page.char_count} chars
          </span>
        </div>
        {data.page.text ? (
          <div className="mt-3 max-h-[32rem] space-y-3 overflow-y-auto text-sm leading-relaxed text-slate-700 dark:text-slate-300">
            {data.page.text.split('\n\n').map((paragraph, i) => (
              <p key={i}>{paragraph}</p>
            ))}
          </div>
        ) : (
          <p className="mt-3 text-sm text-slate-500 dark:text-slate-400">No text on this page.</p>
        )}
      </section>

      {data.elements.map((element) => (
        <section key={element.id} className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 shadow-sm">
          <h3 className="mb-3 text-sm font-semibold capitalize text-slate-600 dark:text-slate-400">{element.element_type}</h3>
          {element.element_type === 'table' ? (
            <MarkdownTable markdown={element.content} />
          ) : (
            <div className="space-y-2">
              <AuthImage
                path={elementImagePath(documentId, element.id)}
                alt={element.content || `${element.element_type} on page ${pageNumber}`}
                className="max-h-80 rounded-lg border border-slate-200 dark:border-slate-800 object-contain"
              />
              {element.content && <p className="text-sm text-slate-700 dark:text-slate-300">{element.content}</p>}
            </div>
          )}
        </section>
      ))}
    </div>
  )
}

export default function DocumentDetailPage() {
  const { id } = useParams()
  const [searchParams, setSearchParams] = useSearchParams()
  const [document, setDocument] = useState(null)
  const [error, setError] = useState('')
  const pageNumber = Number(searchParams.get('page') ?? 1)

  useEffect(() => {
    let active = true
    getDocument(id)
      .then((doc) => active && setDocument(doc))
      .catch((err) => active && setError(getErrorMessage(err)))
    return () => {
      active = false
    }
  }, [id])

  if (error) return <Alert>{error}</Alert>
  if (!document) {
    return (
      <div className="flex justify-center py-10">
        <Spinner />
      </div>
    )
  }

  const pageCount = document.page_count ?? 0
  const goTo = (n) => setSearchParams({ page: String(n) })

  return (
    <div className="space-y-6">
      <div>
        <Link to="/documents" className="text-sm text-indigo-600 dark:text-indigo-400 hover:underline">
          ← All documents
        </Link>
        <div className="mt-2 flex flex-wrap items-center gap-3">
          <h1 className="text-2xl font-semibold">{document.title || document.original_filename}</h1>
          <StatusBadge status={document.status} />
        </div>
        <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
          {document.original_filename} · {pageCount} pages{document.is_scanned && ' · scanned'}
          {document.chunk_count > 0 &&
            ` · ${document.chunk_count} chunks (${document.chunk_strategy}, ${document.embedding_model})`}
        </p>
      </div>

      {document.status !== 'ready' ? (
        <Alert type={document.status === 'failed' ? 'error' : 'info'}>
          {document.status === 'failed'
            ? document.error_message
            : 'This document is still being processed. Check back in a moment.'}
        </Alert>
      ) : (
        <>
          <div className="flex items-center gap-2">
            <Button variant="secondary" disabled={pageNumber <= 1} onClick={() => goTo(pageNumber - 1)}>
              ← Previous
            </Button>
            <span className="px-2 text-sm text-slate-600 dark:text-slate-400">
              Page {pageNumber} of {pageCount}
            </span>
            <Button variant="secondary" disabled={pageNumber >= pageCount} onClick={() => goTo(pageNumber + 1)}>
              Next →
            </Button>
          </div>

          <div className="grid gap-6 lg:grid-cols-2">
            <AuthImage
              path={pageImagePath(id, pageNumber)}
              alt={`Page ${pageNumber}`}
              className="w-full rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm"
            />
            <PageContent documentId={id} pageNumber={pageNumber} />
          </div>
        </>
      )}
    </div>
  )
}

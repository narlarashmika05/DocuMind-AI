import { useCallback, useEffect, useRef, useState } from 'react'
import { getErrorMessage } from '../api/client'
import { deleteDocument, fetchDocumentFile, listDocuments, reprocessDocument } from '../api/documents'
import DocumentList from '../components/documents/DocumentList'
import UploadDropzone from '../components/documents/UploadDropzone'
import Alert from '../components/ui/Alert'
import Spinner from '../components/ui/Spinner'
import usePolling from '../hooks/usePolling'
import useToast from '../hooks/useToast'
import { isInProgress } from '../utils/documents'

export default function DocumentsPage() {
  const [documents, setDocuments] = useState(null) // null = still loading
  const [error, setError] = useState('')
  const [busyId, setBusyId] = useState(null)
  const notify = useToast()
  const previousStatus = useRef({})

  const refresh = useCallback(
    () =>
      listDocuments()
        .then((docs) => {
          // Tell the user when a document they were waiting for finishes processing.
          for (const doc of docs) {
            const before = previousStatus.current[doc.id]
            if (before && before !== doc.status) {
              const name = doc.title || doc.original_filename
              if (doc.status === 'ready') notify(`"${name}" is ready for questions.`, 'success')
              if (doc.status === 'failed') notify(`Processing "${name}" failed.`, 'error')
            }
          }
          previousStatus.current = Object.fromEntries(docs.map((d) => [d.id, d.status]))
          setDocuments(docs)
        })
        .catch((err) => {
          setError(getErrorMessage(err))
          setDocuments((current) => current ?? [])
        }),
    [notify],
  )

  useEffect(() => {
    refresh()
  }, [refresh])

  // While anything is being processed, refresh every 3 seconds to show progress.
  usePolling(refresh, Boolean(documents?.some(isInProgress)))

  function handleUploaded(result) {
    for (const doc of result.uploaded) previousStatus.current[doc.id] = doc.status
    setDocuments((current) => [...result.uploaded, ...current])
  }

  async function handleDelete(doc) {
    if (!window.confirm(`Delete "${doc.original_filename}"? This cannot be undone.`)) return
    setBusyId(doc.id)
    setError('')
    try {
      await deleteDocument(doc.id)
      setDocuments((current) => current.filter((d) => d.id !== doc.id))
      notify(`Deleted "${doc.original_filename}".`, 'success')
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setBusyId(null)
    }
  }

  async function handleReprocess(doc) {
    setError('')
    try {
      const updated = await reprocessDocument(doc.id)
      setDocuments((current) => current.map((d) => (d.id === doc.id ? updated : d)))
    } catch (err) {
      setError(getErrorMessage(err))
    }
  }

  async function handleView(doc) {
    // Open the tab immediately (inside the click) so pop-up blockers allow it.
    const tab = window.open('', '_blank')
    try {
      const blob = await fetchDocumentFile(doc.id)
      const url = URL.createObjectURL(blob)
      tab.location.href = url
      setTimeout(() => URL.revokeObjectURL(url), 60_000)
    } catch (err) {
      tab?.close()
      setError(getErrorMessage(err))
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Documents</h1>
        <p className="mt-1 text-slate-600 dark:text-slate-400">Upload research papers and study material to ask questions about them.</p>
      </div>

      <UploadDropzone onUploaded={handleUploaded} />

      {error && <Alert onClose={() => setError('')}>{error}</Alert>}

      <section className="space-y-3">
        <h2 className="text-lg font-semibold">Your library</h2>
        {documents === null ? (
          <div className="flex justify-center py-10">
            <Spinner />
          </div>
        ) : documents.length === 0 ? (
          <p className="rounded-2xl border border-dashed border-slate-300 dark:border-slate-700 px-6 py-10 text-center text-slate-500 dark:text-slate-400">
            No documents yet. Upload your first PDF above.
          </p>
        ) : (
          <DocumentList
            documents={documents}
            onView={handleView}
            onDelete={handleDelete}
            onReprocess={handleReprocess}
            busyId={busyId}
          />
        )}
      </section>
    </div>
  )
}

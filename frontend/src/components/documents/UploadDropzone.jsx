import { useRef, useState } from 'react'
import { getErrorMessage } from '../../api/client'
import { uploadDocuments } from '../../api/documents'
import { MAX_FILE_SIZE_MB, MAX_FILES_PER_UPLOAD } from '../../config'
import { formatBytes } from '../../utils/format'
import Alert from '../ui/Alert'
import Button from '../ui/Button'

export default function UploadDropzone({ onUploaded }) {
  const inputRef = useRef(null)
  const [files, setFiles] = useState([])
  const [problems, setProblems] = useState([])
  const [dragging, setDragging] = useState(false)
  const [progress, setProgress] = useState(null)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')

  function addFiles(fileList) {
    const rejected = []
    let selected = [...files]
    for (const file of fileList) {
      if (!file.name.toLowerCase().endsWith('.pdf')) {
        rejected.push(`${file.name}: only PDF files are allowed`)
      } else if (file.size > MAX_FILE_SIZE_MB * 1024 * 1024) {
        rejected.push(`${file.name}: larger than ${MAX_FILE_SIZE_MB} MB`)
      } else if (!selected.some((f) => f.name === file.name && f.size === file.size)) {
        selected.push(file)
      }
    }
    if (selected.length > MAX_FILES_PER_UPLOAD) {
      rejected.push(`You can upload at most ${MAX_FILES_PER_UPLOAD} files at once`)
      selected = selected.slice(0, MAX_FILES_PER_UPLOAD)
    }
    setFiles(selected)
    setProblems(rejected)
    setResult(null)
    setError('')
  }

  function handleDrop(event) {
    event.preventDefault()
    setDragging(false)
    addFiles(event.dataTransfer.files)
  }

  async function handleUpload() {
    setError('')
    setProgress(0)
    try {
      const response = await uploadDocuments(files, setProgress)
      setResult(response)
      setFiles([])
      setProblems([])
      onUploaded(response)
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setProgress(null)
    }
  }

  const uploading = progress !== null

  return (
    <section className="space-y-4 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-6 shadow-sm">
      <div
        role="button"
        tabIndex={0}
        onClick={() => inputRef.current.click()}
        onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && inputRef.current.click()}
        onDragOver={(e) => {
          e.preventDefault()
          setDragging(true)
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={handleDrop}
        className={`flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed px-6 py-10 text-center transition-colors ${
          dragging ? 'border-indigo-500 bg-indigo-50 dark:bg-indigo-950/50' : 'border-slate-300 dark:border-slate-700 hover:border-indigo-400 hover:bg-slate-50 dark:hover:bg-slate-800'
        }`}
      >
        <p className="font-medium">Drag and drop PDF files here, or click to browse</p>
        <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
          Up to {MAX_FILES_PER_UPLOAD} files at once, {MAX_FILE_SIZE_MB} MB each
        </p>
        <input
          ref={inputRef}
          type="file"
          accept="application/pdf,.pdf"
          multiple
          hidden
          onChange={(e) => {
            addFiles(e.target.files)
            e.target.value = '' // allow choosing the same file again
          }}
        />
      </div>

      {problems.length > 0 && (
        <Alert type="warning" onClose={() => setProblems([])}>
          <ul className="list-inside list-disc">
            {problems.map((problem) => (
              <li key={problem}>{problem}</li>
            ))}
          </ul>
        </Alert>
      )}

      {files.length > 0 && (
        <div className="space-y-3">
          <ul className="divide-y divide-slate-100 dark:divide-slate-800 rounded-lg border border-slate-200 dark:border-slate-800">
            {files.map((file) => (
              <li key={`${file.name}-${file.size}`} className="flex items-center justify-between gap-3 px-4 py-2 text-sm">
                <span className="truncate">{file.name}</span>
                <span className="flex shrink-0 items-center gap-3 text-slate-500 dark:text-slate-400">
                  {formatBytes(file.size)}
                  {!uploading && (
                    <button
                      onClick={() => setFiles(files.filter((f) => f !== file))}
                      className="text-slate-400 hover:text-red-600"
                      aria-label={`Remove ${file.name}`}
                    >
                      ✕
                    </button>
                  )}
                </span>
              </li>
            ))}
          </ul>

          {uploading && (
            <div className="h-2 overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800" aria-label="Upload progress">
              <div className="h-full bg-indigo-600 transition-all" style={{ width: `${progress}%` }} />
            </div>
          )}

          <Button onClick={handleUpload} loading={uploading}>
            {uploading ? `Uploading… ${progress}%` : `Upload ${files.length} file${files.length > 1 ? 's' : ''}`}
          </Button>
        </div>
      )}

      {error && <Alert onClose={() => setError('')}>{error}</Alert>}

      {result && (
        <div className="space-y-2">
          {result.uploaded.length > 0 && (
            <Alert type="success" onClose={() => setResult(null)}>
              Uploaded {result.uploaded.length} file{result.uploaded.length > 1 ? 's' : ''} successfully.
            </Alert>
          )}
          {result.rejected.length > 0 && (
            <Alert type="warning">
              <p className="font-medium">Some files were not uploaded:</p>
              <ul className="mt-1 list-inside list-disc">
                {result.rejected.map((item) => (
                  <li key={item.filename}>
                    {item.filename}: {item.reason}
                  </li>
                ))}
              </ul>
            </Alert>
          )}
        </div>
      )}
    </section>
  )
}

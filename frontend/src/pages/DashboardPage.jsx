import { useEffect, useState } from 'react'
import { Link } from 'react-router'
import { getErrorMessage } from '../api/client'
import { listDocuments } from '../api/documents'
import BackendStatus from '../components/BackendStatus'
import Alert from '../components/ui/Alert'
import useAuth from '../hooks/useAuth'

function StatCard({ label, value }) {
  return (
    <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 shadow-sm">
      <p className="text-sm text-slate-500 dark:text-slate-400">{label}</p>
      <p className="mt-1 text-3xl font-semibold">{value ?? '—'}</p>
    </div>
  )
}

export default function DashboardPage() {
  const { user } = useAuth()
  const [documents, setDocuments] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true
    listDocuments()
      .then((data) => active && setDocuments(data))
      .catch((err) => active && setError(getErrorMessage(err)))
    return () => {
      active = false
    }
  }, [])

  const count = (status) => documents?.filter((d) => d.status === status).length

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold">Welcome, {user.full_name.split(' ')[0]}</h1>
        <p className="mt-1 text-slate-600 dark:text-slate-400">Here is an overview of your research workspace.</p>
      </div>

      {error && <Alert>{error}</Alert>}

      <div className="grid gap-4 sm:grid-cols-3">
        <StatCard label="Documents" value={documents?.length} />
        <StatCard label="Ready for questions" value={count('ready')} />
        <StatCard label="Waiting for processing" value={documents && count('uploaded') + count('processing')} />
      </div>

      {documents?.length === 0 && (
        <div className="rounded-2xl border border-dashed border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-6 py-10 text-center">
          <p className="font-medium">Your library is empty</p>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">Upload a research paper or study notes to get started.</p>
          <Link
            to="/documents"
            className="mt-4 inline-block rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700"
          >
            Upload documents
          </Link>
        </div>
      )}

      <BackendStatus />
    </div>
  )
}

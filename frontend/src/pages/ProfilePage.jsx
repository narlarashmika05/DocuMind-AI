import { useState } from 'react'
import { getErrorMessage } from '../api/client'
import { changePassword, deleteAccount, updateProfile } from '../api/users'
import Alert from '../components/ui/Alert'
import Button from '../components/ui/Button'
import TextField from '../components/ui/TextField'
import useAuth from '../hooks/useAuth'
import { formatDate } from '../utils/format'
import { passwordProblem } from '../utils/validation'

function Card({ title, children }) {
  return (
    <section className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-6 shadow-sm">
      <h2 className="text-lg font-semibold">{title}</h2>
      <div className="mt-4">{children}</div>
    </section>
  )
}

function ProfileForm() {
  const { user, setUser } = useAuth()
  const [form, setForm] = useState({ fullName: user.full_name, language: user.preferred_language })
  const [message, setMessage] = useState(null)
  const [saving, setSaving] = useState(false)

  async function handleSubmit(event) {
    event.preventDefault()
    setSaving(true)
    setMessage(null)
    try {
      const updated = await updateProfile({ full_name: form.fullName, preferred_language: form.language })
      setUser(updated)
      setMessage({ type: 'success', text: 'Profile saved.' })
    } catch (err) {
      setMessage({ type: 'error', text: getErrorMessage(err) })
    } finally {
      setSaving(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {message && <Alert type={message.type}>{message.text}</Alert>}
      <TextField label="Full name" value={form.fullName} onChange={(e) => setForm({ ...form, fullName: e.target.value })} />
      <TextField label="Email" value={user.email} disabled hint={`Member since ${formatDate(user.created_at)}`} />
      <div>
        <label htmlFor="language" className="block text-sm font-medium text-slate-700 dark:text-slate-300">
          Preferred answer language
        </label>
        <select
          id="language"
          value={form.language}
          onChange={(e) => setForm({ ...form, language: e.target.value })}
          className="mt-1 block w-full rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-2 text-sm shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
        >
          <option value="en">English</option>
          <option value="te">తెలుగు (Telugu)</option>
        </select>
      </div>
      <Button type="submit" loading={saving}>
        Save changes
      </Button>
    </form>
  )
}

const EMPTY_PASSWORDS = { current: '', next: '', confirm: '' }

function PasswordForm() {
  const [form, setForm] = useState(EMPTY_PASSWORDS)
  const [message, setMessage] = useState(null)
  const [saving, setSaving] = useState(false)

  const update = (field) => (event) => setForm({ ...form, [field]: event.target.value })

  async function handleSubmit(event) {
    event.preventDefault()
    const problem = passwordProblem(form.next) || (form.next !== form.confirm && 'New passwords do not match')
    if (problem) {
      setMessage({ type: 'error', text: problem })
      return
    }
    setSaving(true)
    setMessage(null)
    try {
      await changePassword(form.current, form.next)
      setForm(EMPTY_PASSWORDS)
      setMessage({ type: 'success', text: 'Password changed. Your other devices have been logged out.' })
    } catch (err) {
      setMessage({ type: 'error', text: getErrorMessage(err) })
    } finally {
      setSaving(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4" noValidate>
      {message && <Alert type={message.type}>{message.text}</Alert>}
      <TextField label="Current password" type="password" autoComplete="current-password" value={form.current} onChange={update('current')} />
      <TextField
        label="New password"
        type="password"
        autoComplete="new-password"
        hint="At least 8 characters, including a letter and a number."
        value={form.next}
        onChange={update('next')}
      />
      <TextField label="Confirm new password" type="password" autoComplete="new-password" value={form.confirm} onChange={update('confirm')} />
      <Button type="submit" loading={saving}>
        Change password
      </Button>
    </form>
  )
}

function DeleteAccount() {
  const { logout } = useAuth()
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [deleting, setDeleting] = useState(false)

  async function handleSubmit(event) {
    event.preventDefault()
    if (!window.confirm('Delete your account, all documents and all conversations permanently?')) return
    setDeleting(true)
    setError('')
    try {
      await deleteAccount(password)
      await logout().catch(() => {}) // the session is already gone on the server
    } catch (err) {
      setError(getErrorMessage(err))
      setDeleting(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <p className="text-sm text-slate-600 dark:text-slate-400">
        Permanently deletes your account, uploaded files, extracted images, search index and conversations. This cannot be
        undone.
      </p>
      {error && <Alert>{error}</Alert>}
      <TextField
        label="Confirm with your password"
        type="password"
        autoComplete="current-password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
      />
      <Button type="submit" variant="danger" loading={deleting} disabled={!password} className="border border-red-300 dark:border-red-800">
        Delete my account
      </Button>
    </form>
  )
}

export default function ProfilePage() {
  return (
    <div className="max-w-xl space-y-6">
      <h1 className="text-2xl font-semibold">Profile and settings</h1>
      <Card title="Profile">
        <ProfileForm />
      </Card>
      <Card title="Change password">
        <PasswordForm />
      </Card>
      <Card title="Delete account">
        <DeleteAccount />
      </Card>
    </div>
  )
}

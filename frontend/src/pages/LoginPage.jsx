import { useState } from 'react'
import { Link } from 'react-router'
import { getErrorMessage } from '../api/client'
import AuthCard from '../components/auth/AuthCard'
import Alert from '../components/ui/Alert'
import Button from '../components/ui/Button'
import TextField from '../components/ui/TextField'
import useAuth from '../hooks/useAuth'

export default function LoginPage() {
  const { login } = useAuth()
  const [form, setForm] = useState({ email: '', password: '' })
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const update = (field) => (event) => setForm({ ...form, [field]: event.target.value })

  async function handleSubmit(event) {
    event.preventDefault()
    setError('')
    setSubmitting(true)
    try {
      await login(form.email, form.password)
      // GuestRoute redirects to the dashboard (or the page the user originally wanted).
    } catch (err) {
      setError(getErrorMessage(err))
      setSubmitting(false)
    }
  }

  return (
    <AuthCard
      title="Welcome back"
      subtitle="Log in to your research workspace."
      footer={
        <>
          New to DocuMind?{' '}
          <Link to="/register" className="font-medium text-indigo-600 dark:text-indigo-400 hover:underline">
            Create an account
          </Link>
        </>
      }
    >
      <form onSubmit={handleSubmit} className="space-y-4" noValidate>
        {error && <Alert>{error}</Alert>}
        <TextField label="Email" type="email" autoComplete="email" required value={form.email} onChange={update('email')} />
        <TextField
          label="Password"
          type="password"
          autoComplete="current-password"
          required
          value={form.password}
          onChange={update('password')}
        />
        <Button type="submit" loading={submitting} className="w-full">
          Log in
        </Button>
      </form>
    </AuthCard>
  )
}

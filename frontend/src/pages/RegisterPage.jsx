import { useState } from 'react'
import { Link } from 'react-router'
import { getErrorMessage } from '../api/client'
import AuthCard from '../components/auth/AuthCard'
import Alert from '../components/ui/Alert'
import Button from '../components/ui/Button'
import TextField from '../components/ui/TextField'
import useAuth from '../hooks/useAuth'
import { passwordProblem } from '../utils/validation'

export default function RegisterPage() {
  const { register } = useAuth()
  const [form, setForm] = useState({ fullName: '', email: '', password: '', confirm: '' })
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const update = (field) => (event) => setForm({ ...form, [field]: event.target.value })

  async function handleSubmit(event) {
    event.preventDefault()
    const problem =
      (form.fullName.trim().length < 2 && 'Please enter your full name') ||
      passwordProblem(form.password) ||
      (form.password !== form.confirm && 'Passwords do not match')
    if (problem) {
      setError(problem)
      return
    }

    setError('')
    setSubmitting(true)
    try {
      await register({ fullName: form.fullName, email: form.email, password: form.password })
    } catch (err) {
      setError(getErrorMessage(err))
      setSubmitting(false)
    }
  }

  return (
    <AuthCard
      title="Create your account"
      subtitle="Upload documents and ask questions in English or Telugu."
      footer={
        <>
          Already have an account?{' '}
          <Link to="/login" className="font-medium text-indigo-600 dark:text-indigo-400 hover:underline">
            Log in
          </Link>
        </>
      }
    >
      <form onSubmit={handleSubmit} className="space-y-4" noValidate>
        {error && <Alert>{error}</Alert>}
        <TextField label="Full name" autoComplete="name" required value={form.fullName} onChange={update('fullName')} />
        <TextField label="Email" type="email" autoComplete="email" required value={form.email} onChange={update('email')} />
        <TextField
          label="Password"
          type="password"
          autoComplete="new-password"
          hint="At least 8 characters, including a letter and a number."
          required
          value={form.password}
          onChange={update('password')}
        />
        <TextField
          label="Confirm password"
          type="password"
          autoComplete="new-password"
          required
          value={form.confirm}
          onChange={update('confirm')}
        />
        <Button type="submit" loading={submitting} className="w-full">
          Create account
        </Button>
      </form>
    </AuthCard>
  )
}

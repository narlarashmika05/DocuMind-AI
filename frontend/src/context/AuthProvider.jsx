import { useCallback, useEffect, useMemo, useState } from 'react'
import * as authApi from '../api/auth'
import { refreshSession, setAccessToken, setSessionExpiredHandler } from '../api/client'
import { AuthContext } from './auth-context'

export default function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [status, setStatus] = useState('loading')

  // On page load the in-memory token is gone, but the refresh cookie may still be valid.
  useEffect(() => {
    let active = true
    setSessionExpiredHandler(() => {
      setUser(null)
      setStatus('anonymous')
    })
    refreshSession()
      .then((data) => {
        if (!active) return
        setUser(data.user)
        setStatus('authenticated')
      })
      .catch(() => active && setStatus('anonymous'))
    return () => {
      active = false
    }
  }, [])

  const login = useCallback(async (email, password) => {
    const data = await authApi.login(email, password)
    setAccessToken(data.access_token)
    setUser(data.user)
    setStatus('authenticated')
  }, [])

  const register = useCallback(
    async ({ fullName, email, password }) => {
      await authApi.register({ fullName, email, password })
      await login(email, password)
    },
    [login],
  )

  const logout = useCallback(async () => {
    try {
      await authApi.logout()
    } finally {
      setAccessToken(null)
      setUser(null)
      setStatus('anonymous')
    }
  }, [])

  const value = useMemo(
    () => ({ user, status, login, register, logout, setUser }),
    [user, status, login, register, logout],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

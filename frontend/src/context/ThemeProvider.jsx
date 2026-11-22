import { useCallback, useEffect, useMemo, useState } from 'react'
import { ThemeContext } from './theme-context'

const STORAGE_KEY = 'documind-theme'

function readStoredTheme() {
  try {
    return localStorage.getItem(STORAGE_KEY) // 'light' | 'dark' | null (= follow the system)
  } catch {
    return null // storage can be blocked (private mode); just follow the system setting
  }
}

export default function ThemeProvider({ children }) {
  const [preference, setPreference] = useState(readStoredTheme)
  const [systemDark, setSystemDark] = useState(() => window.matchMedia('(prefers-color-scheme: dark)').matches)

  useEffect(() => {
    const query = window.matchMedia('(prefers-color-scheme: dark)')
    const onChange = (event) => setSystemDark(event.matches)
    query.addEventListener('change', onChange)
    return () => query.removeEventListener('change', onChange)
  }, [])

  const theme = preference ?? (systemDark ? 'dark' : 'light')

  useEffect(() => {
    document.documentElement.classList.toggle('dark', theme === 'dark')
    document.documentElement.style.colorScheme = theme
  }, [theme])

  const toggle = useCallback(() => {
    const next = theme === 'dark' ? 'light' : 'dark'
    setPreference(next)
    try {
      localStorage.setItem(STORAGE_KEY, next)
    } catch {
      // not persisted; the choice still applies for this visit
    }
  }, [theme])

  const value = useMemo(() => ({ theme, toggle }), [theme, toggle])
  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
}

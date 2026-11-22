import { createContext } from 'react'

// { user, status: 'loading' | 'authenticated' | 'anonymous', login, register, logout, setUser }
export const AuthContext = createContext(null)

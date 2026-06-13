import { createContext, useContext, useState, useCallback, useEffect, type ReactNode } from 'react'
import { login as apiLogin, signup as apiSignup, setAuthToken, type AuthUser } from '../api'

interface AuthValue {
  user: AuthUser | null
  token: string | null
  login: (email: string, password: string) => Promise<void>
  signup: (email: string, password: string, name: string) => Promise<void>
  logout: () => void
}
const AuthContext = createContext<AuthValue | null>(null)
const KEY = 'buybot.auth'

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null)
  const [token, setToken] = useState<string | null>(null)

  // Restore on mount
  useEffect(() => {
    const raw = localStorage.getItem(KEY)
    if (raw) {
      try {
        const { token, user } = JSON.parse(raw)
        setToken(token); setUser(user); setAuthToken(token)
      } catch { /* ignore */ }
    }
  }, [])

  const persist = (t: string, u: AuthUser) => {
    setToken(t); setUser(u); setAuthToken(t)
    localStorage.setItem(KEY, JSON.stringify({ token: t, user: u }))
  }

  const login = useCallback(async (email: string, password: string) => {
    const res = await apiLogin(email, password); persist(res.token, res.user)
  }, [])
  const signup = useCallback(async (email: string, password: string, name: string) => {
    const res = await apiSignup(email, password, name); persist(res.token, res.user)
  }, [])
  const logout = useCallback(() => {
    setToken(null); setUser(null); setAuthToken(null); localStorage.removeItem(KEY)
  }, [])

  return <AuthContext.Provider value={{ user, token, login, signup, logout }}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}

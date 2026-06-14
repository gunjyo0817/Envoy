import { createContext, useContext, useState, useCallback, useEffect, type ReactNode } from 'react'
import { login as apiLogin, signup as apiSignup, setAuthToken, fetchMe, type AuthUser } from '../api'

interface AuthValue {
  user: AuthUser | null
  token: string | null
  login: (email: string, password: string) => Promise<void>
  signup: (email: string, password: string, name: string) => Promise<void>
  loginWithToken: (token: string) => Promise<void>
  logout: () => void
  refreshUser: () => Promise<void>
}
const AuthContext = createContext<AuthValue | null>(null)
const KEY = 'envoy.auth'

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null)
  const [token, setToken] = useState<string | null>(null)

  const persist = (t: string, u: AuthUser) => {
    setToken(t); setUser(u); setAuthToken(t)
    localStorage.setItem(KEY, JSON.stringify({ token: t, user: u }))
  }

  const loginWithToken = useCallback(async (tk: string) => {
    setAuthToken(tk)
    const u = await fetchMe()
    persist(tk, u)
  }, [])

  const refreshUser = useCallback(async () => {
    const u = await fetchMe()
    setUser(u)
    const raw = localStorage.getItem(KEY)
    if (raw) {
      try {
        const parsed = JSON.parse(raw)
        localStorage.setItem(KEY, JSON.stringify({ ...parsed, user: u }))
      } catch { /* ignore */ }
    }
  }, [])

  // On mount: first honor a ?token= from the Google redirect, else restore from storage.
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const urlToken = params.get('token')
    if (urlToken) {
      // strip token (and any auth_error) from the URL, then establish the session
      window.history.replaceState({}, '', window.location.pathname)
      loginWithToken(urlToken).catch(() => { /* ignore */ })
      return
    }
    const raw = localStorage.getItem(KEY)
    if (raw) {
      try {
        const { token, user } = JSON.parse(raw)
        setToken(token); setUser(user); setAuthToken(token)
      } catch { /* ignore */ }
    }
  }, [loginWithToken])

  const login = useCallback(async (email: string, password: string) => {
    const res = await apiLogin(email, password); persist(res.token, res.user)
  }, [])
  const signup = useCallback(async (email: string, password: string, name: string) => {
    const res = await apiSignup(email, password, name); persist(res.token, res.user)
  }, [])
  const logout = useCallback(() => {
    setToken(null); setUser(null); setAuthToken(null); localStorage.removeItem(KEY)
  }, [])

  return <AuthContext.Provider value={{ user, token, login, signup, loginWithToken, logout, refreshUser }}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}

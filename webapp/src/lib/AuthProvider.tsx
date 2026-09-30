import { useQueryClient } from "@tanstack/react-query"
import { createContext, useContext, useEffect, useState, type ReactNode } from "react"

import * as api from "@/lib/api"
import type { User } from "@/lib/api"

interface AuthContextValue {
  user: User | null
  isLoading: boolean
  login: (identifier: string, password: string, remember?: boolean) => Promise<void>
  register: (payload: Parameters<typeof api.register>[0]) => Promise<void>
  logout: () => void
  refreshUser: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const queryClient = useQueryClient()

  useEffect(() => {
    const token = localStorage.getItem("access_token")
    if (!token) {
      setIsLoading(false)
      return
    }
    api
      .getMe()
      .then(setUser)
      .catch(() => api.logout())
      .finally(() => setIsLoading(false))
  }, [])

  const login = async (identifier: string, password: string, remember = true) => {
    const loggedInUser = await api.login(identifier, password, remember)
    setUser(loggedInUser)
  }

  const register = async (payload: Parameters<typeof api.register>[0]) => {
    await api.register(payload)
    await login(payload.email ?? payload.mobile ?? "", payload.password)
  }

  const logout = () => {
    api.logout()
    setUser(null)
    queryClient.clear()
  }

  const refreshUser = async () => {
    setUser(await api.getMe())
  }

  return (
    <AuthContext.Provider value={{ user, isLoading, login, register, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider")
  return ctx
}

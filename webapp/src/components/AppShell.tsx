import type { ReactNode } from "react"
import { Navigate } from "react-router-dom"

import { MobileNavigation } from "@/components/MobileNavigation"
import { Navbar } from "@/components/Navbar"
import { LoadingState } from "@/components/LoadingState"
import { useAuth } from "@/lib/AuthProvider"

export function AppShell({ children }: { children: ReactNode }) {
  const { user, isLoading } = useAuth()

  if (isLoading) return <LoadingState />
  if (!user) return <Navigate to="/login" replace />

  return (
    <div className="min-h-screen bg-bone">
      <Navbar />
      <main className="mx-auto max-w-6xl px-4 pb-24 pt-6 sm:px-6 md:pb-10">{children}</main>
      <MobileNavigation />
    </div>
  )
}

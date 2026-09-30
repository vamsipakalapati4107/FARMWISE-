import { useState, type FormEvent } from "react"
import { Link, useNavigate, useSearchParams } from "react-router-dom"

import { AuthLayout } from "@/components/AuthLayout"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { ApiError, resetPassword } from "@/lib/api"

export function ResetPassword() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const [token, setToken] = useState(searchParams.get("token") ?? "")
  const [newPassword, setNewPassword] = useState("")
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      await resetPassword(token, newPassword)
      navigate("/login")
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Reset failed. The link may have expired.")
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <AuthLayout>
      <h1 className="mb-6 font-serif text-3xl font-light text-charcoal">Reset password</h1>

      <form onSubmit={onSubmit} className="space-y-4">
        <div className="space-y-1.5">
          <Label htmlFor="token">Reset token</Label>
          <Input id="token" value={token} onChange={(e) => setToken(e.target.value)} required />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="new-password">New password</Label>
          <Input
            id="new-password"
            type="password"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            minLength={8}
            required
          />
        </div>

        {error && (
          <p className="rounded-xl bg-status-critical-bg px-3 py-2 text-sm text-status-critical">{error}</p>
        )}

        <Button type="submit" className="w-full" disabled={submitting}>
          {submitting ? "..." : "Reset password"}
        </Button>
      </form>

      <p className="mt-4 text-center text-sm text-pewter">
        <Link to="/login" className="text-forest-ink hover:underline">
          Back to login
        </Link>
      </p>
    </AuthLayout>
  )
}

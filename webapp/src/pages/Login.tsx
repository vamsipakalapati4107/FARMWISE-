import { useState, type FormEvent } from "react"
import { useTranslation } from "react-i18next"
import { Link, Navigate, useNavigate } from "react-router-dom"

import { AuthLayout } from "@/components/AuthLayout"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { ApiError } from "@/lib/api"
import { useAuth } from "@/lib/AuthProvider"

export function Login() {
  const { t } = useTranslation()
  const { user, login } = useAuth()
  const navigate = useNavigate()
  const [identifier, setIdentifier] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [remember, setRemember] = useState(true)

  if (user) return <Navigate to="/dashboard" replace />

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      await login(identifier, password, remember)
      navigate("/dashboard")
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Login failed. Please try again.")
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <AuthLayout>
      <h1 className="mb-1 font-serif text-3xl font-light text-charcoal">FarmWise</h1>
      <p className="mb-6 text-sm text-pewter">Weather intelligence for your farm.</p>

      <form onSubmit={onSubmit} className="space-y-4">
        <div className="space-y-1.5">
          <Label htmlFor="identifier">{t("auth.email")} / {t("auth.mobile")}</Label>
          <Input
            id="identifier"
            value={identifier}
            onChange={(e) => setIdentifier(e.target.value)}
            placeholder="you@example.com"
            required
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="password">{t("auth.password")}</Label>
          <Input
            id="password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </div>

        <div className="flex items-center justify-between text-sm">
          <label className="flex items-center gap-2 text-graphite">
            <Checkbox checked={remember} onCheckedChange={(checked) => setRemember(checked === true)} />
            {t("auth.rememberMe")}
          </label>
          <Link to="/forgot-password" className="text-forest-ink hover:underline">
            {t("auth.forgotPassword")}
          </Link>
        </div>

        {error && (
          <p className="rounded-xl bg-status-critical-bg px-3 py-2 text-sm text-status-critical">{error}</p>
        )}

        <Button type="submit" className="w-full" disabled={submitting}>
          {submitting ? "..." : t("auth.login")}
        </Button>
      </form>

      <p className="mt-4 text-center text-sm text-pewter">
        New here?{" "}
        <Link to="/register" className="text-forest-ink hover:underline">
          {t("auth.register")}
        </Link>
      </p>
    </AuthLayout>
  )
}

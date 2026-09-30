import { useState, type FormEvent } from "react"
import { Link } from "react-router-dom"

import { AuthLayout } from "@/components/AuthLayout"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { forgotPassword } from "@/lib/api"

export function ForgotPassword() {
  const [identifier, setIdentifier] = useState("")
  const [sent, setSent] = useState(false)
  const [submitting, setSubmitting] = useState(false)

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setSubmitting(true)
    try {
      await forgotPassword(identifier)
      setSent(true)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <AuthLayout>
      <h1 className="mb-1 font-serif text-3xl font-light text-charcoal">Forgot password</h1>
      <p className="mb-6 text-sm text-pewter">
        We'll generate a reset link for your account. No email/SMS provider is configured for this
        demo, so ask whoever runs the server to check its console output for the link.
      </p>

      {sent ? (
        <p className="rounded-xl bg-status-safe-bg px-3 py-2 text-sm text-status-safe">
          If that account exists, a reset link has been generated.
        </p>
      ) : (
        <form onSubmit={onSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="identifier">Email or mobile number</Label>
            <Input id="identifier" value={identifier} onChange={(e) => setIdentifier(e.target.value)} required />
          </div>
          <Button type="submit" className="w-full" disabled={submitting}>
            {submitting ? "..." : "Send reset link"}
          </Button>
        </form>
      )}

      <p className="mt-4 text-center text-sm text-pewter">
        <Link to="/login" className="text-forest-ink hover:underline">
          Back to login
        </Link>
      </p>
    </AuthLayout>
  )
}

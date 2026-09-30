import { Sprout } from "lucide-react"
import type { ReactNode } from "react"

import { FieldPattern } from "@/components/FieldPattern"

/** Shared shell for Login/Register/ForgotPassword/ResetPassword: an
 * illustration panel on larger screens, clean single-column form on mobile
 * (spec section 3: "Use an agricultural visual on larger screens while
 * keeping the mobile experience clean"). */
export function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-screen bg-bone">
      <div className="relative hidden w-1/2 overflow-hidden lg:block">
        <FieldPattern className="absolute inset-0 h-full w-full" />
        <div className="relative z-10 flex h-full flex-col justify-between p-12 text-white">
          <div className="flex items-center gap-2 font-serif text-xl">
            <Sprout className="size-6 text-vivid-lime" /> FarmWise
          </div>
          <blockquote className="font-serif text-3xl font-light leading-snug">
            "Weather intelligence and actionable farm advisories, designed for every farmer."
          </blockquote>
          <p className="text-sm text-white/70">Sathupally block, Khammam district, Telangana</p>
        </div>
      </div>

      <div className="flex w-full items-center justify-center px-4 py-12 lg:w-1/2">
        <div className="w-full max-w-sm">{children}</div>
      </div>
    </div>
  )
}

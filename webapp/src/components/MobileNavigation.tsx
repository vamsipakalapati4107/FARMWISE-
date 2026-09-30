import { CloudSun, Home, Sprout, Stethoscope, User } from "lucide-react"
import { useTranslation } from "react-i18next"
import { NavLink } from "react-router-dom"

import { cn } from "@/lib/utils"

export function MobileNavigation() {
  const { t } = useTranslation()

  const items = [
    { to: "/dashboard", label: t("nav.home"), icon: Home },
    { to: "/forecast", label: t("nav.forecast"), icon: CloudSun },
    { to: "/advisory", label: t("nav.advisory"), icon: Stethoscope },
    { to: "/farm", label: t("nav.farm"), icon: Sprout },
    { to: "/profile", label: t("nav.profile"), icon: User },
  ]

  return (
    <nav
      className="fixed inset-x-0 bottom-0 z-20 flex items-center justify-around border-t border-moss bg-card px-2 py-2 md:hidden"
      aria-label="Primary"
      style={{ paddingBottom: "max(0.5rem, env(safe-area-inset-bottom))" }}
    >
      {items.map(({ to, label, icon: Icon }) => (
        <NavLink
          key={to}
          to={to}
          className={({ isActive }) =>
            cn(
              "flex min-w-16 flex-col items-center gap-0.5 rounded-nav-pill px-3 py-1.5 text-xs",
              isActive ? "text-forest-ink" : "text-pewter"
            )
          }
        >
          {({ isActive }) => (
            <>
              <Icon className="size-5" fill={isActive ? "var(--color-sage-card)" : "none"} aria-hidden="true" />
              {label}
            </>
          )}
        </NavLink>
      ))}
    </nav>
  )
}

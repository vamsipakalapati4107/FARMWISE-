import { useQuery, useQueryClient } from "@tanstack/react-query"
import { Bell, Search, Sprout } from "lucide-react"
import { useTranslation } from "react-i18next"
import { Link } from "react-router-dom"

import { LanguageSelector } from "@/components/LanguageSelector"
import { NotificationPanel } from "@/components/NotificationPanel"
import { ProfileMenu } from "@/components/ProfileMenu"
import { Button, buttonVariants } from "@/components/ui/button"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { getNotifications, markNotificationRead } from "@/lib/api"
import { cn } from "@/lib/utils"

export function Navbar() {
  const { t } = useTranslation()
  const queryClient = useQueryClient()

  const { data: notifications = [] } = useQuery({
    queryKey: ["notifications"],
    queryFn: getNotifications,
    refetchInterval: 60_000,
  })
  const unreadCount = notifications.filter((n) => !n.read).length

  const onMarkRead = async (id: string) => {
    await markNotificationRead(id)
    queryClient.invalidateQueries({ queryKey: ["notifications"] })
  }

  return (
    <header className="sticky top-0 z-20 bg-forest-ink px-4 py-3 text-white sm:px-6">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-4">
        <Link to="/" className="flex items-center gap-2 font-serif text-lg font-medium">
          <Sprout className="size-5 text-vivid-lime" aria-hidden="true" />
          FarmWise
        </Link>

        <nav className="hidden items-center gap-1 md:flex" aria-label="Primary">
          {[
            { to: "/dashboard", label: t("nav.home") },
            { to: "/forecast", label: t("nav.forecast") },
            { to: "/advisory", label: t("nav.advisory") },
            { to: "/farm", label: t("nav.farm") },
          ].map((item) => (
            <Link
              key={item.to}
              to={item.to}
              className="rounded-nav-pill px-4 py-2 text-sm text-white/90 transition-colors hover:bg-white/10"
            >
              {item.label}
            </Link>
          ))}
        </nav>

        <div className="flex items-center gap-2">
          <Link
            to="/search"
            aria-label="Search"
            className={cn(buttonVariants({ variant: "ghost", size: "icon" }), "text-white hover:bg-white/10")}
          >
            <Search className="size-5" />
          </Link>
          <LanguageSelector variant="on-dark" />
          <Popover>
            <PopoverTrigger
              render={
                <Button
                  variant="ghost"
                  size="icon"
                  className="relative text-white hover:bg-white/10"
                  aria-label={`Notifications${unreadCount > 0 ? ` (${unreadCount} unread)` : ""}`}
                >
                  <Bell className="size-5" />
                  {unreadCount > 0 && (
                    <span className="absolute right-1.5 top-1.5 flex size-2 rounded-full bg-vivid-lime" />
                  )}
                </Button>
              }
            />
            <PopoverContent align="end" className="w-80 rounded-card p-0 shadow-none ring-1 ring-moss">
              <NotificationPanel notifications={notifications} onMarkRead={onMarkRead} />
            </PopoverContent>
          </Popover>
          <ProfileMenu />
        </div>
      </div>
    </header>
  )
}

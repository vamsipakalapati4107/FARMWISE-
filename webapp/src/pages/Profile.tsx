import { LanguageSelector } from "@/components/LanguageSelector"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Button } from "@/components/ui/button"
import { useAuth } from "@/lib/AuthProvider"

export function Profile() {
  const { user, logout } = useAuth()
  if (!user) return null

  const initials = user.name
    .split(" ")
    .map((part) => part[0])
    .slice(0, 2)
    .join("")
    .toUpperCase()

  return (
    <div className="space-y-6">
      <h1 className="font-serif text-2xl font-medium text-charcoal">Profile</h1>

      <div className="flex items-center gap-4 rounded-card bg-card p-6">
        <Avatar className="size-14">
          <AvatarFallback className="bg-sage-card text-lg text-forest-ink">{initials}</AvatarFallback>
        </Avatar>
        <div>
          <p className="font-serif text-xl text-charcoal">{user.name}</p>
          <p className="text-sm text-pewter">{user.email ?? user.mobile}</p>
        </div>
      </div>

      <div className="rounded-card bg-card p-6">
        <h2 className="mb-3 text-sm font-medium text-graphite">Language</h2>
        <LanguageSelector />
      </div>

      <Button variant="outline" onClick={logout}>
        Log out
      </Button>
    </div>
  )
}

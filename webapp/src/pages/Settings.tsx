import { useState } from "react"
import { Link } from "react-router-dom"

import { LanguageSelector } from "@/components/LanguageSelector"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { updateProfile, type SmsCategory } from "@/lib/api"
import { useAuth } from "@/lib/AuthProvider"

function readNotificationPref(): boolean {
  try {
    const raw = localStorage.getItem("notification_prefs")
    return raw ? JSON.parse(raw).enabled !== false : true
  } catch {
    return true
  }
}

const SMS_CATEGORY_LABELS: { value: SmsCategory; label: string }[] = [
  { value: "severe_weather", label: "Severe Weather" },
  { value: "disease_risk", label: "Disease Risk" },
  { value: "crop_stress", label: "Crop Stress" },
  { value: "farm_actions", label: "Important Farm Actions" },
]
const ALL_SMS_CATEGORIES: SmsCategory[] = SMS_CATEGORY_LABELS.map((c) => c.value)

export function Settings() {
  const { user, logout, refreshUser } = useAuth()
  const [units, setUnits] = useState(() => localStorage.getItem("units") ?? "metric")
  const [notifications, setNotifications] = useState(readNotificationPref)
  const [savingSms, setSavingSms] = useState(false)

  const updateUnits = (value: string) => {
    setUnits(value)
    localStorage.setItem("units", value)
  }

  const updateNotifications = (checked: boolean) => {
    setNotifications(checked)
    localStorage.setItem("notification_prefs", JSON.stringify({ enabled: checked }))
  }

  const smsEnabled = user?.sms_notifications_enabled ?? true
  const smsCategories = user?.sms_alert_categories ?? ALL_SMS_CATEGORIES

  const toggleSmsEnabled = async (checked: boolean) => {
    setSavingSms(true)
    try {
      await updateProfile({ sms_notifications_enabled: checked })
      await refreshUser()
    } finally {
      setSavingSms(false)
    }
  }

  const toggleSmsCategory = async (category: SmsCategory, checked: boolean) => {
    const next = checked ? [...smsCategories, category] : smsCategories.filter((c) => c !== category)
    setSavingSms(true)
    try {
      await updateProfile({ sms_alert_categories: next })
      await refreshUser()
    } finally {
      setSavingSms(false)
    }
  }

  return (
    <div className="space-y-6">
      <h1 className="font-serif text-2xl font-medium text-charcoal">Settings</h1>

      <div className="space-y-5 rounded-card bg-card p-6">
        <div className="space-y-1.5">
          <p className="text-sm font-medium text-graphite">Language</p>
          <LanguageSelector />
        </div>

        <div className="space-y-1.5">
          <p className="text-sm font-medium text-graphite">Units</p>
          <Select value={units} onValueChange={(v) => v && updateUnits(v)}>
            <SelectTrigger className="w-full sm:w-64">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="metric">Metric (°C, mm, km/h)</SelectItem>
              <SelectItem value="imperial">Imperial (°F, in, mph)</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <label className="flex items-center gap-2 text-sm text-graphite">
          <Checkbox checked={notifications} onCheckedChange={(c) => updateNotifications(c === true)} />
          Send me weather alerts and advisory notifications
        </label>
      </div>

      <div className="space-y-4 rounded-card bg-card p-6">
        <div>
          <p className="text-sm font-medium text-graphite">Notifications</p>
          <label className="mt-2 flex items-center gap-2 text-sm text-charcoal">
            <Checkbox
              checked={smsEnabled}
              disabled={savingSms}
              onCheckedChange={(c) => toggleSmsEnabled(c === true)}
            />
            📱 SMS Alerts
          </label>
          <p className="mt-1 text-xs text-pewter">
            {user?.mobile
              ? "Receive important FarmWise alerts by SMS."
              : "Add a mobile number to your account to receive SMS alerts (none on file yet)."}
          </p>
          <p className="mt-1 text-xs italic text-pewter">
            No SMS provider is connected for this deployment yet -- messages are simulated, not actually delivered.
          </p>
        </div>

        {smsEnabled && (
          <div>
            <p className="text-sm font-medium text-graphite">SMS Alert Types</p>
            <div className="mt-2 space-y-2">
              {SMS_CATEGORY_LABELS.map((c) => (
                <label key={c.value} className="flex items-center gap-2 text-sm text-charcoal">
                  <Checkbox
                    checked={smsCategories.includes(c.value)}
                    disabled={savingSms}
                    onCheckedChange={(checked) => toggleSmsCategory(c.value, checked === true)}
                  />
                  {c.label}
                </label>
              ))}
            </div>
          </div>
        )}
      </div>

      <div className="space-y-5 rounded-card bg-card p-6">
        <div className="space-y-1.5">
          <p className="text-sm font-medium text-graphite">Location</p>
          <p className="text-sm text-pewter">
            Manage your farms and their Gram Panchayat in{" "}
            <Link to="/farm" className="text-forest-ink hover:underline">
              My Farm
            </Link>
            .
          </p>
        </div>
      </div>

      <div className="rounded-card bg-card p-6">
        <p className="mb-3 text-sm font-medium text-graphite">Account</p>
        <Button variant="outline" onClick={logout}>
          Log out
        </Button>
      </div>
    </div>
  )
}

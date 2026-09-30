import { Languages } from "lucide-react"
import { useTranslation } from "react-i18next"

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

const LANGUAGES = [
  { code: "en", label: "English" },
  { code: "te", label: "తెలుగు" },
  { code: "hi", label: "हिन्दी" },
]

export function LanguageSelector({ variant = "default" }: { variant?: "default" | "on-dark" }) {
  const { i18n } = useTranslation()

  const setLanguage = (code: string | null) => {
    if (!code) return
    void i18n.changeLanguage(code)
    localStorage.setItem("language", code)
  }

  return (
    <Select value={i18n.language} onValueChange={setLanguage}>
      <SelectTrigger
        className={variant === "on-dark" ? "border-white/30 bg-transparent text-white" : "w-auto"}
        size="sm"
      >
        <Languages className="size-4" aria-hidden="true" />
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        {LANGUAGES.map((lang) => (
          <SelectItem key={lang.code} value={lang.code}>
            {lang.label}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}

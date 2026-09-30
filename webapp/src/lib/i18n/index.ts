import i18n from "i18next"
import { initReactI18next } from "react-i18next"

import en from "./locales/en.json"
import hi from "./locales/hi.json"
import te from "./locales/te.json"

// te/hi are partially translated -- missing keys fall back to English
// (fallbackLng below), so localization can grow incrementally without
// blocking on a full translation pass.
void i18n.use(initReactI18next).init({
  resources: {
    en: { translation: en },
    te: { translation: te },
    hi: { translation: hi },
  },
  lng: localStorage.getItem("language") ?? "en",
  fallbackLng: "en",
  interpolation: { escapeValue: false },
})

export default i18n

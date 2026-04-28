import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import LanguageDetector from "i18next-browser-languagedetector";
import en from "./en.json";
import zhCN from "./zh-CN.json";
import msMY from "./ms-MY.json";
import taSG from "./ta-SG.json";

/**
 * Supported locale codes for the Arbor / Central UI.
 *
 * - en:    English (default)
 * - zh-CN: Mandarin (Simplified)
 * - ms-MY: Bahasa Melayu (used for the Singapore Malay community)
 * - ta-SG: Tamil (Singapore standard)
 */
export const SUPPORTED_LOCALES = ["en", "zh-CN", "ms-MY", "ta-SG"] as const;
export type SupportedLocale = (typeof SUPPORTED_LOCALES)[number];

export const DEFAULT_LOCALE: SupportedLocale = "en";

const STORAGE_KEY = "arbor-locale";

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: {
      en: { translation: en },
      "zh-CN": { translation: zhCN },
      "ms-MY": { translation: msMY },
      "ta-SG": { translation: taSG },
    },
    fallbackLng: DEFAULT_LOCALE,
    supportedLngs: [...SUPPORTED_LOCALES],
    interpolation: {
      escapeValue: false,
    },
    detection: {
      // Read from localStorage first, then fall back to browser language
      order: ["localStorage", "navigator"],
      lookupLocalStorage: STORAGE_KEY,
      caches: ["localStorage"],
    },
  });

/**
 * Persist locale choice to localStorage and update the active language.
 * Components should call this from a settings UI or a language switcher.
 */
export function setLocale(locale: SupportedLocale): void {
  if (typeof window !== "undefined") {
    window.localStorage.setItem(STORAGE_KEY, locale);
    // Update <html lang> for accessibility / typography hints
    document.documentElement.lang = locale;
  }
  void i18n.changeLanguage(locale);
}

/**
 * Read the currently-active locale, normalised to a supported code.
 */
export function getLocale(): SupportedLocale {
  const raw = i18n.resolvedLanguage ?? i18n.language ?? DEFAULT_LOCALE;
  return (SUPPORTED_LOCALES as readonly string[]).includes(raw)
    ? (raw as SupportedLocale)
    : DEFAULT_LOCALE;
}

export const LOCALE_STORAGE_KEY = STORAGE_KEY;

export default i18n;

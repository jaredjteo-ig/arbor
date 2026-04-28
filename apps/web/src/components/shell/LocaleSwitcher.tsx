"use client";

import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Globe, Check } from "lucide-react";
import {
  SUPPORTED_LOCALES,
  getLocale,
  setLocale,
  type SupportedLocale,
} from "@/lib/i18n";

/**
 * LocaleSwitcher
 *
 * Renders a list of supported locales as selectable cards. Persists the
 * choice to localStorage via `setLocale()` (read by i18next's
 * LanguageDetector on the next mount) and immediately switches the
 * active i18next language so the rest of the UI re-renders in place.
 *
 * For B17 (minimum-viable i18n) we keep this entirely client-side — no
 * backend round-trip is required to flip languages.
 */
export function LocaleSwitcher() {
  const { t } = useTranslation();
  // Track the selected locale in component state so the active card
  // re-renders when the user clicks another option. We hydrate from
  // i18next on mount to avoid a server/client mismatch.
  const [selected, setSelected] = useState<SupportedLocale>("en");
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    setSelected(getLocale());
    setHydrated(true);
  }, []);

  function handleSelect(next: SupportedLocale) {
    setSelected(next);
    setLocale(next);
  }

  return (
    <div className="space-y-3">
      <p className="text-sm text-[var(--color-gray-600)]">
        {t("settings.language_switcher_description")}
      </p>

      <ul className="grid grid-cols-1 sm:grid-cols-2 gap-3" role="radiogroup">
        {SUPPORTED_LOCALES.map((code) => {
          const isActive = hydrated && code === selected;
          return (
            <li key={code}>
              <button
                type="button"
                role="radio"
                aria-checked={isActive}
                onClick={() => handleSelect(code)}
                className={`
                  w-full text-left flex items-center gap-3 p-3 rounded-lg cursor-pointer transition-colors border
                  ${
                    isActive
                      ? "border-[var(--color-primary)] bg-[var(--color-primary-bg)]"
                      : "border-[var(--color-gray-200)] hover:bg-[var(--color-gray-50)]"
                  }
                  focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-primary)]
                `}
              >
                <div
                  className="flex items-center justify-center h-8 w-8 rounded-full
                    bg-[var(--color-primary)] text-white text-[11px] font-bold uppercase shrink-0"
                  aria-hidden="true"
                >
                  {code === "en"
                    ? "EN"
                    : code === "zh-CN"
                      ? "中"
                      : code === "ms-MY"
                        ? "MS"
                        : "த"}
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium text-[var(--color-gray-900)] truncate">
                    {t(`language.${code}`)}
                  </p>
                  <p className="text-xs text-[var(--color-gray-500)] truncate">
                    {isActive
                      ? t("settings.language_currently_selected")
                      : t(`language.${code}_native`)}
                  </p>
                </div>
                {isActive && (
                  <Check
                    className="h-4 w-4 text-[var(--color-primary)] shrink-0"
                    aria-hidden="true"
                  />
                )}
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

/**
 * Convenience header element so the Settings page can render the
 * standard `<Globe /> Language` row without having to import the icon
 * itself.
 */
export function LocaleSwitcherHeader() {
  const { t } = useTranslation();
  return (
    <div className="flex items-center gap-2">
      <Globe
        className="h-4 w-4 text-[var(--color-gray-500)]"
        aria-hidden="true"
      />
      <h2 className="text-base font-semibold text-[var(--color-gray-900)]">
        {t("settings.language")}
      </h2>
    </div>
  );
}

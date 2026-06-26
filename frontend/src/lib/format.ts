/**
 * Locale-aware formatters.
 * Call with the current i18n language ("fr" | "ar").
 */

const LOCALE_MAP: Record<string, string> = {
  fr: "fr-MA",
  ar: "ar-MA",
}

function locale(lang: string): string {
  return LOCALE_MAP[lang] ?? "fr-MA"
}

export function fmtNumber(
  value: number | null | undefined,
  lang: string,
  decimals = 0,
): string {
  if (value == null) return "—"
  return value.toLocaleString(locale(lang), {
    maximumFractionDigits: decimals,
    minimumFractionDigits: decimals,
  })
}

export function fmtDate(
  isoString: string | null | undefined,
  lang: string,
): string {
  if (!isoString) return "—"
  return new Date(isoString).toLocaleDateString(locale(lang), {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  })
}

export function fmtDateTime(
  isoString: string | null | undefined,
  lang: string,
): string {
  if (!isoString) return "—"
  return new Date(isoString).toLocaleString(locale(lang), {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  })
}

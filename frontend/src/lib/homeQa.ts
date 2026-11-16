import { ADVERTISED_LOCALES } from "./advertised-locales";
import { localeName } from "./lang.svelte";

/**
 * The home page's "Questions about Ochorus": what an answer engine is asked
 * about the site ("What is Ochorus?", "Is it free?", "What languages?"),
 * answered on the page itself and mirrored into FAQPage JSON-LD. The first
 * answer is the site's one-sentence definition — the line AI answers quote.
 *
 * The languages answer is built from the advertised locales, so it can never
 * name a language the site does not serve.
 */
export const HOME_QA_KEYS = ["what", "free", "lang", "pd", "start"] as const;

/** "English, Español and Kiswahili", in the reader's own language's list style. */
export function languageList(
  uiLocale: string,
  codes: readonly string[] = ADVERTISED_LOCALES,
): string {
  const names = codes.map(localeName);
  try {
    return new Intl.ListFormat(uiLocale, {
      style: "long",
      type: "conjunction",
    }).format(names);
  } catch {
    return names.join(", ");
  }
}

export function homeQa(
  t: (key: string) => string,
  uiLocale: string,
): { q: string; a: string }[] {
  return HOME_QA_KEYS.map((k) => ({
    q: t(`home.qa.${k}Q`),
    a: t(`home.qa.${k}A`).replace("%languages%", languageList(uiLocale)),
  }));
}

/**
 * The UI locales whose chrome (footer, palette, More sheet) links the hub.
 *
 * The page itself needs no list — it 404s where the series has no book
 * (no English fallback), and its hreflang and sitemap row are derived from the
 * API's own per-language presence. But the chrome is drawn without a request,
 * and a footer link in a locale with no Bible would send the prerender crawl to
 * that 404 and fail the build. Add a locale here when its Bible books ship AND
 * the hub's own copy (/bible, /bible/story, /open-word-bible) is in it: every
 * `BibleText` then fails to type-check until it has that language's words.
 * Spanish joined on 2026-11-23, the day after its books.
 */
export const BIBLE_LOCALES = ['en', 'es'] as const;

/** A locale the hub is drawn in. */
export type BibleLocale = (typeof BIBLE_LOCALES)[number];

/** Whether the chrome links the hub for a reader in `locale`. */
export const bibleIn = (locale: string): locale is BibleLocale =>
	(BIBLE_LOCALES as readonly string[]).includes(locale);

/**
 * The hub's own prose — the "Where to start" reasons, the story's eras, the
 * translation's page — in every hub locale. Kept beside the code that draws it
 * rather than in the 14-locale catalogue: only these pages use it, and they
 * exist only in BIBLE_LOCALES, so the type is the completeness check.
 */
export type BibleText = Readonly<Record<BibleLocale, string>>;

/**
 * `text` in `locale`. Only a hub locale is ever asked (the pages 404
 * elsewhere); any other gets the English, for the pure helpers' callers
 * outside the hub (a book page's chapter names), never a hub page.
 */
export const bibleText = (text: BibleText, locale: string): string =>
	bibleIn(locale) ? text[locale] : text.en;

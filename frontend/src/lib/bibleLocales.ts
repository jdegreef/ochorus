/**
 * The UI locales whose chrome (footer, palette, More sheet) links the hub.
 *
 * The page itself needs no list — it 404s where the series has no book
 * (no English fallback), and its hreflang and sitemap row are derived from the
 * API's own per-language presence. But the chrome is drawn without a request,
 * and a footer link in a locale with no Bible would send the prerender crawl to
 * that 404 and fail the build. Add a locale here when its Bible books ship AND
 * the hub's own copy (/bible, /bible/story, /open-word-bible) is in it:
 * Spanish has the books (2026-11-22) but not yet the hub.
 */
export const BIBLE_LOCALES: readonly string[] = ['en'];

/** Whether the chrome links the hub for a reader in `locale`. */
export const bibleIn = (locale: string) => BIBLE_LOCALES.includes(locale);

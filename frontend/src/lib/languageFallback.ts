import { SITE_URL } from './config';
import { localizeHref } from './href';
import { isLocale } from './paraglide/runtime';
import { baseEdition } from './reading-schema';
import { hreflangFor, type Hreflang } from './seo';

/**
 * A page showing another language's edition than its URL names: the loaders
 * retry a 404 in English, so /hi/books/x/ can render the English book.
 * `requested` is the URL's locale, `shown` the language the payload is in; the
 * Modern English edition counts as English.
 */
export interface LanguageFallback {
	requested: string;
	shown: string;
}

export function languageFallback(requested: string, shown: string): LanguageFallback | null {
	const want = baseEdition(requested);
	const got = baseEdition(shown);
	return want === got ? null : { requested: want, shown: got };
}

/**
 * The head for a per-language work (book, chapter, sermon, plan, article):
 * hreflang over the editions that exist, and a canonical that is the page
 * itself — or, when it is showing another edition, that edition's URL, so the
 * localized address is consolidated into the real one instead of indexed as
 * a copy of it.
 */
export function editionSeo(
	path: string,
	available: string[],
	fallback: LanguageFallback | null
): { hreflang: Hreflang; canonical: string } {
	return {
		hreflang: hreflangFor(path, available),
		canonical: `${SITE_URL}${localizeHref(path, fallback && isLocale(fallback.shown) ? { locale: fallback.shown } : undefined)}`
	};
}

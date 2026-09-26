import { baseEdition } from './reading-schema';

/**
 * When a page is showing another language's edition than the one its URL asks
 * for.
 *
 * Books, sermons and plans are per-language rows with no English fallback in
 * the API, but the client's `localized()` retries a 404 in English so a missing
 * edition still renders something readable. That is the right call for the
 * text and the wrong one for everything that describes it: /hi/books/x/ used
 * to show English prose under Hindi chrome with no word about it, a canonical
 * claiming it was the Hindi page, and nothing stopping it being indexed as one.
 *
 * `requested` is the URL's locale; `shown` is the language the payload is
 * actually in. The Modern English edition counts as English — reading it under
 * /en is not a fallback.
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

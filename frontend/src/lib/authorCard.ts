// Read by the build script under plain Node, so this module stays import-free
// at runtime: the one import below is a type, and Node strips it.
import type { AuthorDetail } from './library-public';

/**
 * Where an author page's share card lives, per interface language.
 *
 * Not committed: `scripts/build-author-cards.mjs` draws one into the build for
 * every prerendered author page, from the data that page was rendered with.
 * One per language because a card with words on it serves one language — the
 * counts, the "Read …" line and the footer are all the page's own. Said once
 * so the page that names a card and the script that draws it cannot disagree.
 */
export function authorCardUrl(slug: string, language: string): string {
	return `/og/authors/${language}/${slug}.jpg`;
}

const FETCHED =
	/<script type="application\/json" data-sveltekit-fetched data-url="[^"]*\/api\/library\/authors\/[^"/?]+\/\?language=([^"&]+)"[^>]*>([\s\S]*?)<\/script>/g;

/**
 * The author API response a prerendered author page was rendered from, and
 * the language that answered — SvelteKit inlines a load's `fetch` into the
 * page. Every inlined response is tried, because a language with no row 404s
 * first and the page then falls back to English: the 404 is inlined too.
 * Null when the page holds no author.
 */
export function authorData(html: string): { author: AuthorDetail; language: string } | null {
	for (const [, language, raw] of html.matchAll(FETCHED)) {
		try {
			const response = JSON.parse(raw);
			const author = JSON.parse(response.body);
			if ((response.status ?? 200) < 400 && author?.slug && author?.name) {
				return { author, language };
			}
		} catch {
			/* not this one */
		}
	}
	return null;
}

/**
 * The line an English card quotes: the first of the author's curated quotes
 * that reads at a glance — so the order of the quote page is how an editor
 * chooses it. Null when none is short enough to set whole.
 */
export function cardQuote(quotes: { text: string }[]): string | null {
	return quotes.map((q) => q.text.trim()).find((t) => t.length >= 30 && t.length <= 150) ?? null;
}

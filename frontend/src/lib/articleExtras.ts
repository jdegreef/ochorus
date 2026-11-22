import { apiFetch } from '$lib/api';
import { getQuotePage, quoteHref, type Article, type Quote } from '$lib/library-public';
import type { ScriptureResult } from '$lib/scripture.svelte';

/**
 * Two things an article page sets beside its prose, fetched with the article
 * so they are in the prerendered page (no jump when they arrive):
 *
 *   * the KEY VERSE — the article's first cited passage, in the Open Word
 *     Bible, set as a block under the title. English only: the scripture
 *     lookup serves the English OWB, and a translated article quotes its own.
 *   * a line FROM THE CLASSIC it leads to — one of the lead book's approved
 *     quotations (English only, like the quote pages), for the "book behind
 *     this article" card. Most writers have no quote page yet; then none.
 *
 * Both are decoration: any failure is null, never a failed page.
 */
export interface KeyVerse {
	ref: string;
	text: string;
	version: string;
}
export interface BookQuote {
	text: string;
	href: string;
}

/** Long enough to say something, short enough to sit in a side card. */
const QUOTE_MIN = 60;
const QUOTE_MAX = 240;

export function pickBookQuote(quotes: Quote[], work: string): BookQuote | null {
	const q = quotes.find(
		(x) =>
			x.source.kind === 'chapter' &&
			x.source.work === work &&
			x.text.length >= QUOTE_MIN &&
			x.text.length <= QUOTE_MAX
	);
	return q ? { text: q.text, href: quoteHref(q) } : null;
}

export async function articleExtras(
	article: Article,
	fetch: typeof globalThis.fetch
): Promise<{ keyVerse: KeyVerse | null; bookQuote: BookQuote | null }> {
	if (article.language !== 'en') return { keyVerse: null, bookQuote: null };
	const ref = article.scripture_refs?.[0];
	const lead = article.lead_book;
	const [verse, quotes] = await Promise.all([
		ref
			? apiFetch<ScriptureResult>(`/api/library/scripture/?ref=${encodeURIComponent(ref)}`, {}, fetch).catch(
					() => null
				)
			: null,
		lead ? getQuotePage(lead.author.slug, fetch).then((p) => p.quotes).catch(() => null) : null
	]);
	const text = verse?.verses.map((v) => v.text).join(' ').trim();
	return {
		keyVerse: verse && text ? { ref: verse.reference, text, version: verse.version } : null,
		bookQuote: lead && quotes ? pickBookQuote(quotes, lead.title) : null
	};
}

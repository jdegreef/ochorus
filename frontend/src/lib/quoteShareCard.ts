// Read by the build script under plain Node, so this module stays import-free:
// the quote picker is passed in (it is `authorCard.cardQuote`), because a
// sibling import would need a `.ts` extension Node wants and TypeScript refuses.

/**
 * Where a quote page's share card lives. Three pages carry one:
 *
 *   /quotes/<author>/          → /og/quotes/<author>.jpg
 *   /quotes/<author>/<topic>/  → /og/quotes/<author>/<topic>.jpg
 *   /quotes/topics/<topic>/    → /og/quotes/topics/<topic>.jpg
 *
 * Not committed: `scripts/build-quote-cards.mjs` draws each into the build
 * from the data its page was rendered with. Said once so the page that names a
 * card and the script that draws it cannot disagree about the path. (No author
 * is slugged `topics`, and the index pages keep the fixed `/og/quotes.png`.)
 */
export function quoteCardUrl(page: { author?: string; topic?: string }): string {
	if (page.author && page.topic) return `/og/quotes/${page.author}/${page.topic}.jpg`;
	if (page.author) return `/og/quotes/${page.author}.jpg`;
	return `/og/quotes/topics/${page.topic}.jpg`;
}

interface TopicVoice {
	author: { slug: string; name: string; photo_url?: string | null };
	count: number;
	quotes: { text: string }[];
}

/**
 * The quote a topic card features: from the writer who says the most on the
 * topic, their first line short enough to set whole — so, as everywhere, the
 * order of the quotes is how an editor chooses it. Falls to the next writer
 * when one has nothing short enough; null when no one does.
 */
export function featuredQuote(
	voices: TopicVoice[],
	pick: (quotes: { text: string }[]) => string | null
): { author: TopicVoice['author']; text: string } | null {
	for (const v of [...voices].sort((a, b) => b.count - a.count)) {
		const text = pick(v.quotes);
		if (text) return { author: v.author, text };
	}
	return null;
}

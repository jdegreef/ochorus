/**
 * Work out which library work a page is showing, from its path, so a piece of
 * feedback filed while reading carries "which book, which chapter" without the
 * reader having to say. Pure and unit-tested; the language is read separately
 * (from `getLang()`), never parsed out of the path — a localized URL may or may
 * not carry a locale prefix, but the app always knows the active language.
 */

/** The route segment → the content kind the backend stores. */
const KINDS: Record<string, string> = {
	books: 'book',
	sermons: 'sermon',
	plans: 'plan',
	articles: 'article',
	authors: 'author',
	topics: 'topic'
};

export interface FeedbackContext {
	content_kind?: string;
	content_slug?: string;
	chapter_ref?: string;
}

/**
 * Parse `/…/books/<slug>/<order>` (and the sermon/plan/article/author/topic
 * variants) into feedback context. Returns `{}` for any page that isn't a work
 * — the feedback is still valid, just without a work attached.
 */
export function feedbackContext(pathname: string): FeedbackContext {
	const segments = pathname.split('/').filter(Boolean);
	for (let i = 0; i < segments.length; i++) {
		const kind = KINDS[segments[i]];
		const slug = segments[i + 1];
		if (!kind || !slug) continue;
		const ctx: FeedbackContext = { content_kind: kind, content_slug: slug };
		// A book chapter is /books/<slug>/<order>; only a numeric next segment is
		// a chapter (never another route word).
		const next = segments[i + 2];
		if (kind === 'book' && next && /^\d+$/.test(next)) ctx.chapter_ref = next;
		return ctx;
	}
	return {};
}

import type { Quote, QuoteTopicPage } from '$lib/library-public';

/**
 * The /quotes "wall of lines": a few themes, each shown as its shortest
 * lines rather than a count — one line per writer, so a theme reads as a
 * conversation across the centuries, not five lines of Spurgeon.
 */
export interface WallLine {
	quote: Quote;
	author: string;
}
export interface WallTopic {
	slug: string;
	title: string;
	lines: WallLine[];
}

/** A line short enough to read at a glance on the wall. */
const WALL_MAX = 140;

/** `seen` holds the quotes already on the wall (filled as it goes), so a line
 *  tagged with two themes appears under the first only. */
export function wallTopic(page: QuoteTopicPage, per = 3, seen = new Set<string>()): WallTopic {
	const best = page.authors
		.map((g) => {
			const q = g.quotes
				.filter((x) => x.text.length <= WALL_MAX && !seen.has(x.slug))
				.sort((a, b) => a.text.length - b.text.length)[0];
			return q ? { quote: q, author: g.author.name } : null;
		})
		.filter((l): l is WallLine => !!l)
		.sort((a, b) => a.quote.text.length - b.quote.text.length)
		.slice(0, per);
	for (const l of best) seen.add(l.quote.slug);
	return { slug: page.topic.slug, title: page.topic.title, lines: best };
}

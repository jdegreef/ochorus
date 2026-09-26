import type { ArticleSummary } from './library-public';

/**
 * The /articles index's pure logic — which articles are guides, how the shelf
 * filters and sorts, which ones it features, and how it groups them by topic.
 * Kept out of the components so it is tested once and shared by the index and
 * the /articles/<topic>/ shelves.
 */

/** A reader's guide to one book. The API says so (`kind`); an API running
 *  behind this build omits the field, so fall back to the slug convention the
 *  backend itself uses (`GUIDE_SLUG_SUFFIX`). */
export const isGuide = (a: ArticleSummary): boolean =>
	a.kind ? a.kind === 'guide' : a.slug.endsWith('-guide');

/** The Questions / Book guides switch. '' (All) is the default. */
export const ARTICLE_KINDS = ['questions', 'guides'] as const;
export type ArticleKind = (typeof ARTICLE_KINDS)[number];

export const ofKind = (a: ArticleSummary, kind: string): boolean =>
	kind === 'guides' ? isGuide(a) : kind === 'questions' ? !isGuide(a) : true;

/** Free-text match over what a reader would type: the headline, the
 *  standfirst, the book it leads to and its author, and its topics. */
export function matchesQuery(a: ArticleSummary, q: string): boolean {
	const needle = q.trim().toLocaleLowerCase();
	if (!needle) return true;
	const hay = [
		a.h1,
		a.description,
		a.lead_book?.title,
		a.lead_book?.author.name,
		...(a.topics ?? []).map((tc) => tc.title)
	];
	return hay.some((s) => s?.toLocaleLowerCase().includes(needle));
}

/** Shelf orders. `featured` is the API's own curated order (sort_order). */
export const ARTICLE_SORTS = ['featured', 'newest', 'shortest', 'title'] as const;
export type ArticleSort = (typeof ARTICLE_SORTS)[number];

export function sortArticles(list: ArticleSummary[], sort: ArticleSort): ArticleSummary[] {
	if (sort === 'featured') return list;
	const arr = [...list];
	switch (sort) {
		case 'newest':
			// ISO timestamps sort as strings; ties keep the curated order.
			return arr.sort((a, b) => (b.created_at ?? '').localeCompare(a.created_at ?? ''));
		case 'shortest':
			return arr.sort((a, b) => a.word_count - b.word_count);
		default:
			return arr.sort((a, b) => a.h1.localeCompare(b.h1));
	}
}

/**
 * The "Start here" picks — one on prayer, one for suffering, one for doubt:
 * the three doors most readers arrive through. Editorial, so a list in code;
 * an article that is missing (renamed, unpublished) is skipped and the gap is
 * filled from the curated order, so the section never shows a dead card.
 */
export const FEATURED_ARTICLES = [
	'how-to-pray-so-god-answers',
	'how-to-trust-god-in-suffering',
	'can-i-be-a-christian-and-have-doubts'
] as const;

export function featuredArticles(articles: ArticleSummary[], count = 3): ArticleSummary[] {
	const bySlug = new Map(articles.map((a) => [a.slug, a]));
	const picks = FEATURED_ARTICLES.map((s) => bySlug.get(s)).filter(
		(a): a is ArticleSummary => !!a
	);
	for (const a of articles) {
		if (picks.length >= count) break;
		if (!isGuide(a) && !picks.includes(a)) picks.push(a);
	}
	return picks.slice(0, count);
}

export interface TopicGroup {
	slug: string;
	title: string;
	/** Articles under the topic, in shelf order. */
	count: number;
	/** The first few, for the group's card. */
	items: ArticleSummary[];
}

/**
 * The shelf's topics, largest first (ties alphabetical), each with its first
 * `per` QUESTION articles — the "Browse by topic" grid. Guides are left out of
 * the preview (a topic card reading "X: Summary and Study Guide" three times
 * says little about the topic) but counted, since the topic shelf lists them.
 */
export function topicGroups(articles: ArticleSummary[], limit = 6, per = 3): TopicGroup[] {
	const groups = new Map<string, TopicGroup>();
	for (const a of articles) {
		for (const tc of a.topics ?? []) {
			let g = groups.get(tc.slug);
			if (!g) groups.set(tc.slug, (g = { slug: tc.slug, title: tc.title, count: 0, items: [] }));
			g.count += 1;
			if (g.items.length < per && !isGuide(a)) g.items.push(a);
		}
	}
	return [...groups.values()]
		.filter((g) => g.items.length > 0)
		.sort((x, y) => y.count - x.count || x.title.localeCompare(y.title))
		.slice(0, limit);
}

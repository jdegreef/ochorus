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

/** Shelf orders. `featured` is the API's own curated order (sort_order), with
 *  the questions ahead of the book guides: seventy-odd guides at the front of
 *  the list buried the questions readers come with, and the guides have their
 *  own rail and switch. */
export const ARTICLE_SORTS = ['featured', 'newest', 'shortest', 'title'] as const;
export type ArticleSort = (typeof ARTICLE_SORTS)[number];

export function sortArticles(list: ArticleSummary[], sort: ArticleSort): ArticleSummary[] {
	if (sort === 'featured') {
		const guides = list.filter(isGuide);
		return guides.length && guides.length < list.length
			? [...list.filter((a) => !isGuide(a)), ...guides]
			: list;
	}
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

/**
 * "Questions people ask", by the situation a reader arrives in — when life
 * hurts, when they doubt, when they are new. Editorial, so a list in code like
 * the Start-here picks; slugs are shared across languages, so each locale
 * shows the ones it has. A situation with fewer than two of its articles here
 * is dropped, and the Start-here picks are skipped so no card repeats.
 */
export const SITUATIONS = [
	{
		k: 'articles.situationHurts',
		slugs: [
			'how-to-find-comfort-in-grief-and-loss',
			'why-would-a-good-god-allow-suffering',
			'how-to-overcome-fear-and-anxiety-with-faith',
			'how-to-find-rest-for-your-soul',
			'how-to-trust-god-in-suffering'
		]
	},
	{
		k: 'articles.situationDoubt',
		slugs: [
			'how-to-overcome-doubt',
			'is-the-bible-reliable',
			'how-do-we-know-jesus-rose',
			'do-science-and-faith-contradict',
			'can-i-be-a-christian-and-have-doubts'
		]
	},
	{
		k: 'articles.situationNew',
		slugs: [
			'what-is-the-gospel',
			'how-to-be-born-again',
			'how-to-have-assurance-of-salvation',
			'how-to-read-the-bible-for-beginners',
			'what-is-baptism'
		]
	},
	{
		k: 'articles.situationSin',
		slugs: [
			'how-to-overcome-sin-and-temptation',
			'how-to-deal-with-guilt-and-shame',
			'how-to-forgive-someone-who-hurt-you',
			'how-to-overcome-anger',
			'what-is-repentance'
		]
	},
	{
		k: 'articles.situationPray',
		slugs: [
			'what-is-intercessory-prayer',
			'how-to-pray-the-psalms',
			'the-power-of-persistent-prayer',
			'the-morning-watch',
			'how-to-pray-so-god-answers'
		]
	},
	{
		k: 'articles.situationDirection',
		slugs: [
			'how-to-find-gods-will-for-your-life',
			'how-to-hear-gods-voice',
			'how-to-wait-on-god',
			'how-to-know-if-god-is-calling-you-to-ministry',
			'how-to-be-content'
		]
	}
] as const;

export function situationGroups(
	articles: ArticleSummary[],
	skip: ArticleSummary[] = [],
	per = 4
): { k: string; items: ArticleSummary[] }[] {
	const bySlug = new Map(articles.map((a) => [a.slug, a]));
	const skipped = new Set(skip.map((a) => a.slug));
	return SITUATIONS.map(({ k, slugs }) => ({
		k,
		items: slugs
			.filter((s) => !skipped.has(s))
			.flatMap((s) => bySlug.get(s) ?? [])
			.slice(0, per)
	})).filter((g) => g.items.length >= 2);
}

/**
 * "New to faith? Read these in order" — one numbered path from the good news
 * to the first steps in a church. Unlike the situations (a door per need, in
 * any order), the order here IS the content: each step assumes the one before.
 * Slugs are shared across languages; a locale shows the steps it has, and the
 * path is hidden below three (a two-step "path" is just two links).
 */
export const NEW_BELIEVER_PATH = [
	'what-is-the-gospel',
	'how-to-be-born-again',
	'how-to-have-assurance-of-salvation',
	'how-to-read-the-bible-for-beginners',
	'how-to-grow-in-your-faith',
	'what-is-the-church',
	'what-is-baptism'
] as const;

export function newBelieverPath(articles: ArticleSummary[], min = 3): ArticleSummary[] {
	const bySlug = new Map(articles.map((a) => [a.slug, a]));
	const steps = NEW_BELIEVER_PATH.flatMap((s) => bySlug.get(s) ?? []);
	return steps.length >= min ? steps : [];
}

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

export interface TopicCount {
	slug: string;
	title: string;
	/** Articles under the topic. */
	count: number;
}

/** Each topic on the shelf with how many articles it holds, in first-seen
 *  order. The one counting pass behind both the topic-filter chips and the
 *  "Browse by topic" grid, so their numbers can't disagree. `?? []` guards a
 *  lagging API that predates the `topics` field (version skew). */
export function topicCounts(articles: ArticleSummary[]): TopicCount[] {
	const bySlug = new Map<string, TopicCount>();
	for (const a of articles) {
		for (const tc of a.topics ?? []) {
			const seen = bySlug.get(tc.slug);
			if (seen) seen.count += 1;
			else bySlug.set(tc.slug, { slug: tc.slug, title: tc.title, count: 1 });
		}
	}
	return [...bySlug.values()];
}

export interface TopicGroup extends TopicCount {
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
	return topicCounts(articles)
		.map((c) => ({
			...c,
			items: articles
				.filter((a) => !isGuide(a) && (a.topics ?? []).some((tc) => tc.slug === c.slug))
				.slice(0, per)
		}))
		.filter((g) => g.items.length > 0)
		.sort((x, y) => y.count - x.count || x.title.localeCompare(y.title))
		.slice(0, limit);
}

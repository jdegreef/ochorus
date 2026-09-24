/**
 * Turning search hits into what the results page renders.
 *
 * Six hit types arrive in six shapes; the page shows one list. That flattening,
 * the grouping into type sections, the clustering of chapter matches under their
 * book, the counts, and the order the keyboard walks are all decisions — and
 * they lived inside a 1,420-line component where nothing could reach them. The
 * page still owns the query, the paging and the URL, which are genuinely
 * coupled to the router; this is the part that is a function of the data.
 *
 * Pure on purpose: no runes, no DOM, no fetch. Everything here can be checked
 * against a handful of hits, which is what `searchResults.test.ts` does — the
 * per-type caps and the "20 of 400" counting had no test at all before, and the
 * counting is the half that has been wrong twice.
 */
import { portraitPosition } from '$lib/portraits';
import { authorPath } from './originals';
import { scripturePageHref } from '$lib/library-public';
import type { ChapterHit, SearchHit, SearchType } from '$lib/library-public';
import { chapterName } from './reading';

/** One flat shape for every hit type, so the list renders uniformly. */
export interface Row {
	key: string;
	/** The type chip. */
	label: string;
	href: string;
	title: string;
	/** The muted line under the title. */
	meta: string;
	/** May be empty for entities with no prose. */
	snippet: string;
	date: string;
	/** Cover or portrait. "" for rows that have neither — topics and plans. */
	image: string;
	/** Backing colour for the reserved box, so the list never reflows. */
	color: string;
	/** Portraits are round and small; covers keep a book's proportions. */
	round: boolean;
	/** Where the face sits in a portrait; unset for covers, which crop nothing. */
	focus?: string;
}

export type ResultRow = Row & { type: SearchHit['type'] };

/** What `toRow` needs from the page: the type chip's wording, and the query. */
export interface RowContext {
	/** i18n lookup for the type chip. */
	label: (type: SearchHit['type']) => string;
	/**
	 * The query that produced these hits. It rides along on chapter and sermon
	 * links so the reader lands on the match rather than at the top.
	 */
	query: string;
}

export function toRow(hit: SearchHit, ctx: RowContext): Row {
	const withQuery = (path: string) =>
		ctx.query ? `${path}?q=${encodeURIComponent(ctx.query)}` : path;

	switch (hit.type) {
		case 'author':
			return {
				key: 'author:' + hit.author_slug,
				label: ctx.label('author'),
				href: authorPath(hit.author_slug),
				title: hit.author_name,
				meta: '',
				snippet: hit.snippet,
				date: hit.date,
				image: hit.photo_url,
				color: '',
				round: true,
				focus: portraitPosition(hit.author_slug)
			};
		case 'book':
			return {
				key: 'book:' + hit.book_slug,
				label: ctx.label('book'),
				href: `/books/${hit.book_slug}`,
				title: hit.book_title,
				meta: hit.author_name,
				snippet: hit.snippet,
				date: hit.date,
				image: hit.cover_url,
				color: hit.cover_color,
				round: false
			};
		case 'topic':
			return {
				key: 'topic:' + hit.topic_slug,
				label: ctx.label('topic'),
				href: `/topics/${hit.topic_slug}`,
				title: hit.topic_title,
				meta: '',
				snippet: hit.snippet,
				date: hit.date,
				image: '',
				color: '',
				round: false
			};
		case 'plan':
			return {
				key: 'plan:' + hit.plan_slug,
				label: ctx.label('plan'),
				href: `/plans/${hit.plan_slug}`,
				title: hit.plan_title,
				meta: '',
				snippet: hit.snippet,
				date: hit.date,
				image: '',
				color: '',
				round: false
			};
		case 'article':
			return {
				key: 'article:' + hit.article_slug,
				label: ctx.label('article'),
				href: `/articles/${hit.article_slug}`,
				title: hit.article_title,
				meta: '',
				snippet: hit.snippet,
				date: hit.date,
				image: '',
				color: '',
				round: false
			};
		case 'scripture':
			return {
				key: `scripture:${hit.book_slug}:${hit.chapter}:${hit.verse ?? ''}`,
				label: ctx.label('scripture'),
				href: scripturePageHref(hit.book_slug, hit.chapter, hit.verse),
				title: hit.reference,
				meta: '',
				snippet: hit.snippet,
				date: hit.date,
				image: '',
				color: '',
				round: false
			};
		case 'sermon':
			return {
				key: 'sermon:' + hit.sermon_slug,
				label: ctx.label('sermon'),
				href: withQuery(`/sermons/${hit.sermon_slug}`),
				title: hit.sermon_title,
				meta: hit.scripture_ref
					? `${hit.author_name} · ${hit.scripture_ref}`
					: hit.author_name,
				snippet: hit.snippet,
				date: hit.date,
				image: '',
				color: '',
				round: false
			};
		default:
			return {
				key: `chapter:${hit.book_slug}:${hit.chapter_order}`,
				label: ctx.label('chapter'),
				href: withQuery(`/books/${hit.book_slug}/${hit.chapter_order}`),
				title: chapterName(hit.chapter_order, hit.chapter_title),
				meta: `${hit.book_title} · ${hit.author_name}`,
				snippet: hit.snippet,
				date: hit.date,
				image: hit.cover_url,
				color: hit.cover_color,
				round: false
			};
	}
}

/**
 * Type sections in a fixed reading order — navigational entities first,
 * passages last. The order is editorial, not alphabetical: someone searching a
 * theme is usually after the book or the topic, and the passages are the long
 * tail underneath them.
 */
export const GROUP_ORDER: { type: SearchHit['type']; labelKey: string }[] = [
	// Scripture leads: it only appears for a reference query, where the passage
	// hub is the most direct answer, above the books/passages that treat it.
	{ type: 'scripture', labelKey: 'search.groupScripture' },
	{ type: 'book', labelKey: 'search.groupBooks' },
	{ type: 'author', labelKey: 'search.groupAuthors' },
	{ type: 'topic', labelKey: 'search.groupTopics' },
	{ type: 'plan', labelKey: 'search.groupPlans' },
	{ type: 'article', labelKey: 'search.groupArticles' },
	{ type: 'chapter', labelKey: 'search.groupPassages' },
	{ type: 'sermon', labelKey: 'search.groupSermons' }
];

export interface ResultGroup {
	type: SearchHit['type'];
	labelKey: string;
	rows: ResultRow[];
}

/** Cluster rows into type sections, keeping only the sections present. */
export function groupRows(rows: ResultRow[]): ResultGroup[] {
	const by = new Map<string, ResultRow[]>();
	for (const r of rows) {
		const arr = by.get(r.type);
		if (arr) arr.push(r);
		else by.set(r.type, [r]);
	}
	return GROUP_ORDER.filter((g) => by.has(g.type)).map((g) => ({
		type: g.type,
		labelKey: g.labelKey,
		rows: by.get(g.type)!
	}));
}

export interface PassageBook {
	slug: string;
	title: string;
	author: string;
	date: string;
	cover: string;
	color: string;
	chapters: { key: string; order: number; title: string; snippet: string }[];
}

/**
 * Collapse chapter matches under their book, so "where does this theme live
 * across the work" reads as a map rather than a scatter of unrelated lines.
 *
 * Server order throughout: books in first-match order, chapters in book order.
 * Re-sorting here would silently override the relevance the server ranked by.
 */
export function passageBooks(hits: SearchHit[]): PassageBook[] {
	const by = new Map<string, PassageBook>();
	for (const h of hits) {
		if (h.type !== 'chapter') continue;
		const c = h as ChapterHit;
		let g = by.get(c.book_slug);
		if (!g) {
			g = {
				slug: c.book_slug,
				title: c.book_title,
				author: c.author_name,
				date: c.date,
				cover: c.cover_url,
				color: c.cover_color,
				chapters: []
			};
			by.set(c.book_slug, g);
		}
		g.chapters.push({
			key: `${c.book_slug}:${c.chapter_order}`,
			order: c.chapter_order,
			title: c.chapter_title || c.book_title,
			snippet: c.snippet
		});
	}
	return [...by.values()];
}

/**
 * Every match across every type.
 *
 * The mixed list is capped per type so no one kind crowds out the others, which
 * used to be invisible: the page reported the number of rows it had been handed,
 * and a search matching four hundred passages rendered "30 results". `totals`
 * is the server's real count per type; a type it did not count falls back to
 * what is loaded, which is only ever an undercount, never an invented number.
 */
export function grandTotal(
	groups: ResultGroup[],
	totals: Partial<Record<SearchType, number>>
): number {
	return groups.reduce(
		(n, g) => n + (totals[g.type as SearchType] ?? g.rows.length),
		0
	);
}

/** How many matches of `type` exist — the server's count, else what is loaded. */
export function totalFor(
	totals: Partial<Record<SearchType, number>>,
	type: SearchType,
	loaded: number
): number {
	return totals[type] ?? loaded;
}

/** The flattened, visible leaf results, in display order. */
export interface NavList {
	keys: string[];
	/** key → href. */
	map: Map<string, string>;
	/** key → what a screen reader announces. */
	labels: Map<string, string>;
	/** key → its type, which doubles as the position the click log records. */
	types: Map<string, SearchType>;
}

/**
 * Flatten what is on screen so ↑/↓ walk it and Enter opens the active one.
 *
 * Only the SHOWN passage chapters: a collapsed book contributes its preview and
 * no more, or the arrow keys would walk through rows the reader cannot see.
 */
export function navList(
	groups: ResultGroup[],
	books: PassageBook[],
	expanded: ReadonlySet<string>,
	previewCap: number
): NavList {
	const keys: string[] = [];
	const map = new Map<string, string>();
	const labels = new Map<string, string>();
	const types = new Map<string, SearchType>();

	for (const g of groups) {
		if (g.type === 'chapter') {
			for (const pb of books) {
				const shown = expanded.has(pb.slug)
					? pb.chapters
					: pb.chapters.slice(0, previewCap);
				for (const ch of shown) {
					keys.push(ch.key);
					map.set(ch.key, `/books/${pb.slug}/${ch.order}`);
					labels.set(ch.key, `${ch.title} — ${pb.title}`);
					types.set(ch.key, 'chapter');
				}
			}
		} else {
			for (const row of g.rows) {
				keys.push(row.key);
				map.set(row.key, row.href);
				labels.set(row.key, row.meta ? `${row.title} — ${row.meta}` : row.title);
				types.set(row.key, g.type as SearchType);
			}
		}
	}
	return { keys, map, labels, types };
}

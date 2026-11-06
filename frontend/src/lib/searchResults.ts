/**
 * Turning search hits into what the results page renders.
 *
 * Six hit types arrive in six shapes; the page shows one list. That flattening,
 * the grouping into type sections, the one top result, the counts, and the
 * order the keyboard walks are all decisions — and
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
import type { CoverFace, SearchHit, SearchType } from '$lib/library-public';
import { chapterName } from './reading';
import { foldText } from './searchNormalize';
import { sermonArt } from './sermonArt';

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
	/** A book's cover to DRAW (title over its ground) rather than show as a bare
	 *  image — a plate ground carries no words. Absent on non-book rows. */
	face?: CoverFace;
	/** Portraits are round and small; covers keep a book's proportions. */
	round: boolean;
	/** Where the face sits in a portrait; unset for covers, which crop nothing. */
	focus?: string;
	/**
	 * A sermon's passage, drawn as its monogram (MAT over 11) in `color` — the
	 * mark it wears on every shelf. Absent on other rows.
	 */
	monogram?: { scriptureRef: string; title: string };
	/**
	 * Where a passage sits — "All of Grace · Chapter 3" — shown above its
	 * snippet. Only chapter rows carry one: a passage is read by where it is.
	 */
	location?: string;
}

export type ResultRow = Row & {
	type: SearchHit['type'];
	/** An admin's pinned best match for this query (see `leadWithPinned`). */
	pinned?: boolean;
};

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
				face: hit.cover,
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
				// The hue each sermon wears on shelves and its plate.
				color: sermonArt(hit.sermon_slug).hue,
				round: true,
				monogram: { scriptureRef: hit.scripture_ref, title: hit.sermon_title }
			};
		default: {
			const title = chapterName(hit.chapter_order, hit.chapter_title);
			return {
				key: `chapter:${hit.book_slug}:${hit.chapter_order}`,
				label: ctx.label('chapter'),
				href: withQuery(`/books/${hit.book_slug}/${hit.chapter_order}`),
				title,
				meta: `${hit.book_title} · ${hit.author_name}`,
				location: `${hit.book_title} · ${title}`,
				snippet: hit.snippet,
				date: hit.date,
				image: hit.cover_url,
				color: hit.cover_color,
				face: hit.cover,
				round: false
			};
		}
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

/**
 * Put the group holding a pinned best match first. Groups otherwise keep their
 * fixed order (GROUP_ORDER), so a pinned topic would sit below every book — not
 * leading anything. The server already put the pinned hit first in the merged
 * list, so within its group it is already the top row.
 */
export function leadWithPinned(groups: ResultGroup[]): ResultGroup[] {
	const i = groups.findIndex((g) => g.rows.some((r) => r.pinned));
	return i > 0 ? [groups[i], ...groups.slice(0, i), ...groups.slice(i + 1)] : groups;
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
 * Every kind is one row per result now — passages included, each carrying its
 * own "Book · Chapter" — so the walk is simply the rows in display order.
 */
export function navList(groups: ResultGroup[]): NavList {
	const keys: string[] = [];
	const map = new Map<string, string>();
	const labels = new Map<string, string>();
	const types = new Map<string, SearchType>();

	for (const g of groups) {
		for (const row of g.rows) {
			keys.push(row.key);
			map.set(row.key, row.href);
			labels.set(row.key, row.meta ? `${row.title} — ${row.meta}` : row.title);
			types.set(row.key, g.type as SearchType);
		}
	}
	return { keys, map, labels, types };
}

/**
 * Case, accents and punctuation folded away, so "all of grace" names "All of
 * Grace". `foldText` strips only Latin combining marks on purpose: stripping
 * every mark would delete Devanagari vowel signs and fold different Hindi
 * titles together.
 */
function fold(s: string): string {
	return foldText(s)
		.replace(/[^\p{L}\p{M}\p{N}]+/gu, ' ')
		.trim();
}

/**
 * The one result worth a larger card above the list: a book or a writer the
 * query names exactly ("all of grace", "spurgeon" does not; "Charles Spurgeon"
 * does), or an admin's pinned best match when that is a book or a writer.
 *
 * Exact, not "first": a top card over a fuzzy match claims an answer the
 * reader didn't ask for. Books win a tie with writers because the reader came
 * to read, and the writer is one tap away from the book.
 */
export function topResult(rows: ResultRow[], query: string): ResultRow | null {
	const named = rows.filter((r) => r.type === 'book' || r.type === 'author');
	const pinned = named.find((r) => r.pinned);
	if (pinned) return pinned;
	const q = fold(query);
	if (q.length < 2) return null;
	const exact = named.filter((r) => fold(r.title) === q);
	return exact.find((r) => r.type === 'book') ?? exact[0] ?? null;
}

/**
 * The admin's inventory lists: one page per kind of content (`/admin/books`,
 * `/admin/authors`, …), all drawn by `AdminCatalog.svelte` from the config
 * below over `GET /api/admin/catalog/<kind>/` (backend
 * `library/admin_views/catalog.py`, whose `KINDS` must offer the same kinds,
 * sorts and statuses).
 *
 * Pure: no Svelte, no fetch — so the columns, labels and links are unit-tested
 * (`adminCatalog.test.ts`). Admin copy is English-only.
 */
import type { SourceType } from './library-public';

export type CatalogKind =
	'books' | 'sermons' | 'authors' | 'plans' | 'topics' | 'articles' | 'quotes' | 'series';

/** One row as the API sends it — the union of every kind's fields. */
export interface CatalogRow {
	slug: string;
	title: string;
	language?: string;
	author?: { slug: string; name: string };
	source_type?: SourceType;
	is_published?: boolean;
	reviewed?: boolean;
	source?: { kind: 'book' | 'sermon'; slug: string; title: string } | null;
	created_at?: string | null;
	updated_at?: string | null;
	[field: string]: unknown;
}

export interface CatalogPage {
	kind: CatalogKind;
	total: number;
	page: number;
	pages: number;
	page_size: number;
	sort: string;
	sorts: string[];
	results: CatalogRow[];
	facets: {
		languages: { code: string; count: number }[];
		statuses: Record<string, number>;
		sources: SourceType[];
	};
}

export interface CatalogQuery {
	q?: string;
	language?: string;
	status?: string;
	source?: string;
	sort?: string;
	page?: number;
}

/** A number column: the row field it reads and its header. */
export interface CatalogColumn {
	field: string;
	label: string;
}

export interface CatalogConfig {
	label: string;
	/** Singular, for "1 book" / "No books match". */
	noun: string;
	blurb: string;
	/** Number columns after the title, in order. */
	columns: CatalogColumn[];
	statusLabels: Record<string, string>;
	sortLabels: Record<string, string>;
	/** The row's admin page, when the kind has one. */
	adminHref?: (row: CatalogRow) => string;
	/** The row's page on the site (unlocalized — the page puts it in the row's language). */
	siteHref: (row: CatalogRow) => string;
	/** The small grey line under the title. */
	meta: (row: CatalogRow) => string;
}

const PUBLISHED = { published: 'Published', unpublished: 'Unpublished' };
const BASIC_SORTS = { title: 'Title', newest: 'Newest', updated: 'Recently changed' };

export const SOURCE_LABELS: Record<SourceType, string> = {
	public_domain: 'Public domain',
	ai_reviewed: 'AI · reviewed',
	ai_unreviewed: 'AI · unreviewed'
};

const enc = encodeURIComponent;
const byline = (r: CatalogRow) => r.author?.name ?? '';
const join = (...parts: (string | false | null | undefined)[]) => parts.filter(Boolean).join(' · ');

export const CATALOG: Record<CatalogKind, CatalogConfig> = {
	books: {
		label: 'Books',
		noun: 'book',
		blurb: 'Every edition of every book — one row per language.',
		columns: [
			{ field: 'chapters', label: 'Chapters' },
			{ field: 'words', label: 'Words' }
		],
		statusLabels: PUBLISHED,
		sortLabels: { ...BASIC_SORTS, words: 'Longest', author: 'Author' },
		adminHref: (r) => `/admin/books/${enc(r.slug)}`,
		siteHref: (r) => `/books/${enc(r.slug)}`,
		meta: (r) => join(byline(r), r.series as string)
	},
	sermons: {
		label: 'Sermons',
		noun: 'sermon',
		blurb: 'Every sermon, one row per language.',
		columns: [
			{ field: 'words', label: 'Words' },
			{ field: 'questions', label: 'Q&A' }
		],
		statusLabels: PUBLISHED,
		sortLabels: { ...BASIC_SORTS, words: 'Longest', author: 'Author' },
		adminHref: (r) => `/admin/sermons/${enc(r.slug)}`,
		siteHref: (r) => `/sermons/${enc(r.slug)}`,
		meta: (r) => join(byline(r), r.scripture_ref as string)
	},
	authors: {
		label: 'Authors',
		noun: 'author',
		blurb: 'The people (and imprints) behind the library, with what each still lacks.',
		columns: [
			{ field: 'books', label: 'Books' },
			{ field: 'sermons', label: 'Sermons' },
			{ field: 'translations', label: 'Bio translations' }
		],
		statusLabels: { no_bio: 'No biography', no_photo: 'No photo', imprint: 'Imprints' },
		sortLabels: { title: 'Name', works: 'Most works', newest: 'Newest' },
		siteHref: (r) => `/authors/${enc(r.slug)}`,
		meta: (r) =>
			join(
				r.years as string,
				r.is_imprint ? 'imprint' : false,
				!r.is_imprint && !r.has_bio && 'no biography',
				!r.is_imprint && !r.has_photo && 'no photo'
			)
	},
	plans: {
		label: 'Plans',
		noun: 'plan',
		blurb: 'Reading plans, one row per language.',
		columns: [{ field: 'days', label: 'Days' }],
		statusLabels: PUBLISHED,
		sortLabels: { title: 'Title', newest: 'Newest', days: 'Longest' },
		siteHref: (r) => `/plans/${enc(r.slug)}`,
		meta: (r) => r.slug
	},
	topics: {
		label: 'Topics',
		noun: 'topic',
		blurb: 'Topic shelves and how much each holds. Works are counted once, in any language.',
		columns: [
			{ field: 'books', label: 'Books' },
			{ field: 'sermons', label: 'Sermons' },
			{ field: 'articles', label: 'Articles' },
			{ field: 'translations', label: 'Translations' }
		],
		statusLabels: PUBLISHED,
		sortLabels: { title: 'Title', works: 'Most works', newest: 'Newest' },
		siteHref: (r) => `/topics/${enc(r.slug)}`,
		meta: (r) => r.slug
	},
	articles: {
		label: 'Articles',
		noun: 'article',
		blurb: 'Articles, one row per language.',
		columns: [{ field: 'words', label: 'Words' }],
		statusLabels: PUBLISHED,
		sortLabels: { ...BASIC_SORTS, words: 'Longest' },
		siteHref: (r) => `/articles/${enc(r.slug)}`,
		meta: (r) => r.slug
	},
	quotes: {
		label: 'Quotes',
		noun: 'quote',
		blurb: 'Every sourced quote, with the work it comes from.',
		columns: [],
		statusLabels: { reviewed: 'Reviewed', unreviewed: 'Not reviewed' },
		sortLabels: { newest: 'Newest', author: 'Author' },
		siteHref: (r) => `/quotes/${enc(r.author?.slug ?? '')}`,
		meta: (r) => join(byline(r), r.source?.title)
	},
	series: {
		label: 'Series',
		noun: 'series',
		blurb: 'Named runs of works, with how far each has got.',
		columns: [
			{ field: 'books', label: 'Books' },
			{ field: 'planned', label: 'Planned' },
			{ field: 'translations', label: 'Translations' }
		],
		statusLabels: {},
		sortLabels: { title: 'Title', books: 'Most books', newest: 'Newest' },
		siteHref: (r) => `/series/${enc(r.slug)}`,
		meta: (r) => join(r.audience as string, r.slug)
	}
};

/** `n noun(s)` — "1 book", "3 series" (series is its own plural). */
export function countLabel(n: number, noun: string): string {
	const plural = noun.endsWith('s') ? noun : `${noun}s`;
	return `${new Intl.NumberFormat('en').format(n)} ${n === 1 ? noun : plural}`;
}

/** A query as a search string ('' when unfiltered); empty filters and page 1
 *  are left off, so the plain list has the plain URL. */
export function urlSearch(query: CatalogQuery): string {
	const params = new URLSearchParams();
	for (const [k, v] of Object.entries(query))
		if (v !== undefined && v !== '' && !(k === 'page' && v === 1)) params.set(k, String(v));
	const qs = params.toString();
	return qs ? `?${qs}` : '';
}

/** The API path for one page of a list. */
export const catalogPath = (kind: CatalogKind, query: CatalogQuery): string =>
	`/api/admin/catalog/${kind}/${urlSearch(query)}`;

/** The query a list page's URL carries (`?q=&language=&status=&source=&sort=&page=`),
 *  so a filtered list can be bookmarked, shared and returned to with Back. */
export function queryFromUrl(params: URLSearchParams): CatalogQuery {
	const page = Number(params.get('page'));
	return {
		q: params.get('q') ?? '',
		language: params.get('language') ?? '',
		status: params.get('status') ?? '',
		source: params.get('source') ?? '',
		sort: params.get('sort') ?? '',
		page: Number.isInteger(page) && page > 1 ? page : 1
	};
}

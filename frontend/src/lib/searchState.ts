import type { SearchSort } from './library-public';

/**
 * The search view as a URL, and back again.
 *
 * A filtered, sorted result list is a real view — worth sharing, worth
 * surviving a reload, and worth restoring when the reader opens a passage and
 * presses Back. That makes the query string part of the page's contract, so the
 * two directions live here as pure functions rather than inline in the
 * component, where neither could be tested.
 *
 * Two rules do the work:
 *
 * - **Defaults never appear.** `?q=prayer` and `?q=prayer&type=all&sort=relevance`
 *   are the same view; emitting the second would give the common case an ugly
 *   link and make an unchanged view look like a changed one.
 * - **What comes back in is not trusted.** A URL is user input; an unknown sort
 *   degrades to relevance rather than reaching the API.
 */

export const SEARCH_SORTS: readonly SearchSort[] = ['relevance', 'title', 'newest'];

/** The places a search can be narrowed to. Mirrors `library.search.SCOPES`. */
export const SEARCH_SCOPES = ['author', 'topic', 'book'] as const;

export interface SearchState {
	q: string;
	/** A hit type, or 'all' for the merged list. */
	type: string;
	sort: SearchSort;
	/** `kind:slug` — the shelf being searched inside — or '' for the library. */
	scope: string;
}

export const DEFAULT_SEARCH_STATE: SearchState = {
	q: '',
	type: 'all',
	sort: 'relevance',
	scope: ''
};

/** Identity of a view, for telling "the reader navigated" from "we wrote the URL". */
export const searchStateKey = (s: SearchState): string =>
	`${s.q}|${s.type}|${s.sort}|${s.scope}`;

/**
 * A link into a scoped search — the one place that spells the `?in=` contract.
 *
 * Every entry point (author page, topic page, book page, the reader's in-book
 * drawer) goes through here, so they encode identically to what the page itself
 * writes back. Hand-built, they didn't: `?in=book:humility` from a link versus
 * `?in=book%3Ahumility` from `writeSearchState` parse the same but differ as
 * text, so arriving from a link immediately rewrote the URL to another spelling.
 */
export function scopedSearchHref(
	kind: (typeof SEARCH_SCOPES)[number],
	slug: string,
	q = ''
): string {
	return `/search${writeSearchState(new URL('https://x/search'), {
		...DEFAULT_SEARCH_STATE,
		q: q.trim(),
		scope: `${kind}:${slug}`
	}).search}`;
}

/**
 * A `kind:slug` scope, or '' if it isn't one.
 *
 * Shape only — whether the shelf exists is the server's answer, and it comes
 * back in the response as a label (or as null, which the page reports).
 */
function readScope(raw: string): string {
	const [kind, ...rest] = raw.split(':');
	const slug = rest.join(':');
	return (SEARCH_SCOPES as readonly string[]).includes(kind) && slug ? `${kind}:${slug}` : '';
}

/** Read a view out of a query string, degrading anything unrecognised. */
export function readSearchState(params: URLSearchParams): SearchState {
	const q = (params.get('q') ?? '').trim();
	const rawSort = params.get('sort') ?? '';
	const sort = (SEARCH_SORTS as readonly string[]).includes(rawSort)
		? (rawSort as SearchSort)
		: 'relevance';
	// A facet without a query describes nothing, so it is dropped rather than
	// left to filter an empty list. A scope is the exception: it survives an
	// empty query, because arriving from "search inside this book" means
	// standing in the scope before typing anything.
	const type = q ? (params.get('type') || 'all') : 'all';
	return {
		q,
		type,
		sort: q ? sort : 'relevance',
		scope: readScope(params.get('in') ?? '')
	};
}

/** Write a view into `url`'s query string, in place, and return it. */
export function writeSearchState(url: URL, state: SearchState): URL {
	const { q, type, sort, scope } = state;
	if (q) url.searchParams.set('q', q);
	else url.searchParams.delete('q');
	if (q && type !== 'all') url.searchParams.set('type', type);
	else url.searchParams.delete('type');
	if (q && sort !== 'relevance') url.searchParams.set('sort', sort);
	else url.searchParams.delete('sort');
	if (scope) url.searchParams.set('in', scope);
	else url.searchParams.delete('in');
	return url;
}

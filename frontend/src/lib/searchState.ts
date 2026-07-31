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

export interface SearchState {
	q: string;
	/** A hit type, or 'all' for the merged list. */
	type: string;
	sort: SearchSort;
}

export const DEFAULT_SEARCH_STATE: SearchState = { q: '', type: 'all', sort: 'relevance' };

/** Identity of a view, for telling "the reader navigated" from "we wrote the URL". */
export const searchStateKey = (s: SearchState): string => `${s.q}|${s.type}|${s.sort}`;

/** Read a view out of a query string, degrading anything unrecognised. */
export function readSearchState(params: URLSearchParams): SearchState {
	const q = (params.get('q') ?? '').trim();
	const rawSort = params.get('sort') ?? '';
	const sort = (SEARCH_SORTS as readonly string[]).includes(rawSort)
		? (rawSort as SearchSort)
		: 'relevance';
	// A facet without a query describes nothing, so it is dropped rather than
	// left to filter an empty list.
	const type = q ? (params.get('type') || 'all') : 'all';
	return { q, type, sort: q ? sort : 'relevance' };
}

/** Write a view into `url`'s query string, in place, and return it. */
export function writeSearchState(url: URL, state: SearchState): URL {
	const { q, type, sort } = state;
	if (q) url.searchParams.set('q', q);
	else url.searchParams.delete('q');
	if (q && type !== 'all') url.searchParams.set('type', type);
	else url.searchParams.delete('type');
	if (q && sort !== 'relevance') url.searchParams.set('sort', sort);
	else url.searchParams.delete('sort');
	return url;
}

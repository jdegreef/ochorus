import type { SearchSort } from './library-public';
import { readFilters, writeFilters } from './urlFilters';

/**
 * The search view as a URL, and back again.
 *
 * A filtered, sorted result list is a real view — worth sharing, worth
 * surviving a reload, and worth restoring when the reader opens a passage and
 * presses Back. That makes the query string part of the page's contract, so the
 * two directions live here as pure functions rather than inline in the
 * component, where neither could be tested.
 *
 * Two rules do the work, and they are not this page's alone — `urlFilters`
 * holds them for every filterable shelf, and this builds on it:
 *
 * - **Defaults never appear.** `?q=prayer` and `?q=prayer&type=all&sort=relevance`
 *   are the same view; emitting the second would give the common case an ugly
 *   link and make an unchanged view look like a changed one.
 * - **What comes back in is not trusted.** A URL is user input; an unknown sort
 *   degrades to relevance rather than reaching the API.
 *
 * What is genuinely search's own, and stays here, is the COUPLING between the
 * fields: a facet means nothing without a query, and `?in=` is a `kind:slug`
 * pair rather than a flat value. Both are normalisation either side of the
 * generic encode/decode.
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

/** The query string's shape, before search's own coupling rules apply. */
const WIRE_DEFAULTS = { q: '', type: 'all', sort: 'relevance', in: '' };
const WIRE_ALLOWED = { sort: SEARCH_SORTS } as const;

/** Read a view out of a query string, degrading anything unrecognised. */
export function readSearchState(params: URLSearchParams): SearchState {
	const wire = readFilters(params, WIRE_DEFAULTS, WIRE_ALLOWED);
	const q = wire.q.trim();
	// A facet without a query describes nothing, so it is dropped rather than
	// left to filter an empty list. A scope is the exception: it survives an
	// empty query, because arriving from "search inside this book" means
	// standing in the scope before typing anything.
	return {
		q,
		type: q ? wire.type : 'all',
		sort: q ? (wire.sort as SearchSort) : 'relevance',
		scope: readScope(wire.in)
	};
}

/** Write a view into a copy of `url`'s query string and return it. */
export function writeSearchState(url: URL, state: SearchState): URL {
	const { q, type, sort, scope } = state;
	// The coupling, applied before the generic write: with no query there is no
	// facet and no sort to speak of, so they go back to their defaults and are
	// dropped for us.
	return writeFilters(
		url,
		{ q, type: q ? type : 'all', sort: q ? sort : 'relevance', in: scope },
		WIRE_DEFAULTS
	);
}

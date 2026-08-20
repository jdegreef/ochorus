import { describe, expect, it } from 'vitest';
import {
	DEFAULT_SEARCH_STATE,
	readSearchState,
	scopedSearchHref,
	searchStateKey,
	writeSearchState
} from './searchState';

const read = (qs: string) => readSearchState(new URLSearchParams(qs));
const write = (state: Parameters<typeof writeSearchState>[1]) =>
	writeSearchState(new URL('https://ochorus.com/search'), state).search;

describe('reading a search view out of the URL', () => {
	it('takes the query, the facet and the sort', () => {
		expect(read('q=prayer&type=chapter&sort=newest')).toEqual({
			q: 'prayer',
			type: 'chapter',
			sort: 'newest',
			scope: ''
		});
	});

	it('falls back to the defaults when nothing is asked for', () => {
		expect(read('')).toEqual(DEFAULT_SEARCH_STATE);
	});

	it('degrades an unknown sort rather than passing it on', () => {
		// The query string is user input and goes on to reach the API.
		expect(read('q=prayer&sort=; drop table').sort).toBe('relevance');
	});

	it('drops a facet that has no query to filter', () => {
		// `?type=chapter` with nothing to search describes no view at all, and
		// would leave the page looking filtered with an empty list.
		expect(read('type=chapter&sort=newest')).toEqual(DEFAULT_SEARCH_STATE);
	});

	it('trims the query, so a stray space is not a different search', () => {
		expect(read('q=%20prayer%20').q).toBe('prayer');
	});

	it('takes a well-formed scope', () => {
		expect(read('q=grace&in=author:andrew-murray').scope).toBe('author:andrew-murray');
	});

	it('keeps a scope that has no query yet', () => {
		// Arriving from "search inside this book" puts you in the scope before
		// you have typed anything — unlike a facet, which describes nothing
		// without a query.
		expect(read('in=book:humility').scope).toBe('book:humility');
	});

	it('drops a scope of an unknown kind rather than passing it on', () => {
		// It reaches the API, and a kind the server doesn't know would silently
		// search the whole library under a scoped-looking URL.
		expect(read('q=grace&in=publisher:x').scope).toBe('');
		expect(read('q=grace&in=author').scope).toBe('');
		expect(read('q=grace&in=:andrew-murray').scope).toBe('');
	});
});

describe('writing a search view into the URL', () => {
	it('omits the defaults', () => {
		// ?q=prayer and ?q=prayer&type=all&sort=relevance are the same view; only
		// the first is worth sharing.
		expect(write({ q: 'prayer', type: 'all', sort: 'relevance', scope: '' })).toBe(
			'?q=prayer'
		);
	});

	it('includes a facet and sort once they differ', () => {
		expect(write({ q: 'prayer', type: 'chapter', sort: 'title', scope: '' })).toBe(
			'?q=prayer&type=chapter&sort=title'
		);
	});

	it('clears the facet when the query goes away', () => {
		expect(write({ q: '', type: 'chapter', sort: 'newest', scope: '' })).toBe('');
	});

	it('keeps the scope even with no query, and clears it when it goes', () => {
		expect(write({ q: '', type: 'all', sort: 'relevance', scope: 'book:humility' })).toBe(
			'?in=book%3Ahumility'
		);
		expect(write({ q: 'grace', type: 'all', sort: 'relevance', scope: '' })).toBe('?q=grace');
	});

	it('leaves unrelated parameters alone, and the caller\'s URL untouched', () => {
		const url = new URL('https://ochorus.com/search?utm_source=x&type=book');
		const out = writeSearchState(url, { q: 'grace', type: 'all', sort: 'relevance', scope: '' });
		// A campaign tag is not ours to drop; a stale facet is.
		expect(out.searchParams.get('utm_source')).toBe('x');
		expect(out.searchParams.has('type')).toBe(false);
		// The result is a copy: writing a view must not mutate a URL the caller
		// still holds (this used to edit it in place, which only worked because
		// every caller happened to pass `new URL(...)`).
		expect(url.searchParams.get('type')).toBe('book');
	});
});

describe('round trip', () => {
	it('survives write → read for every view the UI can produce', () => {
		for (const type of ['all', 'book', 'chapter', 'sermon']) {
			for (const sort of ['relevance', 'title', 'newest'] as const) {
				const state = { q: 'prayer', type, sort, scope: 'author:andrew-murray' };
				const back = read(write(state).replace(/^\?/, ''));
				expect(back, `${type}/${sort}`).toEqual(state);
			}
		}
	});

	it('keys two views the same only when they are the same view', () => {
		const a = { q: 'prayer', type: 'book', sort: 'title' as const, scope: '' };
		expect(searchStateKey(a)).toBe(searchStateKey({ ...a }));
		expect(searchStateKey(a)).not.toBe(searchStateKey({ ...a, type: 'chapter' }));
		expect(searchStateKey(a)).not.toBe(searchStateKey({ ...a, sort: 'newest' }));
		expect(searchStateKey(a)).not.toBe(searchStateKey({ ...a, scope: 'book:humility' }));
	});
});

describe('linking into a scoped search', () => {
	it('encodes exactly as the page writes it back', () => {
		// A link that spelled the scope differently from writeSearchState made
		// arriving from one immediately rewrite the URL.
		const href = scopedSearchHref('book', 'humility');
		expect(href).toBe('/search?in=book%3Ahumility');
		expect(href).toBe(
			'/search' + write({ ...DEFAULT_SEARCH_STATE, scope: 'book:humility' })
		);
	});

	it('carries a query when there is one', () => {
		expect(scopedSearchHref('author', 'andrew-murray', ' pride ')).toBe(
			'/search?q=pride&in=author%3Aandrew-murray'
		);
	});

	it('round-trips back to the same state', () => {
		const back = read(scopedSearchHref('topic', 'prayer', 'grace').split('?')[1]);
		expect(back.scope).toBe('topic:prayer');
		expect(back.q).toBe('grace');
	});
});

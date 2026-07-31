import { describe, expect, it } from 'vitest';
import {
	DEFAULT_SEARCH_STATE,
	readSearchState,
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
			sort: 'newest'
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
});

describe('writing a search view into the URL', () => {
	it('omits the defaults', () => {
		// ?q=prayer and ?q=prayer&type=all&sort=relevance are the same view; only
		// the first is worth sharing.
		expect(write({ q: 'prayer', type: 'all', sort: 'relevance' })).toBe('?q=prayer');
	});

	it('includes a facet and sort once they differ', () => {
		expect(write({ q: 'prayer', type: 'chapter', sort: 'title' })).toBe(
			'?q=prayer&type=chapter&sort=title'
		);
	});

	it('clears the facet when the query goes away', () => {
		expect(write({ q: '', type: 'chapter', sort: 'newest' })).toBe('');
	});

	it('leaves unrelated parameters alone', () => {
		const url = new URL('https://ochorus.com/search?utm_source=x&type=book');
		writeSearchState(url, { q: 'grace', type: 'all', sort: 'relevance' });
		expect(url.searchParams.get('utm_source')).toBe('x');
		expect(url.searchParams.has('type')).toBe(false);
	});
});

describe('round trip', () => {
	it('survives write → read for every view the UI can produce', () => {
		for (const type of ['all', 'book', 'chapter', 'sermon']) {
			for (const sort of ['relevance', 'title', 'newest'] as const) {
				const state = { q: 'prayer', type, sort };
				const back = read(write(state).replace(/^\?/, ''));
				expect(back, `${type}/${sort}`).toEqual(state);
			}
		}
	});

	it('keys two views the same only when they are the same view', () => {
		const a = { q: 'prayer', type: 'book', sort: 'title' as const };
		expect(searchStateKey(a)).toBe(searchStateKey({ ...a }));
		expect(searchStateKey(a)).not.toBe(searchStateKey({ ...a, type: 'chapter' }));
		expect(searchStateKey(a)).not.toBe(searchStateKey({ ...a, sort: 'newest' }));
	});
});

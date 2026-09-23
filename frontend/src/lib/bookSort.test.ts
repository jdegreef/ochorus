import { describe, it, expect } from 'vitest';
import { matchesBookQuery, sortBooks, type BookSort } from './bookSort';

const book = (over: Partial<Parameters<typeof matchesBookQuery>[0]> = {}) => ({
	title: 'A Title',
	subtitle: null,
	author: { name: 'An Author' },
	word_count: 1000,
	...over
});

describe('matchesBookQuery', () => {
	it('matches on title, subtitle, and author (case-insensitively)', () => {
		const b = book({ title: 'Holy Living', subtitle: 'A Rule', author: { name: 'Jeremy Taylor' } });
		expect(matchesBookQuery(b, 'holy')).toBe(true); // title
		expect(matchesBookQuery(b, 'rule')).toBe(true); // subtitle
		expect(matchesBookQuery(b, 'taylor')).toBe(true); // author
	});

	it('returns false when nothing matches', () => {
		expect(matchesBookQuery(book({ title: 'Grace', author: { name: 'Spurgeon' } }), 'zzz')).toBe(false);
	});

	it('treats an empty query as "no filter" (matches everything)', () => {
		expect(matchesBookQuery(book(), '')).toBe(true);
	});

	it('handles a null subtitle without throwing', () => {
		expect(matchesBookQuery(book({ subtitle: null }), 'nope')).toBe(false);
	});
});

describe('sortBooks', () => {
	const shelf = [
		book({ title: 'Beta', word_count: 300 }),
		book({ title: 'alpha', word_count: 900 }),
		book({ title: 'Gamma', word_count: null })
	];

	it('preserves input order for "shelf"', () => {
		expect(sortBooks(shelf, 'shelf').map((b) => b.title)).toEqual(['Beta', 'alpha', 'Gamma']);
	});

	it('sorts by title with locale-aware, case-insensitive order', () => {
		// localeCompare puts 'alpha' before 'Beta' despite the lowercase lead.
		expect(sortBooks(shelf, 'title').map((b) => b.title)).toEqual(['alpha', 'Beta', 'Gamma']);
	});

	it('sorts longest and shortest by word_count, missing count as 0', () => {
		expect(sortBooks(shelf, 'longest').map((b) => b.title)).toEqual(['alpha', 'Beta', 'Gamma']);
		expect(sortBooks(shelf, 'shortest').map((b) => b.title)).toEqual(['Gamma', 'Beta', 'alpha']);
	});

	it('does not mutate the input array', () => {
		const input = [...shelf];
		const before = input.map((b) => b.title);
		sortBooks(input, 'title');
		expect(input.map((b) => b.title)).toEqual(before);
	});

	it('accepts every BookSort value', () => {
		const sorts: BookSort[] = ['shelf', 'title', 'longest', 'shortest'];
		for (const s of sorts) expect(sortBooks(shelf, s)).toHaveLength(3);
	});
});

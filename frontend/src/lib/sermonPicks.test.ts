import { describe, expect, it } from 'vitest';
import { START_WITH, featuredOrder, startWith } from './sermonPicks';

const s = (slug: string, author: string) => ({ slug, author: { slug: author, name: author } });

// The API's order: preacher by preacher, alphabetically.
const shelf = [
	s('a1', 'a'),
	s('a2', 'a'),
	s('a3', 'a'),
	s('b1', 'b'),
	s('c1', 'c'),
	s('c2', 'c'),
	s('the-infinite-god', 'tozer'),
	s('t2', 'tozer')
];

describe('featuredOrder', () => {
	it('lets the preachers take turns, each in their own sequence', () => {
		const order = featuredOrder(shelf).map((x) => x.slug);
		// Deepest shelves first; ties by name.
		expect(order).toEqual(['a1', 'c1', 'the-infinite-god', 'b1', 'a2', 'c2', 't2', 'a3']);
	});

	it("moves deferred sermons to the end of their preacher's turn", () => {
		const order = featuredOrder(shelf, new Set(['the-infinite-god'])).map((x) => x.slug);
		expect(order).toEqual(['a1', 'c1', 't2', 'b1', 'a2', 'c2', 'the-infinite-god', 'a3']);
	});

	it('keeps every sermon exactly once', () => {
		const order = featuredOrder(shelf);
		expect(order).toHaveLength(shelf.length);
		expect(new Set(order.map((x) => x.slug)).size).toBe(shelf.length);
	});

	it('handles an empty shelf', () => {
		expect(featuredOrder([])).toEqual([]);
	});
});

describe('startWith', () => {
	it('shows the hand picks in their own order when all are present', () => {
		const full = [...START_WITH.map((slug, i) => s(slug, `p${i}`)), ...shelf];
		expect(startWith(full).map((x) => x.slug)).toEqual([...START_WITH]);
	});

	it('tops a thin language up with preachers the row does not show yet', () => {
		const picks = startWith(shelf);
		expect(picks.map((x) => x.slug)).toEqual(['the-infinite-god', 'a1', 'c1']);
		expect(new Set(picks.map((x) => x.author.slug)).size).toBe(3);
	});

	it('is empty when the shelf cannot fill the row', () => {
		expect(startWith([s('a1', 'a'), s('a2', 'a'), s('b1', 'b')])).toEqual([]);
	});
});

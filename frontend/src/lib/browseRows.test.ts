import { describe, expect, it } from 'vitest';
import { browseRows, ROW_MAX, ROW_TOPICS, START_HERE } from './browseRows';

const topic = (slug: string) => ({ slug, title: slug.toUpperCase() });
// A young-reader edition's title carries its "(For …)", as the API's do.
const titleOf = (slug: string) =>
	slug.endsWith('-teens') ? `${slug} (For Teens)` : slug.endsWith('-children') ? `${slug} (For Children)` : slug;
const book = (slug: string, ...topics: string[]) => ({ slug, title: titleOf(slug), topics: topics.map(topic) });
const many = (n: number, prefix: string, ...topics: string[]) =>
	Array.from({ length: n }, (_, i) => book(`${prefix}-${i}`, ...topics));

describe('browseRows', () => {
	it('opens on Start here, in the hand list order, then the named topics in order', () => {
		const books = [
			...START_HERE.slice(0, 5)
				.reverse()
				.map((s) => book(s)),
			...ROW_TOPICS.flatMap((t) => many(5, t, t))
		];
		const rows = browseRows(books);
		expect(rows[0].topic).toBeNull();
		expect(rows[0].books.map((b) => b.slug)).toEqual(START_HERE.slice(0, 5));
		expect(rows.slice(1).map((r) => r.topic?.slug)).toEqual([...ROW_TOPICS]);
	});

	it('tops a thin Start here up from featured order, skipping young-reader editions', () => {
		const books = [book('confessions'), book('a-children'), book('b-teens'), ...many(10, 'x')];
		const start = browseRows(books)[0];
		expect(start.topic).toBeNull();
		const slugs = start.books.map((b) => b.slug);
		expect(slugs[0]).toBe('confessions');
		expect(slugs).not.toContain('a-children');
		expect(slugs).not.toContain('b-teens');
		expect(slugs.length).toBe(8);
	});

	it('skips a topic too small for a row and fills in from the largest remaining', () => {
		const books = [
			...many(2, 'p', 'prayer'),
			...many(6, 'e', 'enduring-classics'),
			...many(9, 'w', 'women-of-faith'),
			...many(5, 'g', 'grace')
		];
		const topics = browseRows(books).flatMap((r) => (r.topic ? [r.topic.slug] : []));
		expect(topics).toEqual(['enduring-classics', 'women-of-faith', 'grace']);
	});

	it('caps a row but keeps the full count for See all', () => {
		const rows = browseRows(many(30, 'p', 'prayer'));
		const prayer = rows.find((r) => r.topic);
		expect(prayer?.books.length).toBe(ROW_MAX);
		expect(prayer?.count).toBe(30);
	});

	it("folds a topic's young-reader editions into their full text when it is in the row", () => {
		const books = [
			book('confessions', 'prayer'),
			book('confessions-teens', 'prayer'),
			book('confessions-children', 'prayer'),
			// Its full text is on the shelf but not in this topic: it stays.
			book('orthodoxy'),
			book('orthodoxy-teens', 'prayer'),
			...many(3, 'p', 'prayer')
		];
		const prayer = browseRows(books).find((r) => r.topic?.slug === 'prayer');
		expect(prayer?.books.map((b) => b.slug)).toEqual(['confessions', 'orthodoxy-teens', 'p-0', 'p-1', 'p-2']);
		expect(prayer?.count).toBe(5);
		const unfolded = browseRows(books, false).find((r) => r.topic?.slug === 'prayer');
		expect(unfolded?.count).toBe(7);
	});

	it('draws no rows for an empty shelf', () => {
		expect(browseRows([])).toEqual([]);
	});
});

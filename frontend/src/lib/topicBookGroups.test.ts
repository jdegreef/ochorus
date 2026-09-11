import { describe, expect, it } from 'vitest';
import { groupBooksByAuthor, type GroupableBook } from './topicBookGroups';

const book = (authorSlug: string): GroupableBook => ({
	author: { slug: authorSlug, name: authorSlug, photo_url: `${authorSlug}.jpg` }
});

describe('groupBooksByAuthor', () => {
	it('groups an author-clustered topic (most books share an author)', () => {
		// The Puritans shape: 6 authors, clusters of 2–3, 9 of 11 books clustered.
		const books = [
			book('bunyan'), book('bunyan'),
			book('sibbes'),
			book('owen'),
			book('watson'), book('watson'),
			book('baxter'), book('baxter'),
			book('edwards'), book('edwards'), book('edwards')
		];
		const groups = groupBooksByAuthor(books);
		expect(groups).not.toBeNull();
		expect(groups!.map((g) => `${g.slug}:${g.items.length}`)).toEqual([
			'bunyan:2', 'sibbes:1', 'owen:1', 'watson:2', 'baxter:2', 'edwards:3'
		]);
	});

	it('stays flat for a diverse gallery (mostly one-off authors)', () => {
		// Women of Faith shape: many distinct authors, only a couple clustered —
		// 5 of 13 clustered, not a majority.
		const books = [
			...['foote', 'lee', 'wesley', 'booth', 'carmichael', 'guyon', 'buyinza'].map(book),
			book('hws'), book('hws'), book('hws'),
			book('originals'), book('originals'),
			book('smith')
		];
		expect(groupBooksByAuthor(books)).toBeNull();
	});

	it('stays flat for a single-author topic', () => {
		expect(groupBooksByAuthor([book('spurgeon'), book('spurgeon'), book('spurgeon')])).toBeNull();
	});

	it('stays flat when every book is a different author', () => {
		expect(groupBooksByAuthor([book('a'), book('b'), book('c')])).toBeNull();
	});

	it('returns null for zero or one book', () => {
		expect(groupBooksByAuthor([])).toBeNull();
		expect(groupBooksByAuthor([book('a')])).toBeNull();
	});

	it('preserves first-appearance author order and within-author order', () => {
		const b1 = book('x'), b2 = book('y'), b3 = book('x'), b4 = book('x');
		const groups = groupBooksByAuthor([b1, b2, b3, b4]);
		// x appears first (3 books), then y — and x's majority makes it group.
		expect(groups!.map((g) => g.slug)).toEqual(['x', 'y']);
		expect(groups![0].items).toEqual([b1, b3, b4]);
	});
});

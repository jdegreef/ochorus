import { describe, expect, it } from 'vitest';
import type { BookSummary, Hub } from '$lib/library-public';
import {
	BOOK_HUB_FLOOR,
	eraBooks,
	erasWithBooks,
	hasPage,
	traditionBooks,
	traditionsWithBooks
} from './bookHubs';

const book = (slug: string, author: string, birth: number | null, is_imprint = false) =>
	({
		slug,
		title: slug,
		author: { slug: author, name: author, birth_year: birth, is_imprint }
	}) as BookSummary;

const hub = (slug: string, members: string[], kind: Hub['kind'] = 'tradition') =>
	({ slug, kind, members, label: slug }) as Hub;

const puritans = [
	book('mortification-of-sin', 'john-owen', 1616),
	book('the-bruised-reed', 'richard-sibbes', 1577),
	book('a-call-to-the-unconverted', 'richard-baxter', 1615),
	book('grace-abounding', 'john-bunyan', 1628),
	book('grace-abounding-teens', 'john-bunyan', 1628),
	book('the-pilgrims-progress', 'john-bunyan', 1628)
];

describe('traditionBooks', () => {
	it('lists the members’ full editions, earliest-born writer first', () => {
		const got = traditionBooks(hub('puritans', ['john-owen', 'richard-sibbes', 'john-bunyan']), [
			...puritans,
			book('humility', 'andrew-murray', 1828)
		]);
		expect(got.map((b) => b.slug)).toEqual([
			'the-bruised-reed',
			'mortification-of-sin',
			'grace-abounding',
			'the-pilgrims-progress'
		]);
	});
});

describe('the floor', () => {
	it('wants enough books by more than one writer', () => {
		expect(hasPage(puritans.slice(0, BOOK_HUB_FLOOR))).toBe(true);
		expect(hasPage(puritans.slice(0, BOOK_HUB_FLOOR - 1))).toBe(false);
		const oneWriter = Array.from({ length: 6 }, (_, i) => book(`b${i}`, 'spurgeon', 1834));
		expect(hasPage(oneWriter)).toBe(false);
	});

	it('gives a page only to a tradition hub that clears it', () => {
		const hubs = [
			hub('puritans', ['john-owen', 'richard-sibbes', 'richard-baxter', 'john-bunyan']),
			hub('baptists', ['john-bunyan']),
			hub('england', ['john-owen', 'richard-sibbes', 'richard-baxter', 'john-bunyan'], 'place')
		];
		expect(traditionsWithBooks(hubs, puritans).map((h) => h.slug)).toEqual(['puritans']);
	});
});

describe('eras', () => {
	it('files a book by its writer’s birth year, leaving house imprints out', () => {
		const books = [
			...puritans,
			book('rooted', 'ochorus', null, true),
			book('the-shepherd-of-hermas', 'hermas', null),
			book('x', 'modern-writer', 1950)
		];
		expect(eraBooks('puritans', books)).toHaveLength(5);
		// Neither the imprint nor the undated Father is filed as modern.
		expect(eraBooks('modern', books).map((b) => b.slug)).toEqual(['x']);
		expect(erasWithBooks(books)).toEqual(['puritans']);
	});
});

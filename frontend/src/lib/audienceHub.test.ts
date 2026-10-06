import { describe, expect, it } from 'vitest';
import {
	AUDIENCE_HUBS,
	TEENS_HUB,
	YOUNG_READERS_HUB,
	hubCounts,
	hubIsEmpty,
	printableLinks,
	startPick
} from './audienceHub';
import type { AudienceShelf, BookSummary, SeriesSummary } from './library-public';

const book = (slug: string): BookSummary => ({ slug, title: `${slug} title` }) as BookSummary;
const series = (slug: string, books: string[]): SeriesSummary =>
	({ slug, title: `${slug} title`, book_count: books.length, books }) as SeriesSummary;

const shelf = (parts: Partial<AudienceShelf> = {}): AudienceShelf => ({
	audience: 'young_readers',
	series: [],
	editions: [],
	more: [],
	plans: [],
	topic: null,
	printable: [],
	languages: [],
	...parts
});

describe('startPick', () => {
	it('takes the first preferred slug the language has', () => {
		const s = shelf({ editions: [book('a'), book('b')], more: [book('c')] });
		expect(startPick(s, ['missing', 'c', 'b'])?.slug).toBe('c');
	});

	it('falls back to the first book when none of the picks is here', () => {
		const s = shelf({ editions: [book('a')], more: [book('c')] });
		expect(startPick(s, ['missing'])?.slug).toBe('a');
	});

	it('is null on a hub with no books', () => {
		expect(startPick(shelf({ series: [series('rooted', ['rooted-1'])] }), [])).toBeNull();
	});
});

describe('hubCounts / hubIsEmpty', () => {
	it('counts series volumes and loose books once each', () => {
		const s = shelf({
			series: [series('bfg', ['bfg-1', 'bfg-2']), series('rooted', ['rooted-1'])],
			editions: [book('a')],
			more: [book('b'), book('c')]
		});
		expect(hubCounts(s)).toEqual({ books: 6, series: 2 });
		expect(hubIsEmpty(s)).toBe(false);
	});

	it('a hub with only plans is still empty — plans read the hub’s books', () => {
		expect(hubIsEmpty(shelf())).toBe(true);
	});
});

describe('printableLinks', () => {
	it('folds a series into one link and keeps loose books', () => {
		const s = shelf({
			series: [series('bfg', ['bfg-1', 'bfg-2']), series('rooted', ['rooted-1'])],
			more: [book('songs'), book('north-wind')],
			printable: ['bfg-1', 'bfg-2', 'songs']
		});
		expect(printableLinks(s)).toEqual([
			{ href: '/series/bfg/', label: 'bfg title' },
			{ href: '/books/songs', label: 'songs title' }
		]);
	});

	it('is empty when nothing prints', () => {
		expect(printableLinks(shelf({ more: [book('a')] }))).toEqual([]);
	});
});

describe('AUDIENCE_HUBS', () => {
	it('lists both hubs, young readers first, each at its own path', () => {
		expect(AUDIENCE_HUBS).toEqual([YOUNG_READERS_HUB, TEENS_HUB]);
		expect(new Set(AUDIENCE_HUBS.map((h) => h.path)).size).toBe(2);
	});
});

import { describe, expect, it } from 'vitest';
import { existsSync } from 'node:fs';
import { resolve } from 'node:path';
import {
	AUDIENCE_HUBS,
	TEENS_HUB,
	hubFor,
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
	series: [],
	editions: [],
	more: [],
	plans: [],
	topic: null,
	start: null,
	printable: [],
	languages: [],
	...parts
});

describe('startPick', () => {
	it("is the card for the API's pick", () => {
		const s = shelf({ editions: [book('a')], more: [book('c')], start: 'c' });
		expect(startPick(s)?.slug).toBe('c');
	});

	it('is null when the hub has no pick', () => {
		expect(startPick(shelf({ series: [series('rooted', ['rooted-1'])] }))).toBeNull();
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
		expect(new Set(AUDIENCE_HUBS.map((h) => h.href)).size).toBe(2);
		expect(hubFor('teens')).toBe(TEENS_HUB);
		expect(hubFor('adults')).toBeUndefined();
	});
});

describe('each hub', () => {
	it('has its share card, where AudienceHub points (`npm run og:pages`)', () => {
		for (const h of AUDIENCE_HUBS) {
			expect(existsSync(resolve(import.meta.dirname, `../../static/og${h.href}.png`)), h.href).toBe(true);
		}
	});
});

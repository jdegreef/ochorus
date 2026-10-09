import { describe, expect, it } from 'vitest';
import { existsSync } from 'node:fs';
import { resolve } from 'node:path';
import {
	AUDIENCE_HUBS,
	TEENS_HUB,
	challengeState,
	editionFamily,
	nextRung,
	rungOf,
	hubFor,
	YOUNG_READERS_HUB,
	heroCovers,
	hubCounts,
	hubIsEmpty,
	hubPaths,
	printableLinks,
	startPick
} from './audienceHub';
import type {
	AudienceShelf,
	BookSummary,
	BookTile,
	EditionRung,
	SeriesSummary
} from './library-public';
import type { ProgressRecord } from './reading-schema';

const book = (slug: string): BookSummary =>
	({ slug, title: `${slug} title`, author: { slug: 'a', name: 'A' } }) as BookSummary;
const tile = (slug: string): BookTile =>
	({ kind: 'book', slug, title: slug, cover_url: '', cover_color: '' }) as BookTile;
const series = (slug: string, books: string[]): SeriesSummary =>
	({
		slug,
		title: `${slug} title`,
		book_count: books.length,
		books,
		covers: books.map(tile)
	}) as SeriesSummary;

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

describe('hubPaths', () => {
	it('keeps only the paths whose place this language has, in the hub’s order', () => {
		const s = shelf({
			series: [series('they-were-young', ['twy-1']), series('anchored', ['anc-1', 'anc-2'])],
			more: [book('around-the-wicket-gate')],
			start: 'around-the-wicket-gate'
		});
		// No Straight Talk here, so no adventure card.
		expect(hubPaths(TEENS_HUB, s).map((p) => p.href)).toEqual([
			'/books/around-the-wicket-gate',
			'/series/anchored/',
			'/series/they-were-young/'
		]);
	});

	it('fans the covers behind each card and points a group at its anchor', () => {
		const s = shelf({
			series: [series('brave-for-god', ['bfg-1', 'bfg-2'])],
			editions: [book('pp-children')]
		});
		const [brave, bedtime] = hubPaths(YOUNG_READERS_HUB, s);
		expect(brave.covers.map((c) => c.slug)).toEqual(['bfg-1', 'bfg-2']);
		expect(bedtime).toMatchObject({ href: '#retold', titleKey: 'audience.pathBedtime' });
		expect(bedtime.covers.map((c) => c.slug)).toEqual(['pp-children']);
	});

	it('is empty on a hub with none of its places', () => {
		expect(hubPaths(TEENS_HUB, shelf({ more: [book('x')] }))).toEqual([]);
	});
});

describe('challengeState', () => {
	const rec = (furthest: number, finished = false, order = furthest): ProgressRecord =>
		({ order, furthest, paragraph_index: 0, language: 'en', at: 1, finished_at: finished ? 1 : null }) as ProgressRecord;
	const of = (map: Record<string, ProgressRecord>) => (slug: string) => map[slug] ?? null;

	it('starts at the first volume’s introduction before any reading', () => {
		expect(challengeState(['a-1', 'a-2'], 30, of({}))).toEqual({
			slug: 'a-1', day: 0, order: 1, started: false, done: false
		});
	});

	it('counts the introduction out: chapter n + 1 is day n', () => {
		expect(challengeState(['a-1'], 30, of({ 'a-1': rec(8) }))).toMatchObject({ day: 7, order: 8, started: true });
		// Still on the introduction: begun, no day yet.
		expect(challengeState(['a-1'], 30, of({ 'a-1': rec(1) }))?.day).toBe(0);
		// The closing chapter past day 30 doesn't overshoot.
		expect(challengeState(['a-1'], 30, of({ 'a-1': rec(32) }))?.day).toBe(30);
	});

	it('resumes where the reader left off, not at a peek ahead', () => {
		expect(challengeState(['a-1'], 30, of({ 'a-1': rec(12, false, 5) }))).toMatchObject({ day: 11, order: 5 });
	});

	it('moves on to the next volume once one is finished', () => {
		expect(challengeState(['a-1', 'a-2'], 30, of({ 'a-1': rec(32, true) }))).toMatchObject({
			slug: 'a-2', day: 0, started: false, done: false
		});
	});

	it('is done when every volume is finished', () => {
		const all = of({ 'a-1': rec(32, true), 'a-2': rec(32, true) });
		expect(challengeState(['a-1', 'a-2'], 30, all)).toMatchObject({ slug: 'a-2', day: 30, done: true });
	});

	it('is null for a series with no volumes here', () => {
		expect(challengeState([], 30, of({}))).toBeNull();
	});
});

describe('nextRung', () => {
	const rung = (slug: string, r: EditionRung['rung']): EditionRung => ({ ...tile(slug), rung: r });
	const ladder = [rung('pp-children', 'children'), rung('pp-teens', 'teens'), rung('pp', 'full')];

	it('is the next step up from the edition in hand', () => {
		expect(nextRung(ladder, 'pp-children')?.slug).toBe('pp-teens');
		expect(nextRung(ladder, 'pp-teens')?.slug).toBe('pp');
	});

	it('is null at the top, off the ladder, or with no ladder', () => {
		expect(nextRung(ladder, 'pp')).toBeNull();
		expect(nextRung(ladder, 'other')).toBeNull();
		expect(nextRung(undefined, 'pp-children')).toBeNull();
	});
});

describe('heroCovers', () => {
	it('puts the start pick in front, between two series’ first volumes', () => {
		const s = shelf({
			series: [series('a', ['a-1', 'a-2']), series('b', ['b-1']), series('c', ['c-1'])],
			more: [book('pick')],
			start: 'pick'
		});
		expect(heroCovers(s).map((c) => c.slug)).toEqual(['a-1', 'pick', 'b-1']);
	});

	it('without a pick, fans the first three series', () => {
		const s = shelf({ series: [series('a', ['a-1']), series('b', ['b-1'])] });
		expect(heroCovers(s).map((c) => c.slug)).toEqual(['a-1', 'b-1']);
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

describe('rungOf / editionFamily', () => {
	it('reads the rung off the slug', () => {
		expect(rungOf('pilgrims-progress-children')).toBe('children');
		expect(rungOf('pilgrims-progress-teens')).toBe('teens');
		expect(rungOf('pilgrims-progress')).toBe('full');
	});

	it('puts the original first, then teens, then children', () => {
		const fam = editionFamily({ slug: 'pp-teens' }, [{ slug: 'pp-children' }, { slug: 'pp' }]);
		expect(fam.map((e) => e.slug)).toEqual(['pp', 'pp-teens', 'pp-children']);
	});
});

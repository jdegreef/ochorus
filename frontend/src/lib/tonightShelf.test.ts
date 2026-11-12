import { describe, expect, it } from 'vitest';
import type { AuthorBio, BookSummary, SermonSummary } from './library-public';
import {
	isEvening,
	tonightKey,
	tonightPool,
	tonightShelf,
	TONIGHT_MIN_ITEMS,
	TONIGHT_SHOWN,
	wordsOf,
	type TonightItem
} from './tonightShelf';

const book = (slug: string, author: string, word_count: number, language = 'en') =>
	({
		slug,
		language,
		title: slug,
		cover_url: '',
		word_count,
		chapter_count: 3,
		author: { slug: author, name: author, birth_year: 1800 }
	}) as BookSummary;
const sermon = (slug: string, author: string, word_count: number, language = 'en') =>
	({
		slug,
		language,
		title: slug,
		scripture_ref: 'John 3:16',
		word_count,
		author: { slug: author, name: author, birth_year: 1800 }
	}) as SermonSummary;
const writer = (slug: string, bio_word_count?: number, has_long_bio = true) =>
	({ slug, name: slug, birth_year: 1800, death_year: 1880, has_long_bio, bio_word_count }) as AuthorBio;

const at = (h: number, m = 0) => new Date(2026, 10, 12, h, m);
const at200 = (words: number) => Math.max(1, Math.round(words / 200));

describe('isEvening', () => {
	it('is evening from 19:00 through midnight until 04:00', () => {
		expect(isEvening(at(18, 59))).toBe(false);
		expect(isEvening(at(19))).toBe(true);
		expect(isEvening(at(23, 59))).toBe(true);
		expect(isEvening(at(0))).toBe(true);
		expect(isEvening(at(3, 59))).toBe(true);
		expect(isEvening(at(4))).toBe(false);
		expect(isEvening(at(12))).toBe(false);
	});
});

describe('tonightPool', () => {
	const lists = {
		books: [
			book('short-a', 'a', 3000),
			book('short-b', 'b', 3800),
			book('long', 'c', 90_000),
			book('no-count', 'd', 0),
			book('pilgrims-progress-children', 'bunyan', 3500),
			book('in-spanish', 'e', 2000, 'es')
		],
		sermons: [
			sermon('s1', 'f', 2500),
			sermon('s2', 'g', 3800),
			sermon('s-twenty', 'j', 4000),
			sermon('s-long', 'h', 8000),
			sermon('s-es', 'i', 2000, 'es')
		],
		authors: [writer('w1', 2600), writer('w2', 9000), writer('w3', 0, false), writer('w4')]
	};

	it('keeps only works of under 20 minutes at the default pace, in this language', () => {
		const pool = tonightPool(lists, 'en', 20000);
		const keys = pool.map(tonightKey).sort();
		expect(keys).toEqual(
			[
				'book:short-a',
				'book:short-b',
				'book:pilgrims-progress-children',
				'sermon:s1',
				'sermon:s2',
				'bio:w1'
			].sort()
		);
		expect(pool.every((i) => wordsOf(i) > 0 && Math.round(wordsOf(i) / 200) < 20)).toBe(true);
	});

	it('is per-language: another language gets only its own rows, never English', () => {
		const es = tonightPool(lists, 'es', 20000).map(tonightKey).sort();
		// Biographies come from the per-language authors list the caller fetched.
		expect(es).toEqual(['bio:w1', 'book:in-spanish', 'sermon:s-es']);
	});

	it('puts full texts before young-reader editions and interleaves the kinds', () => {
		const pool = tonightPool(lists, 'en', 20000);
		expect(pool.slice(0, 3).map((i) => i.kind)).toEqual(['book', 'sermon', 'bio']);
		const books = pool.filter((i) => i.kind === 'book').map(tonightKey);
		expect(books.at(-1)).toBe('book:pilgrims-progress-children');
	});

	it('never backfills a young-reader edition beside its own full text', () => {
		const pool = tonightPool(
			{
				...lists,
				books: [
					book('pilgrims-progress', 'bunyan', 3000),
					book('pilgrims-progress-children', 'bunyan', 2000),
					book('pilgrims-progress-teens', 'bunyan', 2500),
					book('other-children', 'x', 1500)
				]
			},
			'en',
			20000
		);
		expect(
			pool
				.filter((i) => i.kind === 'book')
				.map(tonightKey)
				.sort()
		).toEqual(['book:other-children', 'book:pilgrims-progress']);
	});

	it('keeps a 20-minute work off a shelf promising "under 20 minutes"', () => {
		const keys = tonightPool(lists, 'en', 20000).map(tonightKey);
		expect(keys).not.toContain('sermon:s-twenty');
		const shelf = tonightShelf(
			[...tonightPool(lists, 'en', 20000), ...tonightPool(lists, 'en', 20000)],
			new Date(2026, 10, 12, 21),
			() => 20
		);
		expect(shelf).toEqual([]);
	});

	it('skips biographies when the API does not send their length', () => {
		const pool = tonightPool({ ...lists, authors: [writer('w5')] }, 'en', 20000);
		expect(pool.some((i) => i.kind === 'bio')).toBe(false);
	});

	it('is a pure function of the lists and the day', () => {
		expect(tonightPool(lists, 'en', 20001)).toEqual(tonightPool(lists, 'en', 20001));
	});
});

describe('tonightShelf', () => {
	const pool: TonightItem[] = Array.from({ length: 8 }, (_, i) => ({
		kind: 'sermon',
		sermon: {
			slug: `s${i}`,
			language: 'en',
			title: `S${i}`,
			scripture_ref: '',
			word_count: 1000 + i * 400, // 5 … 19 min at 200 wpm
			author: { slug: `a${i}`, name: `A${i}`, birth_year: null }
		}
	}));

	it('shows nothing outside the evening', () => {
		expect(tonightShelf(pool, at(10), at200)).toEqual([]);
		expect(tonightShelf(pool, at(18, 30), at200)).toEqual([]);
		expect(tonightShelf(pool, at(4, 30), at200)).toEqual([]);
	});

	it('shows up to the shelf size in the evening, in pool order', () => {
		const shown = tonightShelf(pool, at(21), at200);
		expect(shown).toHaveLength(TONIGHT_SHOWN);
		expect(shown).toEqual(pool.slice(0, TONIGHT_SHOWN));
		expect(tonightShelf(pool, at(1), at200)).toHaveLength(TONIGHT_SHOWN);
	});

	it("re-times each work at the reader's own pace", () => {
		// At 100 wpm only three (10, 14 and 18 min) still fit: below the threshold.
		const slow = (w: number) => Math.round(w / 100);
		expect(tonightShelf(pool, at(21), slow)).toEqual([]);
		// At 140 wpm: 7, 10, 13, 16, 19 min fit; 21 does not.
		const steady = (w: number) => Math.round(w / 140);
		expect(tonightShelf(pool, at(21), steady).map(tonightKey)).toEqual(
			['s0', 's1', 's2', 's3', 's4'].map((s) => `sermon:${s}`)
		);
	});

	it(`hides when fewer than ${TONIGHT_MIN_ITEMS} works qualify`, () => {
		const few = pool.slice(0, TONIGHT_MIN_ITEMS - 1);
		expect(tonightShelf(few, at(21), at200)).toEqual([]);
		expect(tonightShelf(pool.slice(0, TONIGHT_MIN_ITEMS), at(21), at200)).toHaveLength(
			TONIGHT_MIN_ITEMS
		);
		expect(tonightShelf([], at(21), at200)).toEqual([]);
	});
});

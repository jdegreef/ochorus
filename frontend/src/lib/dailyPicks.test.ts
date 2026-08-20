/**
 * The daily rotation behind the home shelf and the not-found page.
 *
 * Both surfaces used to show `books.slice(0, n)` — on the home page baked into
 * the prerendered HTML, so the front of the library was frozen at build time
 * and, because the API lists by author, usually several works by the same one
 * or two people. `pickByDay` is what makes those shelves move and spread, so
 * its three promises are asserted here: same day → same picks, distinct authors
 * first, and a balanced backfill when there aren't enough distinct ones.
 */
import { describe, expect, it } from 'vitest';
import { pickByDay, dayNumber } from './dailyPicks';

type Work = { id: string; author: string };
const authorOf = (w: Work) => w.author;

/** `n` works spread over `authors` people, round-robin. */
function library(n: number, authors: number): Work[] {
	return Array.from({ length: n }, (_, i) => ({
		id: `w${i}`,
		author: `a${i % authors}`
	}));
}

describe('dayNumber', () => {
	it('advances by one per calendar day', () => {
		const a = dayNumber(new Date('2026-08-20T09:00:00'));
		const b = dayNumber(new Date('2026-08-21T09:00:00'));
		expect(b - a).toBe(1);
	});

	it('is the same all day long', () => {
		expect(dayNumber(new Date('2026-08-20T00:30:00'))).toBe(
			dayNumber(new Date('2026-08-20T23:30:00'))
		);
	});
});

describe('pickByDay', () => {
	const books = library(30, 12);

	it('is deterministic for a given day', () => {
		expect(pickByDay(books, 6, 500, authorOf)).toEqual(pickByDay(books, 6, 500, authorOf));
	});

	it('moves from one day to the next', () => {
		// Not a guarantee for every pair of days, but over a week a 30-book
		// shelf must not sit still — that was the whole complaint.
		const week = Array.from({ length: 7 }, (_, d) =>
			pickByDay(books, 6, 500 + d, authorOf)
				.map((b) => b.id)
				.join(',')
		);
		expect(new Set(week).size).toBeGreaterThan(1);
	});

	it('picks distinct authors when it can', () => {
		for (let day = 0; day < 40; day++) {
			const picks = pickByDay(books, 6, day, authorOf);
			expect(picks).toHaveLength(6);
			expect(new Set(picks.map(authorOf)).size).toBe(6);
		}
	});

	it('prefers authors a previous shelf did not already feature', () => {
		const first = pickByDay(books, 3, 7, authorOf);
		const second = pickByDay(books, 3, 7, authorOf, first.map(authorOf));
		// Nine distinct authors exist, so the second shelf never has to reuse one.
		expect(second.map(authorOf).some((a) => first.map(authorOf).includes(a))).toBe(false);
	});

	it('falls back to reusing authors rather than returning a short shelf', () => {
		// Three people, six slots: variety within the shelf beats the exclusion.
		const small = library(12, 3);
		const picks = pickByDay(small, 6, 3, authorOf, ['a0', 'a1', 'a2']);
		expect(picks).toHaveLength(6);
	});

	it('backfills evenly instead of clustering on one author', () => {
		// Four works, two authors, four slots: 2/2, never 3/1.
		const picks = pickByDay(library(4, 2), 4, 11, authorOf);
		const counts = new Map<string, number>();
		for (const p of picks) counts.set(p.author, (counts.get(p.author) ?? 0) + 1);
		expect([...counts.values()].sort()).toEqual([2, 2]);
	});

	it('never repeats an item within one shelf', () => {
		const picks = pickByDay(library(5, 1), 5, 2, authorOf);
		expect(new Set(picks.map((p) => p.id)).size).toBe(5);
	});

	it('returns everything it has when the shelf is short', () => {
		expect(pickByDay(library(2, 2), 6, 1, authorOf)).toHaveLength(2);
		expect(pickByDay([], 6, 1, authorOf)).toEqual([]);
	});
});

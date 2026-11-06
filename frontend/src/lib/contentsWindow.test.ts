import { describe, expect, it } from 'vitest';
import { contentsWindow } from './contentsWindow';

const range = (n: number) => Array.from({ length: n }, (_, i) => i + 1);
const shown = (s: Set<number> | null) => (s ? [...s].sort((a, b) => a - b) : null);

describe('contentsWindow', () => {
	it('shows everything for a short book', () => {
		expect(contentsWindow(range(9), 3)).toBeNull();
		expect(contentsWindow(range(12), null)).toBeNull();
		// Up to 20 chapters show whole (design review #9): hiding seven of
		// thirteen behind "⋯" saved little and hid the shape of the book.
		expect(contentsWindow(range(20), 7)).toBeNull();
	});

	it('collapses a book past 20 chapters', () => {
		expect(shown(contentsWindow(range(21), null))).toEqual([1, 2, 3, 4, 5, 21]);
	});

	it('shows the opening chapters and the last with no saved place', () => {
		expect(shown(contentsWindow(range(36), null))).toEqual([1, 2, 3, 4, 5, 36]);
	});

	it('shows first, last and two either side of the saved place', () => {
		expect(shown(contentsWindow(range(36), 12))).toEqual([1, 10, 11, 12, 13, 14, 36]);
	});

	it('fills a gap that would hide a single chapter', () => {
		// Place at 4: window 2..6 and chapter 1 leave no gap to fill at the start.
		expect(shown(contentsWindow(range(36), 4))).toEqual([1, 2, 3, 4, 5, 6, 36]);
		// Place at 5: window 3..7 would leave chapter 2 alone between 1 and 3.
		expect(shown(contentsWindow(range(36), 5))).toEqual([1, 2, 3, 4, 5, 6, 7, 36]);
		// Place at 33: window 31..35 would leave 36 adjacent — nothing to fill.
		expect(shown(contentsWindow(range(36), 33))).toEqual([1, 31, 32, 33, 34, 35, 36]);
	});

	it('works on the chapter orders, not positions, and ignores an unknown place', () => {
		const orders = range(24).map((o) => o + 1); // chapters 2..25
		expect(shown(contentsWindow(orders, 99))).toEqual([2, 3, 4, 5, 6, 25]);
		expect(shown(contentsWindow(orders, 25))).toEqual([2, 23, 24, 25]);
	});
});

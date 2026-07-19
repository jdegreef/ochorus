import { describe, expect, it } from 'vitest';
import { bookProgressPercent, readingMinutes, readingTime } from './reading';

describe('readingMinutes', () => {
	it('never returns less than one minute', () => {
		expect(readingMinutes(0)).toBe(1);
		expect(readingMinutes(50)).toBe(1);
	});

	it('rounds to the nearest minute at ~200 wpm', () => {
		expect(readingMinutes(200)).toBe(1);
		expect(readingMinutes(300)).toBe(2); // 1.5 rounds up
		expect(readingMinutes(500)).toBe(3); // 2.5 rounds up
	});
});

describe('bookProgressPercent', () => {
	it('does not count the open chapter as fully read (was 10% for ch1/10)', () => {
		expect(bookProgressPercent(1, 10)).toBe(5); // midpoint of chapter 1
	});

	it('stays below 100% on the last chapter so the book never vanishes', () => {
		expect(bookProgressPercent(10, 10)).toBe(95);
		expect(bookProgressPercent(16, 16)).toBeLessThan(100);
	});

	it('is always a visibly-started value in [1, 99]', () => {
		expect(bookProgressPercent(1, 1)).toBe(50);
		expect(bookProgressPercent(1, 500)).toBe(1); // clamped up from ~0
		expect(bookProgressPercent(3, 6)).toBe(42);
	});

	it('handles a zero/unknown chapter count without dividing by zero', () => {
		expect(bookProgressPercent(1, 0)).toBe(0);
	});
});

describe('readingTime', () => {
	it('labels sub-hour reads in minutes', () => {
		expect(readingTime(400)).toBe('2 min read');
	});

	it('labels a whole hour without trailing minutes', () => {
		expect(readingTime(200 * 60)).toBe('1 hr read');
	});

	it('labels hours and minutes together', () => {
		expect(readingTime(200 * 65)).toBe('1 hr 5 min read');
		expect(readingTime(200 * 130)).toBe('2 hr 10 min read');
	});
});

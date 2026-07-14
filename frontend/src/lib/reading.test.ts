import { describe, expect, it } from 'vitest';
import { readingMinutes, readingTime } from './reading';

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

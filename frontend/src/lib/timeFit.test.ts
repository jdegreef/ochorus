import { describe, expect, it } from 'vitest';
import { DEFAULT_TIME, daySeed, parseTime, readingPlaces, wordWindow } from './timeFit';

describe('wordWindow', () => {
	it('is the time there is, down to half of it, at the given pace', () => {
		expect(wordWindow(15, 200)).toEqual({ min: 1500, max: 3000 });
		expect(wordWindow(60, 250)).toEqual({ min: 7500, max: 15000 });
	});
	it('never asks for nothing', () => {
		expect(wordWindow(5, 0).max).toBe(1);
	});
});

describe('readingPlaces', () => {
	type Rec = {
		order: number;
		furthest: number;
		language: string;
		kind: 'book' | 'sermon';
		finished_at: number | null;
	};
	const rec = (slug: string, o: Partial<Rec> = {}) => ({
		slug,
		kind: 'book' as 'book' | 'sermon',
		order: 1,
		paragraph_index: 0,
		language: 'en',
		at: 0,
		...o
	});
	it('sends unfinished books in this language, newest first, at the Continue chapter', () => {
		const places = readingPlaces(
			[
				rec('a', { order: 4 }),
				rec('b', { kind: 'sermon' }),
				rec('c', { finished_at: 1 }),
				rec('d', { language: 'es' }),
				// A peek past the furthest chapter resumes at the furthest.
				rec('e', { order: 9, furthest: 6 }),
				rec('f'),
				rec('g')
			],
			'en'
		);
		expect(places).toBe('a:4,e:6,f:1');
	});
	it('is empty for a new reader', () => {
		expect(readingPlaces([], 'en')).toBe('');
	});
});

describe('parseTime', () => {
	it('restores a known choice and defaults anything else', () => {
		expect(parseTime('30')).toBe(30);
		expect(parseTime(null)).toBe(DEFAULT_TIME);
		expect(parseTime('7')).toBe(DEFAULT_TIME);
		expect(parseTime('junk')).toBe(DEFAULT_TIME);
	});
});

describe('daySeed', () => {
	it('holds all day and moves at local midnight', () => {
		const morning = daySeed(new Date(2026, 10, 11, 0, 5));
		expect(daySeed(new Date(2026, 10, 11, 23, 55))).toBe(morning);
		expect(daySeed(new Date(2026, 10, 12, 0, 1))).toBe(morning + 1);
	});
});

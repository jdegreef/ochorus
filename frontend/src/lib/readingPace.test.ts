import { beforeEach, describe, expect, it } from 'vitest';
import {
	readingPace,
	load,
	effectiveWpm,
	DEFAULT_WPM,
	TRUST_WORDS,
	WPM_MIN,
	WPM_MAX
} from './readingPace.svelte';
import { readingMinutes } from './reading';

beforeEach(() => {
	localStorage.clear();
	readingPace.reset();
});

describe('effectiveWpm', () => {
	it('answers the default until enough has been read to trust', () => {
		expect(effectiveWpm({ words: TRUST_WORDS - 1, ms: 60_000 })).toBe(DEFAULT_WPM);
		expect(effectiveWpm({ words: TRUST_WORDS, ms: 0 })).toBe(DEFAULT_WPM);
	});

	it('then answers the measured rate, within sanity bounds', () => {
		expect(effectiveWpm({ words: 3000, ms: 10 * 60_000 })).toBe(300);
		expect(effectiveWpm({ words: 3000, ms: 60 * 60_000 })).toBe(WPM_MIN);
		expect(effectiveWpm({ words: 30_000, ms: 60_000 })).toBe(WPM_MAX);
	});
});

describe('readingPace store', () => {
	it('accumulates, persists, and feeds readingMinutes', () => {
		expect(readingMinutes(2000)).toBe(10); // default 200 wpm
		readingPace.record(2000, 5 * 60_000); // this reader: 400 wpm
		expect(readingPace.personalized).toBe(true);
		expect(readingPace.wpm).toBe(400);
		expect(readingMinutes(2000)).toBe(5);
		expect(load()).toEqual({ words: 2000, ms: 5 * 60_000 });
	});

	it('ignores empty or nonsense samples', () => {
		readingPace.record(0, 1000);
		readingPace.record(100, 0);
		readingPace.record(-5, 1000);
		expect(load()).toEqual({ words: 0, ms: 0 });
	});

	it('halves the tally past the decay point so recent reading weighs most', () => {
		readingPace.record(29_000, 100 * 60_000); // 290 wpm
		readingPace.record(2000, 2 * 60_000); // 1000 wpm burst → tips over 30k
		const s = load();
		expect(s.words).toBe(15_500);
		expect(s.ms).toBe(51 * 60_000);
	});

	it('survives junk in storage', () => {
		localStorage.setItem('ochorus:reading-pace', '{"words":"lots","ms":-1}');
		expect(load()).toEqual({ words: 0, ms: 0 });
	});

	it('re-reads the cache when another tab or a wipe replaces it (ochorus:sync)', () => {
		readingPace.record(3000, 10 * 60_000);
		expect(readingPace.wpm).toBe(300);
		localStorage.removeItem('ochorus:reading-pace'); // "clear reading data"
		window.dispatchEvent(new CustomEvent('ochorus:sync'));
		expect(readingPace.wpm).toBe(DEFAULT_WPM);
		expect(readingPace.personalized).toBe(false);
	});

	it('adds to what is on disk, so two tabs do not overwrite each other', () => {
		readingPace.record(1000, 60_000);
		localStorage.setItem('ochorus:reading-pace', JSON.stringify({ words: 5000, ms: 300_000 })); // other tab
		readingPace.record(1000, 60_000);
		expect(load()).toEqual({ words: 6000, ms: 360_000 });
	});
});

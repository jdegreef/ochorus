import { describe, expect, it } from 'vitest';
import { paceDelta, paragraphWordCounts, wordCount, MIN_GAP_MS, MAX_GAP_MS } from './pace';

const words = [100, 120, 80, 150, 90, 200]; // per paragraph

describe('paceDelta', () => {
	it('credits the paragraphs scrolled past, over the time it took', () => {
		// top moved 1 → 4 in 60 s: paragraphs 1, 2, 3 = 350 words
		expect(paceDelta({ p: 1, at: 0 }, { p: 4, at: 60_000 }, words)).toEqual({ words: 350, ms: 60_000 });
	});

	it('ignores backward moves and standing still', () => {
		expect(paceDelta({ p: 4, at: 0 }, { p: 2, at: 30_000 }, words)).toBeNull();
		expect(paceDelta({ p: 4, at: 0 }, { p: 4, at: 30_000 }, words)).toBeNull();
	});

	it('ignores a flick, a long pause, a skim and a crawl', () => {
		expect(paceDelta({ p: 0, at: 0 }, { p: 1, at: MIN_GAP_MS - 1 }, words)).toBeNull(); // flick
		expect(paceDelta({ p: 0, at: 0 }, { p: 1, at: MAX_GAP_MS + 1 }, words)).toBeNull(); // coffee
		expect(paceDelta({ p: 0, at: 0 }, { p: 5, at: 5_000 }, words)).toBeNull(); // 540 words in 5 s
		expect(paceDelta({ p: 0, at: 0 }, { p: 1, at: 240_000 }, words)).toBeNull(); // 100 words in 4 min
	});

	it('ignores moves across paragraphs with no words (a figure, a rule)', () => {
		expect(paceDelta({ p: 0, at: 0 }, { p: 1, at: 30_000 }, [0, 50])).toBeNull();
	});
});

describe('word counting', () => {
	it('counts whitespace-separated tokens like the server', () => {
		expect(wordCount('  Two words.\n')).toBe(2);
		expect(wordCount('')).toBe(0);
	});

	it('maps a chapter body to per-paragraph counts', () => {
		const p = (t: string) => ({ textContent: t }) as Element;
		expect(paragraphWordCounts([p('a b c'), p(''), p('one')])).toEqual([3, 0, 1]);
	});
});

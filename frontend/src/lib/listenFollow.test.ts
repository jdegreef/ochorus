import { describe, it, expect } from 'vitest';
import { shouldFollow } from './listenFollow';

const base = {
	viewportHeight: 1000,
	headerOffset: 64,
	msSinceUserScroll: Infinity,
	yieldMs: 3000
};

describe('shouldFollow', () => {
	it('yields while the reader has scrolled by hand recently', () => {
		// Off-station, but a hand-scroll 1s ago (< yieldMs) means leave it be.
		expect(shouldFollow({ ...base, top: -200, msSinceUserScroll: 1000 })).toBe(false);
	});

	it('follows again once the yield window has passed', () => {
		expect(shouldFollow({ ...base, top: -200, msSinceUserScroll: 3001 })).toBe(true);
	});

	it('stays put when the paragraph is comfortably in the band', () => {
		// top 300 is below the header (72) and above the lower fifth (800).
		expect(shouldFollow({ ...base, top: 300 })).toBe(false);
	});

	it('scrolls when playback carried the paragraph above the header', () => {
		expect(shouldFollow({ ...base, top: 40 })).toBe(true); // 40 < 64+8
	});

	it('scrolls when the paragraph has dropped past the lower fifth', () => {
		expect(shouldFollow({ ...base, top: 850 })).toBe(true); // 850 > 800
	});

	it('treats the band edges as in-view (no scroll)', () => {
		expect(shouldFollow({ ...base, top: 72 })).toBe(false); // exactly bandTop
		expect(shouldFollow({ ...base, top: 800 })).toBe(false); // exactly bandBottom
	});
});

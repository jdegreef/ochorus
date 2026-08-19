/**
 * The popover viewport clamp.
 *
 * Both reading popovers (a scripture reference, a word definition) are centred
 * on the tapped word with `translate(-50%)` at a fixed width, so before this a
 * reference near either margin rendered half off-screen — on a phone, where the
 * measure is close to the viewport, that is most of them.
 */
import { describe, expect, it, afterEach, vi } from 'vitest';
import { clampPopoverLeft } from './reading';

const WIDTH = 320; // a 20rem popover
const GUTTER = 12;

function viewport(innerWidth: number, scrollX = 0) {
	vi.stubGlobal('window', { innerWidth, scrollX } as unknown as Window);
}

afterEach(() => vi.unstubAllGlobals());

describe('clampPopoverLeft', () => {
	it('leaves a centred popover where it is', () => {
		viewport(1200);
		expect(clampPopoverLeft(600, WIDTH)).toBe(600);
	});

	it('pushes a popover off the leading edge back inside', () => {
		viewport(1200);
		// Centred on x=10 the popover would start at -150.
		expect(clampPopoverLeft(10, WIDTH)).toBe(WIDTH / 2 + GUTTER);
	});

	it('pushes a popover off the trailing edge back inside', () => {
		viewport(1200);
		expect(clampPopoverLeft(1190, WIDTH)).toBe(1200 - WIDTH / 2 - GUTTER);
	});

	it('keeps both edges clear when the popover is wider than the viewport', () => {
		// A 320px popover on a 300px-wide screen: the CSS caps its width at
		// calc(100vw - 2rem), so the clamp has to use that capped width or it
		// would push the popover off the other side trying to fix the first.
		viewport(300);
		const left = clampPopoverLeft(0, WIDTH);
		const half = (300 - GUTTER * 2) / 2;
		expect(left).toBe(half + GUTTER);
		expect(left - half).toBeGreaterThanOrEqual(GUTTER);
		expect(left + half).toBeLessThanOrEqual(300 - GUTTER);
	});

	it('clamps against the viewport but returns page coordinates', () => {
		// The popover is absolutely positioned in the page, so a scrolled page
		// must not drag the clamp along with it.
		viewport(1200, 800);
		expect(clampPopoverLeft(800 + 10, WIDTH)).toBe(800 + WIDTH / 2 + GUTTER);
	});

	it('is inert without a window (prerender)', () => {
		vi.stubGlobal('window', undefined);
		expect(clampPopoverLeft(42, WIDTH)).toBe(42);
	});
});

import { describe, expect, it } from 'vitest';
import { pageOfOffset } from './pageMath';

// Real geometry, measured in the browser at pageW 1248 with a two-column spread
// (two columns per page, so offsets pair up: 0,0,1,1,2,2…).
const PAGE_W = 1248;
const LTR = { origin: 32, offsets: [32, 656, 1280, 1904, 2528, 3152] };
const RTL = { origin: 656, offsets: [656, 32, -592, -1216, -1840, -2464] };
const EXPECTED = [0, 0, 1, 1, 2, 2];

describe('pageOfOffset', () => {
	it('maps a left-to-right column flow', () => {
		expect(LTR.offsets.map((o) => pageOfOffset(o, LTR.origin, PAGE_W))).toEqual(EXPECTED);
	});

	it('maps a right-to-left column flow, where offsetLeft counts down', () => {
		expect(RTL.offsets.map((o) => pageOfOffset(o, RTL.origin, PAGE_W))).toEqual(EXPECTED);
	});

	it('matches the old LTR formula exactly — this is not a behaviour change', () => {
		const old = (o: number) => Math.max(0, Math.floor(o / PAGE_W));
		for (const o of LTR.offsets) {
			expect(pageOfOffset(o, LTR.origin, PAGE_W)).toBe(old(o));
		}
	});

	it('is what the old formula got WRONG in RTL', () => {
		// The bug: negatives floored below zero and clamped, so every page past the
		// first reported as page 0.
		const old = (o: number) => Math.max(0, Math.floor(o / PAGE_W));
		expect(RTL.offsets.map(old)).toEqual([0, 0, 0, 0, 0, 0]);
		expect(RTL.offsets.map((o) => pageOfOffset(o, RTL.origin, PAGE_W))).not.toEqual(
			RTL.offsets.map(old)
		);
	});

	it('degrades to page 0 before the first measurement', () => {
		expect(pageOfOffset(500, 0, 0)).toBe(0);
	});
});

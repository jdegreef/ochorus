import { describe, it, expect } from 'vitest';
import { tapTurn, swipeTurn, dampDrag } from './pageGestures';

describe('tapTurn', () => {
	it('splits the screen in half by default (touch)', () => {
		expect(tapTurn(50, 400, false)).toBe('prev'); // left half
		expect(tapTurn(350, 400, false)).toBe('next'); // right half
	});

	it('flips left/right meaning for RTL content', () => {
		expect(tapTurn(50, 400, true)).toBe('next');
		expect(tapTurn(350, 400, true)).toBe('prev');
	});

	it('with a wide dead zone only the outer edges turn (desktop 15%)', () => {
		// deadZone 0.7 → live below 0.15 and above 0.85 of the width.
		expect(tapTurn(0.1 * 400, 400, false, 0.7)).toBe('prev');
		expect(tapTurn(0.9 * 400, 400, false, 0.7)).toBe('next');
		expect(tapTurn(0.5 * 400, 400, false, 0.7)).toBe('none'); // middle is inert
		expect(tapTurn(0.4 * 400, 400, false, 0.7)).toBe('none');
	});

	it('returns none for a zero-width viewport', () => {
		expect(tapTurn(10, 0, false)).toBe('none');
	});
});

describe('swipeTurn', () => {
	const W = 400;
	it('turns on a long-enough horizontal swipe', () => {
		expect(swipeTurn(-120, 0, W, false)).toBe('next'); // left → next (LTR)
		expect(swipeTurn(120, 0, W, false)).toBe('prev');
	});

	it('flips direction under RTL content', () => {
		expect(swipeTurn(120, 0, W, true)).toBe('next'); // right → next (RTL)
		expect(swipeTurn(-120, 0, W, true)).toBe('prev');
	});

	it('ignores a swipe shorter than the threshold', () => {
		expect(swipeTurn(-40, 0, W, false)).toBe('none'); // < 18% of 400
	});

	it('ignores a mostly-vertical swipe (that is a scroll)', () => {
		expect(swipeTurn(-120, 200, W, false)).toBe('none');
	});
});

describe('dampDrag', () => {
	it('passes travel through in the middle of a chapter', () => {
		expect(dampDrag(-80, false, false, false)).toBe(-80);
		expect(dampDrag(80, false, false, false)).toBe(80);
	});

	it('damps a pull past the last page (LTR advance = leftward)', () => {
		expect(dampDrag(-80, false, true, false)).toBeCloseTo(-28); // 80 * 0.35
	});

	it('damps a pull past the first page (LTR recede = rightward)', () => {
		expect(dampDrag(80, true, false, false)).toBeCloseTo(28);
	});

	it('does not damp a legal turn even at an edge', () => {
		// At the last page, dragging BACK (rightward in LTR) is toward an earlier
		// page and must move freely.
		expect(dampDrag(80, false, true, false)).toBe(80);
	});

	it('flips which edge resists under RTL', () => {
		// RTL: advancing is rightward, so the last page resists a rightward pull.
		expect(dampDrag(80, false, true, true)).toBeCloseTo(28);
		expect(dampDrag(-80, false, true, true)).toBe(-80);
	});
});

import { describe, it, expect } from 'vitest';
import { nextBarHidden } from './readerAutohide';

const VH = 800;

describe('nextBarHidden', () => {
	it('hides when scrolling down past the deadzone', () => {
		expect(nextBarHidden(false, 400, 380, VH)).toBe(true);
	});

	it('reveals when scrolling up past the deadzone', () => {
		expect(nextBarHidden(true, 380, 400, VH)).toBe(false);
	});

	it('always shows near the top, even mid down-scroll', () => {
		expect(nextBarHidden(true, 40, 10, VH)).toBe(false);
	});

	it('ignores a tiny wobble (keeps the current state)', () => {
		expect(nextBarHidden(true, 405, 402, VH)).toBe(true);
		expect(nextBarHidden(false, 402, 405, VH)).toBe(false);
	});

	it('treats a jump larger than a viewport as programmatic and leaves the bar as-is', () => {
		// restore-scroll deep into a chapter: was showing, stays showing
		expect(nextBarHidden(false, 3000, 0, VH)).toBe(false);
		// jump back to the top from deep: was hidden, stays hidden (until a real gesture)
		expect(nextBarHidden(true, 0, 3000, VH)).toBe(true);
	});

	it('honours a custom reveal band', () => {
		expect(nextBarHidden(true, 100, 60, VH, 150)).toBe(false); // within 150 → show
		expect(nextBarHidden(false, 200, 160, VH, 150)).toBe(true); // past 150, down → hide
	});
});

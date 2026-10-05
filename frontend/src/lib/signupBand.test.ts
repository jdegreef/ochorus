import { beforeEach, describe, expect, it } from 'vitest';
import { FIRST_VISIT_ARMS, chooseVariant, firstVisitArm } from './signupBand';

beforeEach(() => localStorage.clear());

describe('firstVisitArm — sticky uniform A/B assignment', () => {
	it('assigns the arm the draw selects and persists it', () => {
		// pick() = 0.5 → floor(0.5*3) = index 1 → "habit".
		expect(firstVisitArm(() => 0.5)).toBe('habit');
		// Sticky: a later call ignores a different draw and returns the stored arm.
		expect(firstVisitArm(() => 0.99)).toBe('habit');
	});

	it('covers every arm across the draw range, and never falls off the end', () => {
		const seen = new Set<string>();
		for (const p of [0, 0.34, 0.67, 0.999]) {
			localStorage.clear();
			seen.add(firstVisitArm(() => p));
		}
		expect(seen).toEqual(new Set(FIRST_VISIT_ARMS));
	});

	it('re-draws when the stored value is not a valid arm', () => {
		// Stored via the persisted-JSON contract; 'progress' is a valid variant
		// but not an A/B arm, so it must be re-drawn.
		localStorage.setItem('ochorus:signup_arm', JSON.stringify('progress'));
		expect(firstVisitArm(() => 0)).toBe('keep');
	});
});

describe('chooseVariant — targeting beats A/B', () => {
	it('shows the progress band to a reader with local reading', () => {
		expect(chooseVariant(true)).toBe('progress');
	});

	it('shows a sticky random arm to a first-time visitor', () => {
		expect(chooseVariant(false, () => 0.8)).toBe('library');
	});

	it('does not let a stored A/B arm override live progress targeting', () => {
		chooseVariant(false, () => 0); // becomes "keep", stored as the sticky arm
		expect(chooseVariant(true)).toBe('progress');
		// …and once they have no live progress again, the sticky arm returns.
		expect(chooseVariant(false)).toBe('keep');
	});
});

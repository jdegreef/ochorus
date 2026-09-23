import { execFileSync } from 'node:child_process';
import { describe, expect, it } from 'vitest';

import { groundBar } from './groundBars';

/**
 * The bars table is measured from the committed grounds, so it goes stale the
 * moment a painting is redrawn or added. The measurement is the script's own
 * (`--check` re-measures and compares), rather than a second copy of it here.
 */
describe('groundBars', () => {
	it('matches the grounds on disk', () => {
		expect(() =>
			execFileSync('node', ['scripts/measure-ground-bars.mjs', '--check'], { stdio: 'pipe' })
		).not.toThrow();
	}, 60_000);

	it('answers 0 for anything that is not a painted ground', () => {
		expect(groundBar('/covers/waiting-on-god.svg')).toBe(0);
		expect(groundBar('/covers/the-god-of-all-comfort.jpg')).toBe(0);
		expect(groundBar('')).toBe(0);
		expect(groundBar('/covers/art/how-to-bring-men-to-christ.jpg')).toBeGreaterThan(0.03);
	});
});

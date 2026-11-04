import { execFileSync } from 'node:child_process';
import { describe, expect, it } from 'vitest';

import { FRAMED_BAR_MAX, framedBar, groundBar, isPaleGround } from './groundBars';
import { SEASON_ART } from './heroArt';

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

	it('crops a framed cover past a thin scan strip only', () => {
		// Claude's Campagna carries a 6-10px black strip along its top.
		const thin = '/covers/art/who-is-the-rich-man-that-shall-be-saved.jpg';
		expect(framedBar(thin)).toBeGreaterThan(0);
		expect(framedBar(thin)).toBe(groundBar(thin));
		// El Greco's night reads as a deep "bar": it is the picture, not a border.
		const deep = '/covers/art/the-everlasting-man.jpg';
		expect(groundBar(deep)).toBeGreaterThan(FRAMED_BAR_MAX);
		expect(framedBar(deep)).toBe(0);
		expect(framedBar('/covers/waiting-on-god.svg')).toBe(0);
	});

	it('names the pale grounds the home hero does not wash, in any width', () => {
		expect(isPaleGround('/covers/art/daughters-of-the-king-1.jpg')).toBe(true);
		expect(isPaleGround('/covers/art/daughters-of-the-king-1-640.webp')).toBe(true);
		expect(isPaleGround('/covers/art/absolute-surrender.jpg')).toBe(false);
		expect(isPaleGround('/covers/at-the-back-of-the-north-wind.svg')).toBe(false);
		expect(isPaleGround(null)).toBe(false);
	});

	it("never picks a pale painting for a season — it would hang on the hero unwashed", () => {
		for (const [season, url] of Object.entries(SEASON_ART)) {
			expect(isPaleGround(url), season).toBe(false);
		}
	});
});

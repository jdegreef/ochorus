import { describe, expect, it } from 'vitest';
import { channels, coverGradient, toHex, tintable } from './coverArt';

/** HSL lightness of a #rrggbb colour. */
const lightness = (hex: string): number => {
	const [r, g, b] = channels(hex).map((c) => c / 255);
	return (Math.max(r, g, b) + Math.min(r, g, b)) / 2;
};

/** HSL hue, in degrees. */
const hue = (hex: string): number => {
	const [r, g, b] = channels(hex).map((c) => c / 255);
	const max = Math.max(r, g, b);
	const d = max - Math.min(r, g, b);
	if (!d) return 0;
	const h = max === r ? (g - b) / d + (g < b ? 6 : 0) : max === g ? (b - r) / d + 2 : (r - g) / d + 4;
	return (h * 60 + 360) % 360;
};

describe('channels / toHex', () => {
	it('round-trips a colour', () => {
		expect(toHex(channels('#3b5bdb'))).toBe('#3b5bdb');
	});

	it('falls back rather than returning NaN channels on a malformed hex', () => {
		// `cover_color` is an unvalidated CharField, so a bad value does reach here.
		// The fallback is module-private, so this asserts the shape, not the hex.
		for (const bad of ['#abc', '', 'rgb(1,2,3)']) {
			expect(channels(bad).every(Number.isInteger), bad).toBe(true);
		}
		expect(channels('#abc')).toEqual(channels(''));
	});

	it('clamps and rounds, so callers can hand it floats', () => {
		expect(toHex([-20, 127.6, 900])).toBe('#0080ff');
	});
});

describe('coverGradient', () => {
	it('cannot carry a stray declaration out of a malformed cover_color', () => {
		// The result lands in a `style` attribute and `cover_color` is free text,
		// so both stops go through the hex guard. Tested here rather than against
		// `shade`, which is module-private.
		const out = coverGradient('#3b5bdb; background: url(x)');
		expect(out).not.toContain('url(');
		expect(out).toMatch(/^linear-gradient\(165deg, #[0-9a-f]{6} 0%, #[0-9a-f]{6} 89%\)$/);
	});
});

describe('tintable', () => {
	it('lifts a hue too dark to show through a color-mix wash', () => {
		// The raven emblem's slate: at lightness 0.22 a 9% wash of it was
		// invisible on a dark surface, so its sermon plate looked unstyled.
		const lifted = tintable('#273748');
		expect(lightness('#273748')).toBeLessThan(0.34);
		expect(lightness(lifted)).toBeCloseTo(0.34, 2);
	});

	it('pulls a hue too light back down', () => {
		expect(lightness(tintable('#d9a441'))).toBeCloseTo(0.52, 2);
	});

	it('leaves a hue already in the band exactly alone', () => {
		expect(tintable('#2f8f85')).toBe('#2f8f85');
	});

	it('keeps the emblem recognisably its own colour', () => {
		// Hue is what makes a lifted slate still read as that emblem's slate; a
		// lift that rotated it would just be a different colour. Held to 3°, not
		// to zero: blending toward white and rounding back to 8 bits moves it by
		// about a degree, and the failure this guards against is tens of them.
		for (const hex of ['#273748', '#3d7434', '#d9a441', '#2d4a80']) {
			const drift = Math.abs(hue(tintable(hex)) - hue(hex));
			expect(Math.min(drift, 360 - drift), `${hex} -> ${tintable(hex)}`).toBeLessThan(3);
		}
	});

	it('lifts a near-black grey too — it is the invisible-wash case, not an exception', () => {
		// An earlier version skipped greys "because there is no hue to restore",
		// which returned the one colour the function exists to fix: at lightness
		// 0.10 a 9% wash of it shows nothing at all. Lightness is all this moves,
		// and a grey has lightness like anything else.
		expect(lightness(tintable('#1a1a1a'))).toBeCloseTo(0.34, 2);
	});
});

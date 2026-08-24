import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';

/**
 * The scrim has to carry white type over ANY painting — including one we have
 * not chosen yet.
 *
 * A curated cover is a painting with the book's type drawn over it in white.
 * Always white: the frame, the byline, the rule and the mark are white on every
 * tier, and a per-cover decision to flip to dark ink would break the one thing
 * the tiers have in common. So the art yields, and the only thing between a
 * title and an illegible cover is `.cover-plate.over-art`'s scrim.
 *
 * The obvious test is to measure each committed painting. That test was written
 * first, and it was a tautology: the scrim is opaque enough that the worst
 * possible input — a sheet of pure white — still clears AA, so no image could
 * ever fail it and the 16 file reads proved nothing. What is actually load
 * bearing is the SCRIM, and nothing pinned it.
 *
 * So this pins the guarantee instead of sampling its consequences. It reads the
 * real stop values out of `cover-type.css`, composites them over white, and
 * checks the ink. Lighten the scrim to show more of a painting — a reasonable
 * thing to want — and this fails with the number it fell to, before a curator
 * discovers it one pale painting at a time.
 *
 * `coverBand.test.ts` is the neighbouring check: that one pins the geometry the
 * two renderers share, this one pins what the type can be trusted to land on.
 */
const COVER_CSS = readFileSync(join(process.cwd(), 'src/lib/components/cover-type.css'), 'utf-8');

/** WCAG relative luminance. */
const luminance = (rgb: number[]): number => {
	const [r, g, b] = rgb.map((c) => {
		const s = c / 255;
		return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
	});
	return 0.2126 * r + 0.7152 * g + 0.0722 * b;
};

/**
 * The scrim, read from the stylesheet rather than restated here — the whole
 * point is to notice when it changes.
 *
 * `.cover-plate.over-art` paints a four-stop black gradient over a flat wash.
 * Both are matched out of the same rule.
 */
function scrim() {
	const block = /\.cover-plate\.over-art \{([\s\S]*?)\n\}/.exec(COVER_CSS);
	expect(block, '.cover-plate.over-art is gone from cover-type.css').not.toBeNull();
	const stops = [...block![1].matchAll(/rgb\(0 0 0 \/ ([\d.]+)\)\s+([\d.]+)%/g)].map(
		([, alpha, pos]) => [Number(pos) / 100, Number(alpha)] as [number, number]
	);
	const wash = /rgb\((\d+) (\d+) (\d+) \/ ([\d.]+)\)(?!\s+[\d.]+%)/.exec(block![1]);
	expect(stops.length, 'no gradient stops found in the scrim').toBeGreaterThan(1);
	expect(wash, 'no flat wash found under the scrim gradient').not.toBeNull();
	return {
		stops,
		wash: [1, 2, 3].map((i) => Number(wash![i])),
		washAlpha: Number(wash![4])
	};
}

/** The gradient's alpha a fraction `t` down the plate. */
const alphaAt = (stops: [number, number][], t: number): number => {
	for (let i = 1; i < stops.length; i++) {
		if (t <= stops[i][0]) {
			const [p0, a0] = stops[i - 1];
			const [p1, a1] = stops[i];
			return a0 + (a1 - a0) * ((t - p0) / (p1 - p0));
		}
	}
	return stops[stops.length - 1][1];
};

/**
 * Where the type sits, how opaque its ink is, and what AA asks of it.
 *
 * The byline is the binding constraint at 4.5:1 — it is small text, and
 * `covers.py` reasons identically about the generated plates. The title runs
 * large enough to count as large text under WCAG 1.4.3, so it asks 3:1. Each
 * band is measured at its LIGHTEST point, which is where the gradient is
 * thinnest across the run of type.
 */
const BANDS = {
	byline: { from: 0.12, to: 0.18, ink: 0.86, min: 4.5 },
	title: { from: 0.33, to: 0.57, ink: 1.0, min: 3.0 },
	// Runs to 0.70 rather than the 0.64 a two-line title measures at: the title
	// block is centred by auto margins, so a three-line title pushes the
	// subtitle down, and the band has to cover the lowest it can go.
	subtitle: { from: 0.57, to: 0.7, ink: 0.85, min: 4.5 }
};

/** Contrast of the band's ink over the worst case the scrim can be asked to
 *  cover: a painting that is pure white there. */
function worstCase(band: (typeof BANDS)[keyof typeof BANDS]) {
	const { stops, wash, washAlpha } = scrim();
	let worst = Infinity;
	for (let t = band.from; t <= band.to; t += 0.005) {
		const a = alphaAt(stops, t);
		const bg = wash.map((w) => (1 - a) * (washAlpha * w + (1 - washAlpha) * 255));
		const ink = bg.map((c) => band.ink * 255 + (1 - band.ink) * c);
		const ratio = (luminance(ink) + 0.05) / (luminance(bg) + 0.05);
		if (ratio < worst) worst = ratio;
	}
	return worst;
}

describe('the art scrim carries white type over anything', () => {
	for (const [name, band] of Object.entries(BANDS)) {
		it(`holds the ${name} at ${band.min}:1 over a pure-white painting`, () => {
			const ratio = worstCase(band);
			expect(
				ratio,
				`the ${name} falls to ${ratio.toFixed(2)}:1 over white, against a ${band.min} bar. ` +
					`The scrim in cover-type.css is no longer strong enough to guarantee legible ` +
					`type, so a pale painting would now ship unreadable. Darken it, or stop ` +
					`promising that any public-domain painting can be dropped in.`
			).toBeGreaterThanOrEqual(band.min);
		});
	}
});

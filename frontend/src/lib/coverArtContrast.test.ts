import { readFileSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

/**
 * The scrim is one curve, written twice — and this is what holds the copies
 * together.
 *
 * A curated cover is a painting with the book's type drawn over it in white, so
 * something has to darken the artwork. That used to be a flat wash plus an even
 * ramp, heavy enough that a sheet of PURE WHITE cleared AA under it, and this
 * file proved exactly that. The guarantee was strong and the cost was the
 * covers: every painting was shown at 38.7% of its own brightness, which is why
 * a translated cover looked dark beside the hand-made English one.
 *
 * The scrim now follows the type instead — three overlapping bands with air
 * between — and the paintings read at 53.4%. THE GUARANTEE NARROWS WITH IT:
 * white type is safe over the paintings the library ships, not over any
 * painting anyone might add. So the real measurement moved to
 * `CoverAssetTests.test_every_painting_still_carries_white_type`, which
 * composites all 38 committed paintings through the curve and measures the ink.
 * Python owns that because Pillow is there and it costs under a second; it is
 * no longer the tautology this file's header used to call it.
 *
 * What is left here is the join. The curve lives in `covers.py` as a cosine;
 * CSS has no cosine, so `cover-type.css` SAMPLES it into stops. Two spellings
 * of one shape, and nothing but this compares them — lighten the stylesheet and
 * the Python gate goes on measuring a curve that is no longer what ships.
 *
 * `coverBand.test.ts` is the neighbouring check: that one pins the geometry the
 * two renderers share, this one pins the scrim they both draw through.
 *
 * The curve here is the shape at FULL strength. How far it is scaled for one
 * painting is `coverScrim.ts`, checked by `coverScrim.test.ts` against the
 * Python table it is generated from — and that table is re-measured against the
 * artwork itself by `CoverAssetTests`. Shape here, strength there, artwork in
 * Python: each held where it can actually be derived.
 */
const COVER_CSS = readFileSync(join(process.cwd(), 'src/lib/components/cover-type.css'), 'utf-8');
const COVERS_PY = readFileSync(
	resolve(process.cwd(), '..', 'backend', 'library', 'covers.py'),
	'utf-8'
);

/** The scrim curve, read out of `covers.py` — bands, floor, strength, ceiling. */
function pythonCurve(subtitle = false) {
	const num = (name: string) => {
		const m = new RegExp(`^${name} = ([\\d.]+)`, 'm').exec(COVERS_PY);
		expect(m, `covers.py no longer declares ${name}`).not.toBeNull();
		return Number(m![1]);
	};
	// The first three tuples are `_SCRIM_BANDS`; the fourth is `_SUBTITLE_BAND`,
	// which only a cover that draws a subtitle wears. Sliced explicitly rather
	// than relying on order alone being obvious — it was `slice(0, 3)` with no
	// fourth band to exclude, and a reader could not tell whether that was a
	// bound or a leftover.
	const bands = [...COVERS_PY.matchAll(/\((0\.\d+), (0\.\d+), (0\.\d+)\)/g)]
		.map(([, c, h, p]) => [Number(c), Number(h), Number(p)] as [number, number, number]);
	expect(bands.length, 'covers.py no longer declares four scrim bands').toBe(4);
	const floor = num('_SCRIM_FLOOR'), strength = num('_SCRIM_STRENGTH'), ceiling = num('_SCRIM_CEILING');
	return (f: number) => {
		let a = floor;
		for (const [centre, half, peak] of bands.slice(0, subtitle ? 4 : 3)) {
			const d = Math.abs(f - centre) / half;
			if (d < 1) a = Math.max(a, floor + (peak - floor) * (0.5 + 0.5 * Math.cos(Math.PI * d)));
		}
		return Math.min(ceiling, strength * a);
	};
}

/** The scrim as the stylesheet spells it: sampled stops. */
function cssStops(subtitle = false): Array<[number, number]> {
	// `::before`, because the scrim moved onto a pseudo-element so one painting's
	// can be lighter than another's — `opacity: var(--scrim-strength)` scales the
	// whole layer, which a gradient cannot do from a custom property.
	const selector = subtitle
		? /\.cover-plate\.over-art\.has-subtitle::before \{([\s\S]*?)\n\}/
		: /\n\.cover-plate\.over-art::before \{([\s\S]*?)\n\}/;
	const block = selector.exec(COVER_CSS);
	expect(block, `the ${subtitle ? 'has-subtitle ' : ''}scrim rule is gone from cover-type.css`)
		.not.toBeNull();
	const stops = [...block![1].matchAll(/rgb\(0 0 0 \/ ([\d.]+)\)\s+([\d.]+)%/g)].map(
		([, alpha, pos]) => [Number(pos) / 100, Number(alpha)] as [number, number]
	);
	expect(stops.length, 'no gradient stops found in the scrim').toBeGreaterThan(20);
	return stops;
}

describe('the scrim over a painting', () => {
	it('is the same curve in the stylesheet and in covers.py', () => {
		// The deviation that matters is not "did someone edit the CSS" but "does
		// the CSS still describe the curve the Python gate measures". Sampling
		// every 2.5% keeps this under 0.02; a 5% sampling missed by 0.048, which
		// is enough to cost a painting its contrast.
		// BOTH SPELLINGS, because there are two gradients now: the three-band
		// curve, and the four-band one a cover with a subtitle wears. The second
		// is the one that was missing entirely — the subtitle sat far down the
		// title band's cosine at alpha 0.29, and 36 of 38 paintings measured
		// under 4.5:1 beneath it.
		for (const subtitle of [false, true]) {
			const curve = pythonCurve(subtitle);
			let worst = 0, at = 0;
			for (const [pos, alpha] of cssStops(subtitle)) {
				const d = Math.abs(alpha - curve(pos));
				if (d > worst) { worst = d; at = pos; }
			}
			expect(
				worst,
				`the stylesheet's ${subtitle ? 'has-subtitle ' : ''}scrim has drifted from ` +
					`covers.py's curve by ${worst.toFixed(3)} alpha at ${(at * 100).toFixed(0)}% — ` +
					`the fixture gate is measuring a scrim that is not the one shipping`
			).toBeLessThan(0.02);
		}
	});

	it('darkens the subtitle strip only on covers that draw one', () => {
		// The whole reason the fourth band is conditional: 18 of the 38 works
		// have no subtitle, and darkening a strip of their photography to protect
		// words that are not there is the even-wash thinking the shaped scrim
		// replaced. Applied to all of them it also made three paintings
		// unsatisfiable at any strength the curve can reach.
		const near = (stops: Array<[number, number]>, f: number) =>
			stops.reduce((b, s) => (Math.abs(s[0] - f) < Math.abs(b[0] - f) ? s : b))[1];
		const plain = cssStops(false);
		const withSub = cssStops(true);
		expect(
			near(withSub, 0.66),
			'the has-subtitle scrim has no peak where the subtitle sits'
		).toBeGreaterThan(near(plain, 0.66) + 0.15);
		// And identical where the subtitle is not: same curve, one extra band.
		for (const f of [0.13, 0.49, 0.91]) {
			expect(
				Math.abs(near(withSub, f) - near(plain, f)),
				`the two scrims disagree at ${f * 100}%, where the subtitle band does not reach`
			).toBeLessThan(0.02);
		}
	});

	it('keeps a peak over each of the three places type sits', () => {
		// The shape IS the feature: byline near the top, title block in the
		// middle, mark at the foot. Flatten it back into an even ramp and the
		// paintings go dark again — which is the change this replaced.
		const stops = cssStops();
		const at = (f: number) => stops.reduce((b, s) => (Math.abs(s[0] - f) < Math.abs(b[0] - f) ? s : b))[1];
		for (const [name, pos] of [['byline', 0.13], ['title', 0.49], ['mark', 0.91]] as const) {
			expect(at(pos), `the scrim has no peak over the ${name}`).toBeGreaterThan(0.55);
		}
		// And air between them, or there is no brightening at all.
		for (const gap of [0.29, 0.73]) {
			expect(at(gap), `the scrim never lifts at ${gap * 100}%`).toBeLessThan(0.35);
		}
	});

	it('never lets the scrim reach opaque', () => {
		// A stop at 1.0 would paint the photograph out entirely at that height.
		for (const subtitle of [false, true])
			for (const [pos, alpha] of cssStops(subtitle)) {
				expect(alpha, `the scrim is opaque at ${pos * 100}%`).toBeLessThan(0.9);
			}
	});
});

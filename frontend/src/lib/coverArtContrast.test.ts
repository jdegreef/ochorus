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
 * The scrim now follows the type instead — peaks over the byline and the mark,
 * and a band hung off the title block that moves with its words — and the
 * paintings read at over 70%. THE GUARANTEE NARROWS WITH IT:
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

/** The PLATE's scrim layer, read out of `covers.py` — bands, floor, strength,
 *  ceiling. Two bands: the byline and the mark, which never move. */
function pythonCurve() {
	const bands = [...COVERS_PY.matchAll(/\((0\.\d+), (0\.\d+), (0\.\d+)\)/g)]
		.map(([, c, h, p]) => [Number(c), Number(h), Number(p)] as [number, number, number]);
	expect(bands.length, 'covers.py no longer declares the byline and mark scrim bands').toBe(2);
	const num = (name: string) => {
		const m = new RegExp(`^${name} = ([\\d.]+)`, 'm').exec(COVERS_PY);
		expect(m, `covers.py no longer declares ${name}`).not.toBeNull();
		return Number(m![1]);
	};
	const floor = num('_SCRIM_FLOOR'), strength = num('_SCRIM_STRENGTH'), ceiling = num('_SCRIM_CEILING');
	return (f: number) => {
		let a = floor;
		for (const [centre, half, peak] of bands) {
			const d = Math.abs(f - centre) / half;
			if (d < 1) a = Math.max(a, floor + (peak - floor) * (0.5 + 0.5 * Math.cos(Math.PI * d)));
		}
		return Math.min(ceiling, strength * a);
	};
}

/** The scrim as the stylesheet spells it: sampled stops. */
function cssStops(): Array<[number, number]> {
	// `::before`, because the scrim moved onto a pseudo-element so one painting's
	// can be lighter than another's — `opacity: var(--scrim-strength)` scales the
	// whole layer, which a gradient cannot do from a custom property.
	const block = /\n\.cover-plate\.over-art::before \{([\s\S]*?)\n\}/.exec(COVER_CSS);
	expect(block, 'the scrim rule is gone from cover-type.css').not.toBeNull();
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
		const curve = pythonCurve();
		let worst = 0, at = 0;
		for (const [pos, alpha] of cssStops()) {
			const d = Math.abs(alpha - curve(pos));
			if (d > worst) { worst = d; at = pos; }
		}
		expect(
			worst,
			`the stylesheet's scrim has drifted from covers.py's curve by ${worst.toFixed(3)} ` +
				`alpha at ${(at * 100).toFixed(0)}% — the fixture gate is measuring a scrim ` +
				`that is not the one shipping`
		).toBeLessThan(0.02);
	});

	it('paints the band under the words, scaled like the rest, and never under a layout', () => {
		// The band hung off `.middle` is the title block's share of the scrim; its
		// STOPS are held to `covers.middle_band_stops` by `tests_covers`, which can
		// call the function. What only the stylesheet can say is where it paints:
		// above the type it would dim the title it exists to protect; unscaled it
		// would ignore the painting's measured strength; under a layout's paper it
		// would darken a composition that sets dark ink and has no scrim.
		const rule = /\n\.cover-plate\.over-art \.cover-type \.middle::after \{([\s\S]*?)\n\}/.exec(COVER_CSS)![1];
		expect(rule).toMatch(/z-index: -1;/);
		expect(rule).toMatch(/opacity: var\(--scrim-strength, 1\);/);
		expect(COVER_CSS).toMatch(/\.cover-plate\.over-art:not\(\.has-layout, \.ink-dark\) \.cover-type \.middle \{[^}]*isolation: isolate;/);
		expect(COVER_CSS).toMatch(/\.cover-plate\.over-art\.ink-dark \.cover-type \.middle::after \{\s*display: none;/);
		expect(COVER_CSS).toMatch(/\.cover-plate\.over-art\.has-layout \.cover-type \.middle::after,/);
	});

	it('keeps a peak over the byline and the mark, and air between', () => {
		// The plate's layer covers the two places type never moves from. The
		// title block's darkness comes from the band above; flatten this back into
		// an even ramp and the paintings go dark again.
		const stops = cssStops();
		const at = (f: number) => stops.reduce((b, s) => (Math.abs(s[0] - f) < Math.abs(b[0] - f) ? s : b))[1];
		for (const [name, pos] of [['byline', 0.13], ['mark', 0.91]] as const) {
			expect(at(pos), `the scrim has no peak over the ${name}`).toBeGreaterThan(0.55);
		}
		for (const gap of [0.29, 0.49, 0.73]) {
			expect(at(gap), `the plate's scrim never lifts at ${gap * 100}%`).toBeLessThan(0.35);
		}
	});

	it('never lets the scrim reach opaque', () => {
		// A stop at 1.0 would paint the photograph out entirely at that height.
		for (const [pos, alpha] of cssStops()) {
			expect(alpha, `the scrim is opaque at ${pos * 100}%`).toBeLessThan(0.9);
		}
	});
});

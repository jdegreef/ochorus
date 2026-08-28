// @vitest-environment node
//
// Reads two files and compares numbers; no DOM. See coverComposition.test.ts
// for the measurement behind that choice.
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

import { COVER_SCRIM, scrimStrength } from './coverScrim';

/**
 * One measurement, two files.
 *
 * How much scrim a painting needs is measured with Pillow, in Python, because
 * that is where the artwork can be opened — and it is needed in TypeScript,
 * because `BookCover` and the share-card script are what draw a cover.
 * `scripts/tune_art_scrim.py` writes both, so they cannot drift while anyone
 * uses the script.
 *
 * This is for when someone does not. Hand-edit either table — to lighten one
 * cover, to drop a work — and the other goes on being the one that is measured:
 * `CoverAssetTests.test_every_painting_still_carries_white_type` re-measures
 * the PYTHON table against the artwork, so a hand-edit on the TypeScript side
 * would ship a scrim nothing has ever checked.
 */
const PY = readFileSync(
	resolve(process.cwd(), '..', 'backend', 'library', 'art_scrim.py'),
	'utf-8'
);

/** The Python table, parsed out of its literal. */
const pythonTable = (): Record<string, number> => {
	const body = /ART_SCRIM: dict\[str, float\] = \{([\s\S]*?)\n\}/.exec(PY);
	expect(body, 'library/art_scrim.py no longer declares ART_SCRIM').not.toBeNull();
	return Object.fromEntries(
		[...body![1].matchAll(/"([^"]+)":\s*([\d.]+),/g)].map(([, slug, k]) => [slug, Number(k)])
	);
};

describe('the scrim strength table', () => {
	it('says the same thing in Python and TypeScript', () => {
		const py = pythonTable();
		expect(Object.keys(py).length, 'the Python table is empty').toBeGreaterThan(30);
		expect(
			COVER_SCRIM,
			'coverScrim.ts and library/art_scrim.py disagree — re-run ' +
				'`cd backend && uv run python scripts/tune_art_scrim.py`, which writes both'
		).toEqual(py);
	});

	it('never scales a scrim past the strength it was measured against', () => {
		// The shape in `cover-type.css` is sampled at a strength of 1, and the
		// stops are clamped at 0.88 alpha. A value above 1 would ask for a scrim
		// the stylesheet cannot draw, so it would silently do nothing at the peaks
		// — the one place it was supposed to matter.
		for (const [slug, k] of Object.entries(COVER_SCRIM)) {
			expect(k, `${slug} asks for more scrim than the curve can give`).toBeLessThanOrEqual(1);
			expect(k, `${slug} asks for no scrim at all`).toBeGreaterThan(0);
		}
	});

	it('gives an unmeasured painting the full scrim', () => {
		// A work added without re-running the tuner must not come out LIGHTER than
		// what was checked. Falling back to 1 means it wears exactly the scrim
		// every painting wore before this table existed, which is the safe end.
		expect(scrimStrength('a-work-nobody-has-measured')).toBe(1);
		const [known] = Object.keys(COVER_SCRIM);
		expect(scrimStrength(known)).toBe(COVER_SCRIM[known]);
	});
});

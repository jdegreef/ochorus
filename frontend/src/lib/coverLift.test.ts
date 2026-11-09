// @vitest-environment node
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

import { COVER_LIFT, groundLift } from './coverLift';

/**
 * How far a dark painting is brightened is measured in Python
 * (`covers.ground_lift`, written by `scripts/tune_art_scrim.py`) and drawn by
 * TypeScript (`BookCover`, the share-card script). Like the scrim strengths
 * (`coverScrim.test.ts`), the two tables must say the same thing, because only
 * the Python one is re-measured against the artwork (`CoverAssetTests`).
 */
const PY = readFileSync(resolve(process.cwd(), '..', 'backend', 'library', 'art_lift.py'), 'utf-8');
const COVERS_PY = readFileSync(resolve(process.cwd(), '..', 'backend', 'library', 'covers.py'), 'utf-8');

const pythonTable = (): Record<string, number> => {
	const body = /ART_LIFT: dict\[str, float\] = \{([\s\S]*?)\n\}/.exec(PY);
	expect(body, 'library/art_lift.py no longer declares ART_LIFT').not.toBeNull();
	return Object.fromEntries(
		[...body![1].matchAll(/"([^"]+)":\s*([\d.]+),/g)].map(([, slug, k]) => [slug, Number(k)])
	);
};

describe('the brightness lift table', () => {
	it('says the same thing in Python and TypeScript', () => {
		expect(
			COVER_LIFT,
			'coverLift.ts and library/art_lift.py disagree — re-run ' +
				'`cd backend && uv run python scripts/tune_art_scrim.py`, which writes both'
		).toEqual(pythonTable());
	});

	it('only ever brightens, and never past the cap', () => {
		const max = Number(/^LIFT_MAX = ([\d.]+)/m.exec(COVERS_PY)?.[1]);
		expect(max).toBeGreaterThan(1);
		for (const [slug, k] of Object.entries(COVER_LIFT)) {
			expect(k, `${slug} is darkened`).toBeGreaterThan(1);
			expect(k, `${slug} is lifted past LIFT_MAX`).toBeLessThanOrEqual(max);
		}
		expect(groundLift('no-such-painting')).toBe(1);
	});
});

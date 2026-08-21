import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';

import { authorInkContrast, inkSafe } from './coverArt';

/**
 * The legibility floor exists twice, and must never diverge.
 *
 * `backend/library/covers.py` floors a plate colour when it DRAWS the committed
 * SVG; `coverArt.ts` floors it when the client draws the fallback for a book
 * whose file hasn't loaded. Both must land on the same colour, or a cover
 * visibly changes shade the moment its image arrives.
 *
 * Two guards, because they fail for different reasons. The constants check
 * catches a backend edit that never reached the mirror. The golden table
 * catches a mirror whose arithmetic drifted — Python truncates where JS rounds,
 * and the ladder is walked in integer steps precisely so the two agree; a
 * one-step difference is invisible in review and obvious on a shelf.
 *
 * If the constants test fails, copy the values from covers.py; the backend is
 * canonical (it draws what actually ships). If the golden test fails, run the
 * backend's `ink_safe` over the inputs below and paste the results.
 */
const COVERS_PY = join(process.cwd(), '..', 'backend', 'library', 'covers.py');

const pyConstant = (name: string): number => {
	const source = readFileSync(COVERS_PY, 'utf-8');
	const match = source.match(new RegExp(`^${name} = ([\\d.]+)$`, 'm'));
	if (!match) throw new Error(`${name} not found in covers.py — was it renamed?`);
	return Number(match[1]);
};

describe('the ink floor matches the backend', () => {
	it.each([
		['AUTHOR_INK_OPACITY', 0.86],
		['AUTHOR_MIN_CONTRAST', 4.5],
		['_GRADIENT_END', 0.55],
		['_AUTHOR_GRADIENT_T', 0.28]
	])('%s is still %s in covers.py', (name, mirrored) => {
		expect(pyConstant(name)).toBe(mirrored);
	});

	// Produced by backend `ink_safe`. The first five are the library's failing
	// plates, then two that already pass (and must come back untouched), then
	// white, which needs the deepest walk down the ladder.
	it.each([
		['#ca8d21', '#a1701a'],
		['#4996a2', '#3f828c'],
		['#2f9e44', '#28893b'],
		['#987952', '#91744e'],
		['#987652', '#947350'],
		['#3b5bdb', '#3b5bdb'],
		['#7a5c48', '#7a5c48'],
		['#ffffff', '#777777']
	])('inkSafe(%s) === %s, as Python computes it', (input, expected) => {
		expect(inkSafe(input)).toBe(expected);
	});

	it.each([['#ca8d21'], ['#4996a2'], ['#2f9e44'], ['#987952'], ['#987652'], ['#ffffff']])(
		'%s clears AA once floored',
		(color) => {
			expect(authorInkContrast(inkSafe(color))).toBeGreaterThanOrEqual(4.5);
		}
	);

	it('falls back to the house blue for a blank or malformed colour', () => {
		expect(inkSafe('')).toBe('#3b5bdb');
		expect(inkSafe(null)).toBe('#3b5bdb');
		expect(inkSafe('#zzz')).toBe('#3b5bdb');
	});
});

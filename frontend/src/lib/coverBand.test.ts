import { readFileSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { describe, expect, it } from 'vitest';

/**
 * The one seam where the two halves of a cover have to agree on a number.
 *
 * A cover is drawn twice over, by design: `covers.py` draws the ground — the
 * colour, the vignette, and the topic emblem — and `BookCover` draws the type
 * over it. Neither measures the other (it could not: one is an SVG written
 * offline, the other is CSS wrapping text in a browser), so the emblem is put
 * at a FIXED band and the type reserves the same band with `.emblem-band`.
 *
 * That works exactly as long as the two bands are the same band. Nothing at
 * runtime checks it, and getting it wrong is invisible in every test either
 * side can run alone: the emblem would simply sit under the lockup, or the
 * subtitle would sit on the emblem, on 105 committed plates, with both suites
 * green. The Python side used to "pin" this by asserting its own constant
 * against the same arithmetic that defined it, which proves nothing.
 *
 * So this reads the real numbers from both files. Python is canonical — it is
 * the side that has already drawn 105 files at those coordinates — and the CSS
 * is checked against it.
 *
 * The conversion is the whole trick: the plate is `W = 600` units wide and
 * `.cover-plate` is the container those `cqw` are measured against, so one cqw
 * is six plate units, exactly.
 */
const BACKEND = resolve(process.cwd(), '..', 'backend');
const COVERS_PY = readFileSync(join(BACKEND, 'library', 'covers.py'), 'utf-8');
const COVER_CSS = readFileSync(join(process.cwd(), 'src/lib/components/cover-type.css'), 'utf-8');
const BOOK_COVER = readFileSync(
	join(process.cwd(), 'src/lib/components/BookCover.svelte'),
	'utf-8'
);

/** A `NAME = 123` constant from covers.py. */
const pyConst = (name: string): number => {
	const found = new RegExp(`^${name} = (\\d+)`, 'm').exec(COVERS_PY);
	expect(found, `covers.py no longer defines ${name}`).not.toBeNull();
	return Number(found![1]);
};

/** Plate units per container-query unit — `W / 100`. `W` is declared with `H`
 *  on one line, so it is read on its own rather than through `pyConst`. */
const PLATE_WIDTH = (() => {
	const found = /^W, H = (\d+), (\d+)/m.exec(COVERS_PY);
	expect(found, 'covers.py no longer declares the plate canvas as `W, H = w, h`').not.toBeNull();
	return Number(found![1]);
})();
const UNITS_PER_CQW = PLATE_WIDTH / 100;

describe('the emblem band is the same band on both sides', () => {
	it('reserves the drawing the same width the ground draws it at', () => {
		const css = /\.cover-type \.emblem-band \{[^}]*height:\s*([\d.]+)cqw/.exec(COVER_CSS);
		expect(css, '.emblem-band no longer sets a height').not.toBeNull();
		expect(Number(css![1]) * UNITS_PER_CQW).toBe(pyConst('_EMBLEM_W'));
	});

	it('leaves the same gap under it', () => {
		const css = /\.cover-type \.emblem-band \{[^}]*margin-bottom:\s*([\d.]+)cqw/.exec(COVER_CSS);
		expect(css, '.emblem-band no longer sets a bottom margin').not.toBeNull();
		expect(Number(css![1]) * UNITS_PER_CQW).toBe(pyConst('_EMBLEM_GAP'));
	});

	it('puts the foot of the plate where covers.py thinks it is', () => {
		// The band is measured up from the bottom of the plate, past the mark and
		// the padding under it, so both of those have to match too — they are
		// what `_EMBLEM_BOTTOM` is derived from.
		const pad = /\.cover-type \{[^}]*padding:[^;]*\s([\d.]+)cqw;/.exec(COVER_CSS);
		expect(pad, '.cover-type no longer sets padding').not.toBeNull();
		expect(Number(pad![1]) * UNITS_PER_CQW).toBe(pyConst('_FOOT_PAD'));

		const mark = /<BrandMark height="([\d.]+)cqw"/.exec(BOOK_COVER);
		expect(mark, 'BookCover no longer sizes the mark in cqw').not.toBeNull();
		// Rounded, because covers.py works in whole plate units and 13.7cqw is
		// 82.2 of them.
		expect(Math.round(Number(mark![1]) * UNITS_PER_CQW)).toBe(pyConst('_MARK_H'));
	});
});

import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';

import { channels, contrastRatio as contrast, isArtCover } from './coverArt';
import {
	BOOK_LAYOUT,
	COVER_HUE_IDS,
	COVER_LAYOUT_IDS,
	coverLayoutFor,
	layoutKey
} from './coverLayouts';
import { COVER_CSS_CODE, blocksFor, lastDecl } from '../test/coverCss';

/**
 * The layout table against the stylesheet that draws it, and the colours it
 * draws in against contrast.
 *
 * A painted cover in the framed composition gets its legibility from a
 * measured scrim (`coverArtContrast.test.ts`). A layout gets it from PAPER, so
 * what has to hold is the paper: the ink on it, the band-coloured byline on it,
 * and — for the two layouts whose paper lets the painting through — the paper
 * at its thinnest, over the darkest painting there could be.
 */

type Rgb = [number, number, number];

/** `a` over `b` at `alpha`, composited in sRGB as a browser does. */
const over = (a: Rgb, b: Rgb, alpha: number): Rgb =>
	a.map((c, i) => c * alpha + b[i] * (1 - alpha)) as Rgb;

const BLACK: Rgb = [0, 0, 0];
const WHITE: Rgb = [255, 255, 255];

function hue(id: string): { band: Rgb; paper: Rgb; ink: Rgb } {
	const get = (prop: string) => {
		const v = lastDecl(`.hue-${id}`, new RegExp(`${prop}:\\s*(#[0-9a-f]{6})`));
		expect(v, `.hue-${id} declares no ${prop}`).not.toBeNull();
		return channels(v!);
	};
	return { band: get('--c-band'), paper: get('--c-paper'), ink: get('--c-ink') };
}

/** A number out of one layout's `::before` block. */
function number(selector: string, pattern: RegExp): number {
	const v = lastDecl(selector, pattern);
	expect(v, `${selector} lost ${pattern}`).not.toBeNull();
	return Number(v);
}

describe('the layout table and the stylesheet name the same things', () => {
	it('draws every layout it names, and names every layout it draws', () => {
		const drawn = new Set([...COVER_CSS_CODE.matchAll(/\.layout-([a-z]+)/g)].map((m) => m[1]));
		expect([...drawn].sort()).toEqual([...COVER_LAYOUT_IDS].sort());
	});

	it('draws every hue it names, and names every hue it draws', () => {
		const drawn = new Set([...COVER_CSS_CODE.matchAll(/\.hue-([a-z]+)\s*\{/g)].map((m) => m[1]));
		expect([...drawn].sort()).toEqual([...COVER_HUE_IDS].sort());
	});

	it('gives a layout only to a work whose English edition wears a painting', () => {
		const books = join(process.cwd(), '..', 'backend', 'library', 'fixtures', 'content', 'books');
		const offenders = Object.keys(BOOK_LAYOUT).filter((slug) => {
			let cover = '';
			try {
				cover = JSON.parse(readFileSync(join(books, `${slug}.en.json`), 'utf8')).find(
					(r: { model: string }) => r.model === 'library.book'
				).fields.cover_url;
			} catch {
				return true;
			}
			return !isArtCover(cover);
		});
		expect(
			offenders,
			'a layout is drawn only over a painting — a designed cover has its words in ' +
				'its pixels, and a plate is composed around its emblem'
		).toEqual([]);
	});
});

describe('coverLayoutFor', () => {
	it('leaves a work outside the table framed', () => {
		expect(coverLayoutFor('no-such-book', null)).toBeNull();
		expect(layoutKey(null)).toBe('framed');
	});

	it('gives a non-latin edition of a railed work the title box, in its colour', () => {
		const railed = Object.keys(BOOK_LAYOUT).find((s) => BOOK_LAYOUT[s].layout === 'rail')!;
		expect(coverLayoutFor(railed, null)?.layout).toBe('rail');
		expect(coverLayoutFor(railed, 'arabic')).toEqual({
			layout: 'box',
			hue: BOOK_LAYOUT[railed].hue
		});
		expect(coverLayoutFor(railed, 'cyrillic')?.layout).toBe('rail');
	});
});

describe('every hue carries its type', () => {
	for (const id of COVER_HUE_IDS) {
		it(`${id}: ink and byline on paper, and the mark on the band`, () => {
			const { band, paper, ink } = hue(id);
			expect(contrast(ink, paper), 'the title ink on paper').toBeGreaterThanOrEqual(7);
			expect(contrast(band, paper), 'the band-coloured byline on paper').toBeGreaterThanOrEqual(4.5);
			expect(contrast(WHITE, band), 'the white mark on the band').toBeGreaterThanOrEqual(4.5);
		});
	}
});

describe('the translucent papers hold at their thinnest', () => {
	it('wash: the title and byline, over a black painting', () => {
		// The title block ends before the 55% stop, so that stop is the thinnest
		// paper it sits on; the byline sits above the 30% stop.
		const block = blocksFor('.cover-plate.over-art.layout-wash::before')[0][1];
		const alphas = [...block.matchAll(/var\(--c-paper\)\s+(\d+)%/g)].map((m) => Number(m[1]) / 100);
		expect(alphas.length).toBe(4);
		for (const id of COVER_HUE_IDS) {
			const { band, paper, ink } = hue(id);
			expect(contrast(ink, over(paper, BLACK, alphas[2])), `${id} title`).toBeGreaterThanOrEqual(4.5);
			expect(contrast(band, over(paper, BLACK, alphas[1])), `${id} byline`).toBeGreaterThanOrEqual(3);
		}
	});

	it('duotone: the ink, over the print at its darkest', () => {
		const sel = '.cover-plate.over-art.layout-duotone::before';
		const tint = number(sel, /var\(--c-band\)\s+(\d+)%/) / 100;
		const alpha = number(sel, /opacity:\s*([\d.]+)/);
		const ground = '.cover-ground:has(~ .cover-plate.layout-duotone)';
		const flat = number(ground, /contrast\(([\d.]+)\)/);
		const lift = number(ground, /brightness\(([\d.]+)\)/);
		// The darkest a greyscale print gets once `contrast()` and `brightness()`
		// have flattened it: black, pulled toward mid-grey, then lifted.
		const floor = ((0 - 0.5) * flat + 0.5) * lift * 255;
		for (const id of COVER_HUE_IDS) {
			const { band, paper, ink } = hue(id);
			const wash = over(band, paper, tint);
			const darkest = over(wash, [floor, floor, floor], alpha);
			expect(contrast(ink, darkest), id).toBeGreaterThanOrEqual(4.5);
		}
	});
});

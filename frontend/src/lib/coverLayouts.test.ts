import { readFileSync, readdirSync } from 'node:fs';
import { join } from 'node:path';
import { describe, expect, it } from 'vitest';

import { channels, contrastRatio as contrast, isArtCover } from './coverArt';
import {
	AUTHOR_LAYOUT,
	BOOK_LAYOUT,
	COVER_HUE_IDS,
	TYPE_TOP,
	COVER_LAYOUT_IDS,
	coverLayoutFor,
	layoutKey
} from './coverLayouts';
import { BOOK_STYLE } from './coverStyles';
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
		const v = lastDecl(`.cover-hue-${id}`, new RegExp(`${prop}:\\s*(#[0-9a-f]{6})`));
		expect(v, `.cover-hue-${id} declares no ${prop}`).not.toBeNull();
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

type BookRow = {
	slug: string;
	title: string;
	language: string;
	author: string[];
	cover_url?: string;
	series?: string[] | null;
};

const BOOKS = join(process.cwd(), '..', 'backend', 'library', 'fixtures', 'content', 'books');

/** Every edition's book row in the shipped fixture. */
const allBooks = (): BookRow[] =>
	readdirSync(BOOKS)
		.filter((f) => f.endsWith('.json'))
		.flatMap((f) => JSON.parse(readFileSync(join(BOOKS, f), 'utf8')))
		.filter((r: { model: string }) => r.model === 'library.book')
		.map((r: { fields: BookRow }) => r.fields);

const englishBooks = () => allBooks().filter((b) => b.language === 'en');

describe('the layout table and the stylesheet name the same things', () => {
	it('draws every layout it names, and names every layout it draws', () => {
		const drawn = new Set([...COVER_CSS_CODE.matchAll(/\.cover-layout-([a-z]+)/g)].map((m) => m[1]));
		expect([...drawn].sort()).toEqual([...COVER_LAYOUT_IDS].sort());
	});

	it('draws every hue it names, and names every hue it draws', () => {
		const drawn = new Set([...COVER_CSS_CODE.matchAll(/\.cover-hue-([a-z]+)\s*\{/g)].map((m) => m[1]));
		expect([...drawn].sort()).toEqual([...COVER_HUE_IDS].sort());
	});

	it('gives a layout only to an author with a painted book in English', () => {
		const painted = new Set(
			englishBooks()
				.filter((b) => isArtCover(b.cover_url))
				.map((b) => b.author[0])
		);
		expect(
			Object.keys(AUTHOR_LAYOUT).filter((author) => !painted.has(author)),
			'a layout is drawn only over a painting — this author has none, so the ' +
				'entry changes nothing'
		).toEqual([]);
	});
});

describe('coverLayoutFor', () => {
	it('leaves an author outside the table framed', () => {
		expect(coverLayoutFor('no-such-author', null, 'no-such-book')).toBeNull();
		expect(layoutKey(null)).toBe('framed');
	});

	it('gives a non-latin edition of a railed work the title box, in its colour', () => {
		const railed = Object.keys(AUTHOR_LAYOUT).find((a) => AUTHOR_LAYOUT[a].layout === 'rail')!;
		expect(coverLayoutFor(railed, null, 'a-railed-book')?.layout).toBe('rail');
		expect(coverLayoutFor(railed, 'arabic', 'a-railed-book')).toEqual({
			layout: 'box',
			hue: AUTHOR_LAYOUT[railed].hue
		});
		expect(coverLayoutFor(railed, 'cyrillic', 'a-railed-book')?.layout).toBe('rail');
	});

	it('lets a series hold its books framed over their authors\' layouts', () => {
		// Baxter's own layout is the paper box; his Key Teachings volume is framed.
		expect(AUTHOR_LAYOUT['richard-baxter']).toBeTruthy();
		expect(coverLayoutFor('richard-baxter', null, 'key-teachings-of-richard-baxter')).toBeNull();
		expect(coverLayoutFor('richard-baxter', null, 'the-reformed-pastor')).toEqual(
			AUTHOR_LAYOUT['richard-baxter']
		);
	});
});

describe('the Key Teachings wear one series look', () => {
	// Keyed by book in two tables, so a new volume must be added to both — or it
	// silently takes its author's layout and century, which is how the first four
	// came out in three layouts and three faces.
	const volumes = [
		...new Set(
			allBooks()
				.filter((b) => b.series?.[0] === 'key-teachings')
				.map((b) => b.slug)
		)
	];

	it('finds the series in the fixture', () => {
		expect(volumes.length).toBeGreaterThan(0);
	});

	it.each(volumes)('%s is framed, set from the top, in the imprint face', (slug) => {
		expect(slug in BOOK_LAYOUT, `${slug}: add it to coverLayouts.BOOK_LAYOUT`).toBe(true);
		expect(BOOK_LAYOUT[slug]).toBeNull();
		expect(BOOK_STYLE[slug], `${slug}: add it to coverStyles.BOOK_STYLE`).toBe('originals');
		// Framed with the words above the tree, not centred on it.
		expect(TYPE_TOP.has(slug), `${slug}: add it to coverLayouts.TYPE_TOP`).toBe(true);
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
		// The paper's alpha at each stop, keyed by the stop's position. The title
		// block ends before the 55% stop, so that is the thinnest paper it sits
		// on; the byline sits above the 30% stop.
		const block = blocksFor('.cover-plate.over-art.cover-layout-wash::before')[0][1];
		const stops = new Map(
			[...block.matchAll(/var\(--c-paper\)\s+(\d+)%,\s*transparent\)\s+(\d+)%/g)].map((m) => [
				Number(m[2]),
				Number(m[1]) / 100
			])
		);
		expect(stops.has(30) && stops.has(55), 'the wash lost its 30% or 55% stop').toBe(true);
		for (const id of COVER_HUE_IDS) {
			const { band, paper, ink } = hue(id);
			const title = contrast(ink, over(paper, BLACK, stops.get(55)!));
			const byline = contrast(band, over(paper, BLACK, stops.get(30)!));
			expect(title, `${id} title`).toBeGreaterThanOrEqual(4.5);
			expect(byline, `${id} byline`).toBeGreaterThanOrEqual(4.5);
		}
	});

	it('duotone: white type, over the print at its brightest', () => {
		const sel = '.cover-plate.over-art.cover-layout-duotone::before';
		const ink = number(sel, /var\(--c-ink\)\s+(\d+)%/) / 100;
		const alpha = number(sel, /opacity:\s*([\d.]+)/);
		const ground = '.cover-ground:has(~ .cover-plate.cover-layout-duotone)';
		const flat = number(ground, /contrast\(([\d.]+)\)/);
		const lift = number(ground, /brightness\(([\d.]+)\)/);
		// The brightest a greyscale print gets once `contrast()` and
		// `brightness()` have flattened it: white, pulled toward mid-grey, then
		// dimmed.
		const top = ((1 - 0.5) * flat + 0.5) * lift * 255;
		for (const color of ['.byline', '.brandmark']) {
			expect(
				lastDecl(`.cover-plate.over-art.cover-layout-duotone .cover-type ${color}`, /color:\s*([^;]+)/),
				`the duotone ${color} is set in white`
			).toBe('#fff');
		}
		for (const id of COVER_HUE_IDS) {
			const { band, ink: inkColour } = hue(id);
			const tint = over(inkColour, band, ink);
			const brightest = over(tint, [top, top, top], alpha);
			expect(contrast(WHITE, brightest), id).toBeGreaterThanOrEqual(4.5);
		}
	});
});

describe('the rail', () => {
	it('is given only authors whose titles are short enough to run up it', () => {
		// The rail sets its title sideways in a 23cqw column, which holds two
		// lines of it. A longer title wraps into a third that spills over the
		// band onto the painting, so an author with one wants another layout.
		const long = allBooks()
			.filter((b) => AUTHOR_LAYOUT[b.author[0]]?.layout === 'rail' && isArtCover(b.cover_url))
			.map((b) => b.title)
			.filter((title) => title.length > 28);
		expect(long).toEqual([]);
	});
});

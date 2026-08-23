import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { mount, unmount } from 'svelte';
import { afterEach, describe, expect, it } from 'vitest';

import BookCover from './BookCover.svelte';
import type { BookSummary } from '$lib/library';

/**
 * The cover's type is drawn HERE, over whatever ground the book has, and these
 * are the rules that keep it the only drawing of it.
 *
 * There used to be two: `covers.py` composited the words into the plate file,
 * and this component had a hand-built SVG replica of that plate for a book with
 * no file. The two drifted in every dimension that could drift — type ramp,
 * wrap budget, line height, title centre, rule offset, gradient angle, the
 * missing vignette — and, worse, the replica had no RTL, no per-script fonts and
 * no script scaling, so an Arabic book's fallback came out in Georgia set
 * left-to-right.
 *
 * The words left the file, which is also what let a cover be set in a real face
 * (an `<img>`-rendered SVG cannot reach the page's webfonts, so every generated
 * cover in the library was Georgia). So these assert the properties that made
 * the replica wrong, not pixels: the title is real text the browser can shape
 * and wrap, it is set in its author's house style, and no second copy of the
 * generator's metrics decides how it is set.
 */
const book = (over: Partial<BookSummary> = {}): BookSummary =>
	({
	slug: 'waiting-on-god',
	title: 'Waiting on God',
	subtitle: '',
	author: { slug: 'andrew-murray', name: 'Andrew Murray', birth_year: 1828 },
	cover_url: '',
	cover_color: '#1864ab',
	chapter_count: 31,
	word_count: 20000,
	language: 'en',
		source_type: 'public_domain',
		...over
	}) as BookSummary;

let target: HTMLElement;
let component: Record<string, unknown> | undefined;

const render = (props: { book: BookSummary; priority?: boolean }): HTMLElement => {
	teardown(); // a test that renders twice must not leave the first in the body
	target = document.createElement('div');
	document.body.appendChild(target);
	component = mount(BookCover, { target, props }) as Record<string, unknown>;
	return target;
};

const teardown = () => {
	if (component) unmount(component);
	target?.remove();
	component = undefined;
};

afterEach(teardown);

describe('BookCover falls back to a plate', () => {
	it('sets the title as text, not as pre-wrapped SVG lines', () => {
		const el = render({ book: book() });
		expect(el.querySelector('.title')?.textContent).toBe('Waiting on God');
		// A <tspan> would mean someone reintroduced the generator's wrap budget —
		// which cannot know where a Devanagari or Arabic line should break.
		expect(el.querySelector('tspan')).toBeNull();
		// Same path for a non-Latin title: handed to the browser whole, for it to
		// shape and break, rather than pre-split at a character count.
		const arabic = render({ book: book({ title: 'الانتظار أمام الله' }) });
		expect(arabic.querySelector('.title')?.textContent).toBe('الانتظار أمام الله');
	});

	it("paints the book's own colour, falling to a darker tone of itself", () => {
		const el = render({ book: book({ cover_color: '#0b7285' }) });
		// The gradient goes in as a custom property, which the browser stores
		// verbatim (a plain `background` would come back normalised to rgb()).
		const style = el.querySelector('.cover-plate')?.getAttribute('style') ?? '';
		expect(style).toContain('#0b7285'); // the book's own colour
		expect(style).toContain('#063f49'); // shaded to 0.55, as the file's stop is
	});

	it('names the cover once for a screen reader, and hides the decorative type', () => {
		// role="img" makes the plate a leaf, so the title inside is not announced
		// a second time after the label.
		const plate = render({ book: book() }).querySelector('.cover-plate');
		expect(plate?.getAttribute('role')).toBe('img');
		expect(plate?.getAttribute('aria-label')).toContain('Waiting on God');
	});

	it('draws the type over a shared painting, and asks for its webp variants', () => {
		// `covers/art/` is a painting with no words in it — one file for every
		// language, with this edition's title drawn over it here. The <img> is
		// then decorative: the plate carries the accessible name.
		const el = render({ book: book({ cover_url: '/covers/art/waiting-on-god.jpg' }) });
		const img = el.querySelector('img');
		expect(img?.getAttribute('alt')).toBe('');
		// The descriptor format is pinned in coverArt.test.ts; here we only care
		// that the component asks for the variants at all.
		expect(img?.getAttribute('srcset')).toContain('/covers/art/waiting-on-god-320.webp');
		expect(el.querySelector('.cover-plate.over-art')).not.toBeNull();
		expect(el.querySelector('.title')?.textContent).toBe('Waiting on God');
	});

	it('asks for variants of a designed cover, and none of an svg', () => {
		const raster = render({ book: book({ cover_url: '/covers/humility-2.jpg' }) });
		expect(raster.querySelector('img')?.getAttribute('srcset')).toContain(
			'/covers/humility-2-320.webp'
		);
		// A generated plate is already a few KB of vector — there is nothing to
		// resize, and a srcset would point at files nobody builds.
		const svg = render({ book: book({ cover_url: '/covers/all-of-grace.svg' }) });
		expect(svg.querySelector('img')?.hasAttribute('srcset')).toBe(false);
	});

	it('draws the type over a plate ground too, and reserves the emblem band', () => {
		// A committed `.svg` is a GROUND — colour, vignette, emblem, no words —
		// so it gets the same treatment as a painting. It used to arrive with its
		// title already in it, and this component drew nothing over it.
		const el = render({ book: book({ cover_url: '/covers/waiting-on-god.svg' }) });
		expect(el.querySelector('img')?.getAttribute('src')).toBe('/covers/waiting-on-god.svg');
		expect(el.querySelector('.cover-plate.over-file')).not.toBeNull();
		expect(el.querySelector('.title')?.textContent).toBe('Waiting on God');
		// The emblem is drawn INTO the ground by covers.py, at a fixed band; this
		// is what keeps the type off it.
		expect(el.querySelector('.emblem-band')).not.toBeNull();
	});

	it('leaves the emblem band out where there is no emblem under it', () => {
		// A painting has none, and neither has the CSS plate a book with no file
		// at all falls back to. Reserving the room anyway would push their titles
		// up the cover for nothing.
		const painting = render({ book: book({ cover_url: '/covers/art/waiting-on-god.jpg' }) });
		expect(painting.querySelector('.emblem-band')).toBeNull();
		expect(render({ book: book() }).querySelector('.emblem-band')).toBeNull();
	});

	it('leaves a DESIGNED raster alone — its words are already in the file', () => {
		// The one tier that must not get type over it: `/covers/<slug>.jpg` is a
		// finished cover, and a second title over it would be a mess.
		const el = render({ book: book({ cover_url: '/covers/humility-2.jpg' }) });
		expect(el.querySelector('.cover-plate')).toBeNull();
		expect(el.querySelector('img')?.getAttribute('alt')).toContain('Waiting on God');
	});
});

describe("the title wears its author's house style", () => {
	/**
	 * The table lives in `coverStyles.ts` and the recipes in `cover-type.css`;
	 * both are tested there. What is checked here is that the decision REACHES
	 * the markup — a style resolved and then not put on the element leaves every
	 * cover in the house serif, which is exactly the sameness the table exists to
	 * end, and looks like nothing at all went wrong.
	 */
	const styleOf = (author: { slug: string; name: string; birth_year: number | null }) =>
		render({ book: book({ author } as Partial<BookSummary>) })
			.querySelector('.cover-type')
			?.className ?? '';

	it('sets a devotional writer and a Victorian one in different faces', () => {
		const murray = styleOf({ slug: 'andrew-murray', name: 'Andrew Murray', birth_year: 1828 });
		const spurgeon = styleOf({
			slug: 'charles-h-spurgeon',
			name: 'Charles H. Spurgeon',
			birth_year: 1834
		});
		expect(murray).toContain('style-devotional');
		expect(spurgeon).toContain('style-revival');
	});

	it("dresses an author nobody has entered in their century's face", () => {
		// An admin import, or a writer added this morning. Falling back to the
		// house face would make them the only unfinished-looking book on a shelf.
		expect(styleOf({ slug: 'not-in-any-table', name: 'A Puritan', birth_year: 1620 })).toContain(
			'style-press'
		);
	});
});

describe('the plate holds no copy of the generator', () => {
	/**
	 * STYLE_GUIDE §5: "Proportions may echo `covers.py`; algorithms may not."
	 *
	 * The `tspan` assertion above catches someone re-pasting SVG. It does not
	 * catch what actually drifted last time — a JS type ramp
	 * (`book.title.length <= 22 ? 58 : 46`) and a `wrap()` budget, which produce
	 * no SVG at all. Those are what this reads the source for, in the same idiom
	 * as `colorTokens.test.ts` and `rtl.test.ts`: a rule nobody can enforce by
	 * memory is a rule that comes back.
	 *
	 * If a future plate genuinely needs to measure a title, say so on the line —
	 * `metrics-ok:` with a reason — and this steps aside.
	 */
	const source = readFileSync(join(process.cwd(), 'src/lib/components/BookCover.svelte'), 'utf-8');

	it.each([
		['title.length', /\btitle\.length\b/],
		['subtitle.length', /\bsubtitle\.length\b/],
		['a local wrap()', /function wrap\b|const wrap\s*=/]
	])('does not re-derive the generator with %s', (_what, pattern) => {
		const offending = source
			.split('\n')
			.filter((line) => pattern.test(line) && !line.includes('metrics-ok:'));
		expect(offending).toEqual([]);
	});
});

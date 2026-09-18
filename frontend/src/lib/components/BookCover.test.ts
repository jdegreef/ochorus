import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { flushSync, mount, unmount } from 'svelte';
import { afterEach, describe, expect, it, vi } from 'vitest';

import BookCover from './BookCover.svelte';
import type { BookSummary } from '$lib/library-public';

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

	it('tells the browser, and the CSS, what script the title is in', () => {
		// The gates in `coverStyles.test.ts` read CSS text; this is the other half
		// — that the component actually emits what those blocks select on. Two
		// separate things: `lang` is for the browser (shaping, hyphenation, a
		// screen reader's voice), the class is for the metric corrections.
		const ar = render({ book: book({ language: 'ar', title: 'المخدع', subtitle: 'دراسة' }) });
		expect(ar.querySelector('.cover-type')?.classList).toContain('script-arabic');
		expect(ar.querySelector('.title')?.getAttribute('lang')).toBe('ar');
		expect(ar.querySelector('.subtitle')?.getAttribute('lang')).toBe('ar');
		// The byline is one Latin row for every edition — an author has no
		// per-language name — so claiming it is Arabic would tell a screen reader
		// to read "Andrew Murray" in the wrong voice.
		expect(ar.querySelector('.byline')?.hasAttribute('lang')).toBe(false);

		// Latin is what the recipes are already written in, so it takes no class.
		const en = render({ book: book() });
		expect(en.querySelector('.cover-type')?.className).not.toMatch(/script-/);

		// `en-modern` is Ochorus' own edition marker, not a BCP-47 subtag: a
		// browser drops the whole attribute and shapes the title in the UI locale.
		const modern = render({ book: book({ language: 'en-modern' }) });
		expect(modern.querySelector('.title')?.getAttribute('lang')).toBe('en');
	});

	it("paints the book's own colour, falling to a darker tone of itself", () => {
		const el = render({ book: book({ cover_color: '#0b7285' }) });
		// The gradient goes in as a custom property, which the browser stores
		// verbatim (a plain `background` would come back normalised to rgb()).
		const style = el.querySelector('.cover-plate')?.getAttribute('style') ?? '';
		// NOT `#0b7285` exactly, and the difference is the point. This fallback
		// stands in for `covers.build_ground`, which lays a rib over its gradient
		// — 1.5 of every 4 user units of black at alpha 0.11 — so the real plate
		// renders 0.959x its own colour. The fallback carries that same factor, so
		// the two sit at the same value, which is the invariant `coverGradient`
		// documents and the reason its `89%` stop exists at all. Measured at the
		// byline: the ribbed plate gives 5.322:1 and this gives 5.324:1, where
		// the unfactored colour gives 5.009:1 — and for the library's floored
		// blue, 4.465:1, under the 4.5 bar the plate itself clears.
		expect(style).toContain('#0b6d80'); // the book's colour as the artwork renders it
		expect(style).toContain('#063c46'); // and that, shaded to 0.55, as the file's stop is
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

	// A designed cover is composed at the artwork's OWN aspect, and object-cover
	// on an off-3:4 one crops its baked-in byline off the top and its Ochorus
	// mark off the foot — the very words this tier exists to keep. So one that
	// isn't 3:4 is contained whole and matted; one that is fills the card as
	// before. The measurement is the image's, so it can only be made once the
	// file has loaded and reported its natural size.
	const loadWith = (img: HTMLImageElement, w: number, h: number) => {
		Object.defineProperty(img, 'naturalWidth', { value: w, configurable: true });
		Object.defineProperty(img, 'naturalHeight', { value: h, configurable: true });
		img.dispatchEvent(new Event('load'));
		flushSync();
	};

	it('never renders a cover hidden while it waits for a script', () => {
		// A prerendered cover must be able to paint the moment it decodes. It used
		// to ship at opacity 0 and wait for an `onload` handler, which on /books/
		// held a cover that arrived at 1.0s invisible until 2.3s — the page's LCP.
		const el = render({ book: book({ cover_url: '/covers/lord-teach-us-to-pray-2.jpg' }) });
		const img = el.querySelector('img')!;
		expect(img.className).not.toMatch(/\bopacity-0\b/);
		// The placeholder is behind it, not instead of it.
		expect(el.querySelector('.animate-pulse')).not.toBeNull();
	});

	it('recognises a cover that finished loading before it hydrated', () => {
		// The prerendered <img> is fetched before the scripts arrive, so its
		// `load` event can fire before `onload` is attached — and is never
		// replayed. Such an image is already `complete` when the component
		// attaches, and must be treated as loaded: placeholder retired, and a
		// designed cover's shape measured so it gets its mat.
		const complete = vi.spyOn(HTMLImageElement.prototype, 'complete', 'get').mockReturnValue(true);
		const w = vi.spyOn(HTMLImageElement.prototype, 'naturalWidth', 'get').mockReturnValue(443);
		const h = vi.spyOn(HTMLImageElement.prototype, 'naturalHeight', 'get').mockReturnValue(668);
		try {
			const el = render({ book: book({ cover_url: '/covers/lord-teach-us-to-pray-2.jpg' }) });
			flushSync();
			expect(el.querySelector('.animate-pulse')).toBeNull();
			const imgs = el.querySelectorAll('img');
			expect(imgs).toHaveLength(2);
			expect(imgs[0].className).toContain('object-contain');
		} finally {
			complete.mockRestore();
			w.mockRestore();
			h.mockRestore();
		}
	});

	it('mats an off-3:4 designed cover so nothing is cropped, leaving a 3:4 one alone', () => {
		const el = render({ book: book({ cover_url: '/covers/lord-teach-us-to-pray-2.jpg' }) });
		// Before the file's size is known it fills the card exactly as it always
		// has: one image, object-cover, no mat behind it.
		expect(el.querySelectorAll('img')).toHaveLength(1);
		expect(el.querySelector('img')?.className).toContain('object-cover');

		// A cover narrower than 3:4 loads: it is now contained, with a second,
		// decorative image behind it filling the remainder.
		loadWith(el.querySelector('img')!, 443, 668);
		const matted = el.querySelectorAll('img');
		expect(matted).toHaveLength(2);
		expect(matted[0].className).toContain('object-contain');
		expect(matted[0].getAttribute('alt')).toContain('Waiting on God');
		expect(matted[1].getAttribute('aria-hidden')).toBe('true');
		expect(matted[1].getAttribute('alt')).toBe('');

		// A cover that is already 3:4 is never matted: it fills the card, alone.
		const threeFour = render({ book: book({ cover_url: '/covers/absolute-surrender.png' }) });
		loadWith(threeFour.querySelector('img')!, 600, 800);
		expect(threeFour.querySelectorAll('img')).toHaveLength(1);
		expect(threeFour.querySelector('img')?.className).toContain('object-cover');
	});

	it('never mats a ground — a painting or plate is drawn at 3:4 to be covered', () => {
		// The mat is the designed tier's alone; a ground with off-size art (were
		// one ever committed) still fills, because the type is set over it here.
		const el = render({ book: book({ cover_url: '/covers/art/waiting-on-god.jpg' }) });
		loadWith(el.querySelector('img')!, 443, 668);
		expect(el.querySelectorAll('img')).toHaveLength(1);
		expect(el.querySelector('img')?.className).toContain('object-cover');
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

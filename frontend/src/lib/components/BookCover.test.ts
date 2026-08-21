import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { mount, unmount } from 'svelte';
import { afterEach, describe, expect, it } from 'vitest';

import BookCover from './BookCover.svelte';
import type { BookSummary } from '$lib/library';

/**
 * The plate is a PLACEHOLDER, and this is the rule that keeps it one.
 *
 * It used to be a hand-built SVG replica of `covers.py`'s generated cover, and
 * the two drifted in every dimension that could drift: type ramp, wrap budget,
 * line height, title centre, rule offset, gradient angle, the missing vignette
 * — and, worse, no RTL, no per-script fonts and no script scaling, so an Arabic
 * book's fallback came out in Georgia set left-to-right.
 *
 * These assert the properties that made the replica wrong, not pixels: the
 * title is real text the browser can shape and wrap, and no second copy of the
 * generator's metrics decides how it is set.
 */
const book = (over: Partial<BookSummary> = {}): BookSummary =>
	({
	slug: 'waiting-on-god',
	title: 'Waiting on God',
	subtitle: '',
	author: { slug: 'andrew-murray', name: 'Andrew Murray' },
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
	target = document.createElement('div');
	document.body.appendChild(target);
	component = mount(BookCover, { target, props }) as Record<string, unknown>;
	return target;
};

afterEach(() => {
	if (component) unmount(component);
	target?.remove();
	component = undefined;
});

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
		// jsdom normalises hex to rgb() in the style attribute.
		const style = el.querySelector('.plate')?.getAttribute('style') ?? '';
		expect(style).toContain('rgb(11, 114, 133)'); // #0b7285, the book's own
		expect(style).toContain('rgb(6, 63, 73)'); // shaded to 0.55, as the file is
	});

	it('names the cover once for a screen reader, and hides the decorative type', () => {
		// role="img" makes the plate a leaf, so the title inside is not announced
		// a second time after the label.
		const plate = render({ book: book() }).querySelector('.plate');
		expect(plate?.getAttribute('role')).toBe('img');
		expect(plate?.getAttribute('aria-label')).toContain('Waiting on God');
	});

	it('shows the artwork instead when the book has some', () => {
		const el = render({ book: book({ cover_url: '/covers/waiting-on-god.svg' }) });
		expect(el.querySelector('img')?.getAttribute('src')).toBe('/covers/waiting-on-god.svg');
		expect(el.querySelector('.plate')).toBeNull();
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

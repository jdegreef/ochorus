import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { mount, unmount } from 'svelte';
import { afterEach, describe, expect, it } from 'vitest';

import BookCover from './components/BookCover.svelte';
import { coverPlateMarkup, coverTypeMarkup, type CoverCardBook } from './coverCardMarkup';
import { coverLayoutFor } from './coverLayouts';
import { coverStyleFor } from './coverStyles';
import { eraOf } from './eras';
import { scrimStrength } from './coverScrim';
import type { BookSummary } from '$lib/library-public';

/**
 * The two renderers, held against each other.
 *
 * A cover is drawn twice: by `BookCover.svelte` in the browser, and by
 * `scripts/generate-cover-og.mjs` into the share card that a link preview
 * shows. The second cannot mount a Svelte component, so it builds the same
 * tree by hand — and until this file existed, NOTHING compared the two. They
 * had drifted in three ways that all change pixels, and every one of them was
 * invisible because twins are only built for English books today:
 *
 *   * no `script-<x>` class, so the first Arabic or Hindi card would take the
 *     Latin face;
 *   * no `dir="auto"`, so an Arabic card would lay out left-to-right;
 *   * no `lang`, so the browser would shape and hyphenate it as English.
 *
 * WHAT THIS GATES IS THE PIXELS, not the markup byte for byte. A share card is
 * a raster: it has no accessibility tree, so `role`, `aria-label` and
 * `aria-hidden` cannot change it, and a gate demanding those match would be
 * asserting something it does not care about. Structure, classes, `lang` and
 * `dir` all decide what gets drawn, so those must agree exactly.
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

const LOCKUP = readFileSync(
	join(process.cwd(), 'src/lib/brand/ochorus-lockup.svg'),
	'utf8'
);

let target: HTMLElement;
let component: Record<string, unknown> | undefined;

afterEach(() => {
	if (component) unmount(component);
	component = undefined;
	target?.remove();
});

/** Mount the real component and hand back its `.cover-plate` element.
 *
 *  THE PLATE, not the type inside it. Starting a level lower left the wrapper
 *  ungated, and it carries `.over-art` — the class that puts the four-stop
 *  scrim under white type on a painting. Renamed there and nowhere else, every
 *  painted card would keep the old scrim with this file green. */
function rendered(props: Partial<BookSummary>): Element {
	target = document.createElement('div');
	document.body.appendChild(target);
	component = mount(BookCover, { target, props: { book: book(props) } }) as Record<
		string,
		unknown
	>;
	const el = target.querySelector('.cover-plate');
	expect(el, 'BookCover drew no .cover-plate at all').not.toBeNull();
	return el!;
}

/** Parse the script's markup and hand back its `.cover-plate` element. */
function built(card: CoverCardBook): Element {
	const host = document.createElement('div');
	host.innerHTML = coverPlateMarkup(card, LOCKUP);
	const el = host.querySelector('.cover-plate');
	expect(el, 'coverPlateMarkup drew no .cover-plate at all').not.toBeNull();
	return el!;
}

/** The type block alone, for the assertions that are about it. */
const builtType = (card: CoverCardBook): Element => {
	const host = document.createElement('div');
	host.innerHTML = coverTypeMarkup(card, LOCKUP);
	return host.querySelector('.cover-type')!;
};

/**
 * An element reduced to what a RASTER can tell apart: its tag, its classes, and
 * the attributes that change how the browser draws it.
 *
 * `style` is deliberately included — the brandmark's `--h` is what sizes the
 * mark, so a card that dropped it would draw the logo at its default height.
 * Text is deliberately excluded: the two callers are given different books in
 * the wild, and the words are not what drifts.
 */
function skeleton(el: Element): unknown {
	// `svelte-<hash>` is the compiler's style scoping, not markup anyone wrote —
	// it appears on exactly the elements whose component has a `<style>` block,
	// and the script has no equivalent because it inlines the stylesheet whole.
	const classes = [...el.classList].filter((c) => !/^svelte-[a-z0-9]+$/.test(c)).sort();
	const attrs: Record<string, string> = {};
	for (const name of ['lang', 'dir', 'style']) {
		const v = el.getAttribute(name);
		// Svelte serialises a style attribute with a trailing `;` and the string
		// version has none. Same declaration, two spellings.
		if (v !== null) attrs[name] = v.replace(/\s+/g, ' ').replace(/;$/, '').trim();
	}
	return {
		tag: el.tagName.toLowerCase(),
		classes,
		attrs,
		// The lockup is a whole SVG document in both; comparing its innards would
		// be comparing the brand file to itself. Its PRESENCE is the property.
		children: el.classList.contains('brandmark')
			? [`<svg>x${el.querySelectorAll('svg').length}`]
			: [...el.children].map(skeleton)
	};
}

describe('the two cover renderers agree', () => {
	// One Latin book and one of every script the library is read in. The Latin
	// case alone would have passed the whole time this was broken.
	//
	// EVERY CASE CARRIES A GROUND, because that is the branch the share card
	// mirrors. `BookCover` draws the type over a file (`overFile`) or, when a
	// book has no cover at all, over a CSS plate — and only the first can ever
	// be photographed, since the script is handed a ground to draw. Written
	// against the coverless branch this gate compared the card to a tree the
	// script never produces, and disagreed about the emblem band for a reason
	// that was the test's fault rather than the code's.
	const PLATE = '/covers/waiting-on-god.svg';
	const ART = '/covers/art/waiting-on-god.jpg';
	const cases: Array<[string, Partial<BookSummary>, Partial<CoverCardBook>]> = [
		['a plate, no subtitle', { cover_url: PLATE }, {}],
		[
			'a painting',
			{ cover_url: ART },
			// A painting has no emblem beneath it to leave room for — and carries
			// `--scrim-strength`, which the skeleton compares as a style attribute.
			// `waiting-on-god` is a real work with a measured strength, so this is
			// the case that catches the card and the page disagreeing about it.
			// Andrew Murray is also a laid-out author (`coverLayouts.ts`), so this
			// is the case where the two disagreeing about a layout's classes
			// would show.
			{
				art: true,
				scrim: scrimStrength('waiting-on-god'),
				layout: coverLayoutFor('andrew-murray', null, 'waiting-on-god')
			}
		],
		[
			'a painting in the framed composition',
			// A painting by an author with no entry in the layout table.
			{
				cover_url: '/covers/art/a-retrospect.jpg',
				slug: 'a-retrospect',
				author: { ...book().author, slug: 'an-author-with-no-layout' }
			},
			{
				art: true,
				scrim: scrimStrength('a-retrospect'),
				style: coverStyleFor(eraOf(1828), 'an-author-with-no-layout', 'a-retrospect')
			}
		],
		[
			'a laid-out painting in arabic',
			{ cover_url: ART, language: 'ar', title: 'انتظار الله' },
			{
				lang: 'ar',
				script: 'arabic',
				title: 'انتظار الله',
				art: true,
				scrim: scrimStrength('waiting-on-god'),
				layout: coverLayoutFor('andrew-murray', 'arabic', 'waiting-on-god')
			}
		],
		[
			'a plate with a subtitle',
			{ cover_url: PLATE, subtitle: 'Thoughts on the Nearness of God' },
			{ subtitle: 'Thoughts on the Nearness of God' }
		],
		[
			// The script hands the card `coverTitle(fields)`, so the card side is
			// the short title — and, being short, drops the long title's step-down.
			'a short cover title over a long title',
			{
				cover_url: PLATE,
				title: 'Rooted – 30 Days with God for Youth – Book 1 of the Series',
				cover_title: 'Rooted'
			},
			{ title: 'Rooted' }
		],
		[
			'arabic',
			{ cover_url: PLATE, language: 'ar', title: 'انتظار الله', subtitle: 'تأملات' },
			{ lang: 'ar', script: 'arabic', title: 'انتظار الله', subtitle: 'تأملات' }
		],
		[
			'devanagari',
			{ cover_url: PLATE, language: 'hi', title: 'परमेश्वर की प्रतीक्षा' },
			{ lang: 'hi', script: 'devanagari', title: 'परमेश्वर की प्रतीक्षा' }
		],
		[
			'a series volume, in its own digits',
			{
				cover_url: PLATE,
				slug: 'brave-for-god-2',
				series_position: 2,
				language: 'ar',
				title: 'شجعان لله'
			},
			{
				lang: 'ar',
				script: 'arabic',
				title: 'شجعان لله',
				volume: '2',
				// The style the component will derive from the slug, so the
				// comparison is of the tree and not of which recipe was picked.
				style: 'young'
			}
		],
		[
			'cyrillic',
			{ cover_url: PLATE, language: 'uk', title: 'Чекання на Бога' },
			{ lang: 'uk', script: 'cyrillic', title: 'Чекання на Бога' }
		]
	];

	for (const [name, props, card] of cases) {
		it(`draws the same tree for ${name}`, () => {
			const fromComponent = skeleton(rendered(props));
			const fromScript = skeleton(
				built({
					author: 'Andrew Murray',
					title: props.title ?? 'Waiting on God',
					subtitle: null,
					style: 'devotional',
					script: null,
					lang: props.language ?? 'en',
					// A plate by default; the painting case overrides it below.
					// `BookCover` reserves the band for a PLATE specifically — not for
					// a painting, which has no emblem beneath it, and not for the
					// coverless CSS fallback, which no share card is ever made from.
					art: false,
					...card
				})
			);
			expect(
				fromScript,
				`the share card's markup has drifted from the component's for ${name} — ` +
					`a link preview would be drawn differently from the page it points at`
			).toEqual(fromComponent);
		});
	}

	it('gives a non-latin card the script class that picks its face', () => {
		// The specific regression this file was written for, asserted head-on so
		// a failure names it rather than showing a tree diff.
		for (const [lang, script] of [
			['ar', 'arabic'],
			['hi', 'devanagari'],
			['uk', 'cyrillic']
		]) {
			const el = builtType({
				author: 'Andrew Murray',
				title: 'x',
				style: 'devotional',
				script,
				lang,
				art: false
			});
			expect(
				[...el.classList],
				`a ${lang} share card carries no script-${script}, so it would be set in ` +
					`the Latin face`
			).toContain(`script-${script}`);
			expect(el.querySelector('.title')?.getAttribute('dir')).toBe('auto');
			expect(el.querySelector('.title')?.getAttribute('lang')).toBe(lang);
		}
	});

	it('leaves the emblem band off a painting, as the component does', () => {
		// A painting has no emblem under it to leave room for; a plate does. Get
		// this wrong and every painted card's title sits at the wrong height.
		expect(
			builtType({ author: 'a', title: 'b', style: 'devotional', lang: 'en', art: true })
				.querySelector('.emblem-band')
		).toBeNull();
		expect(
			builtType({ author: 'a', title: 'b', style: 'devotional', lang: 'en', art: false })
				.querySelector('.emblem-band')
		).not.toBeNull();
	});

	it('escapes what it interpolates', () => {
		// The script builds a string; the component builds nodes. A title with a
		// bracket in it is the one input that can turn one into markup.
		const el = builtType({
			author: 'a"b',
			title: '<script>x</script>',
			style: 'devotional',
			lang: 'en',
			art: false
		});
		expect(el.querySelectorAll('script')).toHaveLength(0);
		expect(el.querySelector('.title')?.textContent).toBe('<script>x</script>');
		expect(el.querySelector('.byline')?.textContent).toBe('a"b');
	});
});

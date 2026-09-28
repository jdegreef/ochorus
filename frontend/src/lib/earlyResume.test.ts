import { afterEach, describe, expect, it, vi } from 'vitest';
import { EARLY_RESUME_JS } from './earlyResume';
import { ANCHOR_KEY, PROGRESS_KEY, chapterKey } from './reading-schema';
import { HEADER_OFFSET } from './reading';
import { READER_PREFS_KEY } from './readerPrefs.svelte';

const PARA_H = 100;

afterEach(() => {
	vi.restoreAllMocks();
	delete (document as { currentScript?: unknown }).currentScript;
	localStorage.clear();
});

/**
 * Run the script as the parser would — as the tag straight after a chapter
 * body of `n` paragraphs, each PARA_H tall, at `url`, in a `width`×812 window,
 * over `store` (values as raw strings, so unreadable storage goes through the
 * same path). jsdom lays nothing out, so the geometry is supplied. Returns the
 * paragraph it scrolled to the top (-1 for none).
 */
function run(url: string, store: Record<string, string>, n = 20, width = 375, lang = 'en') {
	// Fresh per call: two runs in one test must not see each other's spies.
	vi.restoreAllMocks();
	localStorage.clear();
	for (const [k, v] of Object.entries(store)) localStorage.setItem(k, v);
	history.replaceState(null, '', url);
	document.documentElement.lang = lang;
	document.body.innerHTML = `<div class="reading">${'<p>x</p>'.repeat(n)}</div>`;
	const body = document.querySelector('.reading')!;
	const script = document.createElement('script');
	body.after(script);
	Object.defineProperty(document, 'currentScript', { value: script, configurable: true });
	vi.spyOn(window, 'innerWidth', 'get').mockReturnValue(width);
	vi.spyOn(window, 'innerHeight', 'get').mockReturnValue(812);
	// The document so far ends at the body: nothing below it is parsed yet.
	vi.spyOn(document.documentElement, 'scrollHeight', 'get').mockReturnValue(n * PARA_H);
	const kids = [...body.children];
	vi.spyOn(Element.prototype, 'getBoundingClientRect').mockImplementation(function (this: Element) {
		return { top: kids.indexOf(this) * PARA_H } as DOMRect;
	});
	const to = vi.spyOn(window, 'scrollTo').mockImplementation(() => {});
	new Function(EARLY_RESUME_JS)();
	const y = to.mock.calls[0]?.[1] as number | undefined;
	return y === undefined ? -1 : (y + HEADER_OFFSET) / PARA_H;
}

const anchor = (slug: string, order: number, p: number) => ({
	[ANCHOR_KEY]: JSON.stringify({ [chapterKey(slug, order)]: p })
});

describe('EARLY_RESUME_JS', () => {
	it("scrolls to this device's anchor for the chapter, under the header", () => {
		expect(run('/books/humility/3/', anchor('humility', 3, 7))).toBe(7);
	});

	it('works under a locale prefix', () => {
		expect(run('/ar/books/humility/3/', anchor('humility', 3, 7), 20, 375, 'ar')).toBe(7);
	});

	it("reads a language-tagged anchor only in its own language", () => {
		const tagged = (lang: string) => ({
			[ANCHOR_KEY]: JSON.stringify({ [chapterKey('humility', 3)]: { p: 7, lang } })
		});
		expect(run('/sw/books/humility/3/', tagged('sw'), 20, 375, 'sw')).toBe(7);
		// Saved in the English text: its paragraphs aren't this edition's.
		expect(run('/sw/books/humility/3/', tagged('en'), 20, 375, 'sw')).toBe(-1);
	});

	it('falls back to the synced record only for this chapter, in this language', () => {
		const rec = (order: number, language = 'en') => ({
			[PROGRESS_KEY]: JSON.stringify({ humility: { order, paragraph_index: 5, language } })
		});
		expect(run('/books/humility/3/', rec(3))).toBe(5);
		expect(run('/books/humility/3/', rec(4))).toBe(-1);
		expect(run('/books/humility/3/', rec(3, 'sw'))).toBe(-1);
	});

	it.each([
		['a ?p= jump', '/books/humility/3/?p=2', {}],
		['a ?pg= turn', '/books/humility/3/?pg=last', {}],
		['a #fragment', '/books/humility/3/#q', {}],
		['page mode', '/books/humility/3/', { [READER_PREFS_KEY]: JSON.stringify({ paged: true }) }],
		['a page that is not a chapter', '/books/humility/', {}]
	])('stands aside for %s', (_, url, extra) => {
		expect(run(url, { ...anchor('humility', 3, 7), ...extra })).toBe(-1);
	});

	it("mirrors the wide-screen page-mode default for a reader who never chose", () => {
		const a = anchor('humility', 3, 7);
		expect(run('/books/humility/3/', a, 20, 1280)).toBe(-1);
		const scroll = { [READER_PREFS_KEY]: JSON.stringify({ paged: false }) };
		expect(run('/books/humility/3/', { ...a, ...scroll }, 20, 1280)).toBe(7);
	});

	it("stands aside for a paragraph that can't reach the top before the page has parsed", () => {
		// 20 paragraphs = 2000px; the last 812px can't be scrolled to the top.
		expect(run('/books/humility/3/', anchor('humility', 3, 18))).toBe(-1);
		expect(run('/books/humility/3/', anchor('humility', 3, 12))).toBe(12);
	});

	it('leaves the top alone, and a spot past the end', () => {
		expect(run('/books/humility/3/', anchor('humility', 3, 0))).toBe(-1);
		expect(run('/books/humility/3/', anchor('humility', 3, 99))).toBe(-1);
	});

	it('never throws on storage it cannot read', () => {
		expect(() => run('/books/humility/3/', { [ANCHOR_KEY]: '{not json' })).not.toThrow();
	});
});

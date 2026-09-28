import { afterEach, describe, expect, it, vi } from 'vitest';
import { EARLY_RESUME_JS } from './earlyResume';
import { ANCHOR_KEY, PROGRESS_KEY, chapterKey } from './reading-schema';
import { HEADER_OFFSET } from './reading';
import { READER_PREFS_KEY } from './readerPrefs.svelte';

// jsdom has no scrollIntoView; a no-op to spy on (it lays nothing out anyway).
Element.prototype.scrollIntoView ??= () => {};

afterEach(() => {
	vi.restoreAllMocks();
	delete (document as { currentScript?: unknown }).currentScript;
	localStorage.clear();
});

/**
 * Run the script as the parser would — as the tag straight after a chapter
 * body of `n` paragraphs, at `url`, over `store` (values as raw strings, so
 * unreadable storage goes through the same path). Returns the paragraph it
 * scrolled to (-1 for none) and the header correction it applied.
 */
function run(url: string, store: Record<string, string>, n = 20) {
	for (const [k, v] of Object.entries(store)) localStorage.setItem(k, v);
	history.replaceState(null, '', url);
	document.body.innerHTML = `<div class="reading">${'<p>x</p>'.repeat(n)}</div>`;
	const body = document.querySelector('.reading')!;
	const script = document.createElement('script');
	body.after(script);
	Object.defineProperty(document, 'currentScript', { value: script, configurable: true });
	const into = vi.spyOn(Element.prototype, 'scrollIntoView').mockImplementation(() => {});
	const by = vi.spyOn(window, 'scrollBy').mockImplementation(() => {});
	new Function(EARLY_RESUME_JS)();
	return {
		at: into.mock.contexts.length ? [...body.children].indexOf(into.mock.contexts[0] as Element) : -1,
		by: by.mock.calls.map((c) => c[1])
	};
}

const anchor = (slug: string, order: number, p: number) => ({
	[ANCHOR_KEY]: JSON.stringify({ [chapterKey(slug, order)]: p })
});

describe('EARLY_RESUME_JS', () => {
	it("scrolls to this device's anchor for the chapter, under the header", () => {
		expect(run('/books/humility/3/', anchor('humility', 3, 7))).toEqual({ at: 7, by: [-HEADER_OFFSET] });
	});

	it('works under a locale prefix', () => {
		expect(run('/ar/books/humility/3/', anchor('humility', 3, 7)).at).toBe(7);
	});

	it('falls back to the synced record only when it names this chapter', () => {
		const rec = (order: number) => ({
			[PROGRESS_KEY]: JSON.stringify({ humility: { order, paragraph_index: 5 } })
		});
		expect(run('/books/humility/3/', rec(3)).at).toBe(5);
		expect(run('/books/humility/3/', rec(4)).at).toBe(-1);
	});

	it.each([
		['a ?p= jump', '/books/humility/3/?p=2', {}],
		['a ?pg= turn', '/books/humility/3/?pg=last', {}],
		['a #fragment', '/books/humility/3/#q', {}],
		['page mode', '/books/humility/3/', { [READER_PREFS_KEY]: JSON.stringify({ paged: true }) }],
		['a page that is not a chapter', '/books/humility/', {}]
	])('stands aside for %s', (_, url, extra) => {
		expect(run(url, { ...anchor('humility', 3, 7), ...extra }).at).toBe(-1);
	});

	it('leaves the top alone, and a spot past the end', () => {
		expect(run('/books/humility/3/', anchor('humility', 3, 0)).at).toBe(-1);
		expect(run('/books/humility/3/', anchor('humility', 3, 99)).at).toBe(-1);
	});

	it('never throws on storage it cannot read', () => {
		expect(() => run('/books/humility/3/', { [ANCHOR_KEY]: '{not json' })).not.toThrow();
	});
});

import { describe, expect, it } from 'vitest';
import { EARLY_RESUME_JS } from './earlyResume';
import { ANCHOR_KEY, PROGRESS_KEY, chapterKey } from './reading-schema';
import { HEADER_OFFSET } from './reading';

/** Run the script against a chapter body of `n` paragraphs at `url`. */
function run(url: string, store: Record<string, unknown>, n = 20) {
	localStorage.clear();
	for (const [k, v] of Object.entries(store)) localStorage.setItem(k, JSON.stringify(v));
	history.replaceState(null, '', url);
	document.body.innerHTML = `<div class="reading">${'<p>x</p>'.repeat(n)}</div>`;
	const body = document.querySelector('.reading')!;
	const script = document.createElement('script');
	body.after(script);
	const scrolled: number[] = [];
	const into: Element[] = [];
	window.scrollBy = ((_x: number, y: number) => {
		scrolled.push(y);
	}) as unknown as typeof window.scrollBy;
	Element.prototype.scrollIntoView = function (this: Element) {
		into.push(this);
	};
	// Evaluate as the parser would: with `document.currentScript` = the tag.
	Object.defineProperty(document, 'currentScript', { value: script, configurable: true });
	new Function(EARLY_RESUME_JS)();
	return { into: into.map((el) => [...body.children].indexOf(el)), scrolled };
}

describe('EARLY_RESUME_JS', () => {
	const anchors = (slug: string, order: number, p: number) => ({ [ANCHOR_KEY]: { [chapterKey(slug, order)]: p } });

	it('uses the storage keys and header offset the reader uses', () => {
		expect(EARLY_RESUME_JS).toContain(`'${ANCHOR_KEY}'`);
		expect(EARLY_RESUME_JS).toContain(`'${PROGRESS_KEY}'`);
		expect(EARLY_RESUME_JS).toContain('ochorus:reader-prefs');
		expect(EARLY_RESUME_JS).toContain(`scrollBy(0,-${HEADER_OFFSET})`);
	});

	it("scrolls to this device's anchor for the chapter, under the header", () => {
		expect(run('/books/humility/3/', anchors('humility', 3, 7))).toEqual({ into: [7], scrolled: [-HEADER_OFFSET] });
		// Under a locale prefix too.
		expect(run('/ar/books/humility/3/', anchors('humility', 3, 7)).into).toEqual([7]);
	});

	it('falls back to the synced record when it names this chapter', () => {
		const rec = (order: number) => ({ [PROGRESS_KEY]: { humility: { order, paragraph_index: 5 } } });
		expect(run('/books/humility/3/', rec(3)).into).toEqual([5]);
		expect(run('/books/humility/3/', rec(4)).into).toEqual([]);
	});

	it('stands aside wherever the app decides the landing', () => {
		const a = anchors('humility', 3, 7);
		expect(run('/books/humility/3/?p=2', a).into).toEqual([]);
		expect(run('/books/humility/3/?pg=last', a).into).toEqual([]);
		expect(run('/books/humility/3/#q', a).into).toEqual([]);
		expect(run('/books/humility/3/', { ...a, 'ochorus:reader-prefs': { paged: true } }).into).toEqual([]);
		expect(run('/books/humility/', a).into).toEqual([]);
		// Paragraph 0 is the top already; a spot past the end is nowhere.
		expect(run('/books/humility/3/', anchors('humility', 3, 0)).into).toEqual([]);
		expect(run('/books/humility/3/', anchors('humility', 3, 99)).into).toEqual([]);
	});

	it('never throws on storage it cannot read', () => {
		localStorage.setItem(ANCHOR_KEY, '{not json');
		expect(() => new Function(EARLY_RESUME_JS)()).not.toThrow();
	});
});

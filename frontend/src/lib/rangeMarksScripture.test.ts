import { beforeEach, describe, expect, it, vi } from 'vitest';
import { renderMarks } from './rangeMarks';
import type { Mark } from './reading-schema';

/**
 * A tap that lands on a scripture reference inside a highlight.
 *
 * Two delegated handlers used to claim it: this one (the note editor) and the
 * chapter route's scripture handler on the enclosing `<article>`. This one runs
 * first and never stopped propagation, so both opened — a note dialog on top of
 * the scripture popover — and a verse reference stopped being tappable at all
 * once it was highlighted.
 */
let container: HTMLElement;

const mark = (id: string, s: number, e: number): Mark => ({ id, p: 0, s, e });

beforeEach(() => {
	container = document.createElement('div');
	container.innerHTML =
		'<p>He quotes <a class="scripture-ref" data-ref="John 3:16">John 3:16</a> often.</p>';
	document.body.replaceChildren(container);
});

const click = (el: Element) => el.dispatchEvent(new MouseEvent('click', { bubbles: true }));

describe('a scripture reference inside a highlight', () => {
	it('nests the mark INSIDE the anchor — the shape the fix relies on', () => {
		// `wrapRange` splits text nodes in place, so the highlight can never wrap
		// the anchor; it always lands within it. That is why `closest()` from the
		// click target finds the reference.
		renderMarks(container, [mark('m1', 0, 26)], () => {});
		const anchor = container.querySelector('a.scripture-ref')!;
		expect(anchor.querySelector('mark.range-mark')).not.toBeNull();
		expect(anchor.closest('mark.range-mark')).toBeNull();
	});

	it('does not open the note editor when the tap is on the reference', () => {
		const onMarkClick = vi.fn();
		renderMarks(container, [mark('m1', 0, 26)], onMarkClick);

		const inRef = container.querySelector('a.scripture-ref mark.range-mark')!;
		click(inRef);

		// The reference wins: it is the smaller, deliberately tappable target.
		expect(onMarkClick).not.toHaveBeenCalled();
	});

	it('still opens the note editor for the rest of the same highlight', () => {
		const onMarkClick = vi.fn();
		renderMarks(container, [mark('m1', 0, 26)], onMarkClick);

		const marks = [...container.querySelectorAll('mark.range-mark')];
		const outside = marks.find((m) => !m.closest('a.scripture-ref'))!;
		expect(outside).toBeDefined();
		click(outside);

		expect(onMarkClick).toHaveBeenCalledWith('m1', expect.anything());
	});

	it('leaves a highlight with no reference in it untouched', () => {
		container.innerHTML = '<p>Plain prose with no reference at all.</p>';
		const onMarkClick = vi.fn();
		renderMarks(container, [mark('m2', 0, 12)], onMarkClick);

		click(container.querySelector('mark.range-mark')!);
		expect(onMarkClick).toHaveBeenCalledWith('m2', expect.anything());
	});
});

import { beforeEach, describe, expect, it } from 'vitest';
import { renderMarks } from './rangeMarks';
import type { Mark } from './reading-schema';

/**
 * The highlight just made brushes in (app.css `mark.range-mark.fresh`); every
 * other mark is simply drawn. Each render rebuilds every mark from the
 * paragraph's pristine HTML, so the flag has to say which one is new — or a
 * page load, a recolour or a sync would brush them all in again.
 */
let container: HTMLElement;
const mark = (id: string, p: number, s: number, e: number): Mark => ({ id, p, s, e });
const fresh = () => [...container.querySelectorAll('mark.range-mark.fresh')].map((m) => m.textContent);

beforeEach(() => {
	container = document.createElement('div');
	container.innerHTML = '<p>Be not angry that you cannot make <em>others</em> as you wish.</p><p>Since you cannot.</p>';
	document.body.replaceChildren(container);
});

describe('a highlight just made', () => {
	const old = mark('old', 1, 0, 5);
	// One highlight across an <em> and into the next paragraph: three <mark>s, one id.
	const made = [mark('new', 0, 29, 40), mark('new', 1, 6, 16)];

	it('marks every piece of the new highlight, and nothing else, as fresh', () => {
		renderMarks(container, [old, ...made], () => {}, [], undefined, 'new');
		expect(fresh()).toEqual(['make ', 'others', 'you cannot']);
		expect(container.querySelectorAll('mark.range-mark')).toHaveLength(4);
	});

	it('draws every mark plainly when nothing is new (a load, a recolour, a sync)', () => {
		renderMarks(container, [old, ...made], () => {});
		expect(fresh()).toEqual([]);
	});

	it('is fresh for its sweep only, then drawn like the rest', () => {
		renderMarks(container, [old, ...made], () => {}, [], undefined, 'new');
		const piece = container.querySelector('mark.range-mark.fresh')!;
		piece.dispatchEvent(Object.assign(new Event('animationend', { bubbles: true }), { animationName: 'mark-brush' }));
		expect(piece.classList.contains('fresh')).toBe(false);
		// Another animation ending (the drop cap's ink, say) leaves the rest alone.
		const other = container.querySelectorAll('mark.range-mark.fresh')[0]!;
		other.dispatchEvent(Object.assign(new Event('animationend', { bubbles: true }), { animationName: 'ink-in' }));
		expect(other.classList.contains('fresh')).toBe(true);
	});
});

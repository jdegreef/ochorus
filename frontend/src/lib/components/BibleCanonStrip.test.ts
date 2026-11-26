import { flushSync, mount, unmount } from 'svelte';
import { afterEach, describe, expect, it } from 'vitest';

import BibleCanonStrip from './BibleCanonStrip.svelte';
import { BIBLE_DIVISIONS } from '$lib/bible';
import type { BookSummary } from '$lib/library-public';

/**
 * Each division's name under the canon strip jumps to that division's books
 * on the /bible hub (`/bible/#gospels`), whose section carries the same id.
 */
const book = (position: number): BookSummary =>
	({
		slug: `book-${position}`,
		title: `Book ${position}`,
		series_position: position,
		word_count: 1000,
		chapter_count: 3,
		cover_color: '#335577'
	}) as unknown as BookSummary;

// jsdom has no ResizeObserver; the strip's scroll fades (scrollEdges) want one.
globalThis.ResizeObserver ??= class {
	observe() {}
	unobserve() {}
	disconnect() {}
} as unknown as typeof ResizeObserver;

let target: HTMLElement | undefined;
let component: Record<string, unknown> | undefined;

afterEach(() => {
	if (component) unmount(component);
	target?.remove();
	component = target = undefined;
});

describe('BibleCanonStrip division links', () => {
	it("links every division's name to its anchor, without a tab stop", () => {
		target = document.createElement('div');
		document.body.appendChild(target);
		const books = Array.from({ length: 66 }, (_, i) => book(i + 1));
		component = mount(BibleCanonStrip, { target, props: { books } }) as Record<string, unknown>;
		flushSync();
		const links = [...target.querySelectorAll<HTMLAnchorElement>('a.canon-label-name')];
		expect(links.map((a) => a.getAttribute('href'))).toEqual(
			BIBLE_DIVISIONS.map((d) => `#${d.id}`)
		);
		for (const a of links) expect(a.tabIndex).toBe(-1);
	});
});

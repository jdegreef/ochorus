import { flushSync, mount, tick, unmount } from 'svelte';
import { afterEach, describe, expect, it, vi } from 'vitest';

vi.mock('$lib/library-public', () => ({
	getBook: vi.fn(async () => ({
		slug: 'against-marcion',
		language: 'en',
		title: 'Against Marcion',
		author: { name: 'Tertullian' },
		parts: [],
		chapters: [
			{ order: 3, title: 'Book III', word_count: 19000 },
			{ order: 4, title: 'Book IV', word_count: 60545 }
		]
	}))
}));

import TocDrawer from './TocDrawer.svelte';

/**
 * A long chapter lists its own sections under it (bug #21), each a `?p=` link
 * into the chapter — the deep link a bookmark already uses — and only under
 * the chapter being read.
 */
let app: ReturnType<typeof mount> | null = null;
async function render(sections: { title: string; p: number }[]) {
	const target = document.createElement('div');
	document.body.append(target);
	app = mount(TocDrawer, {
		target,
		props: { slug: 'against-marcion', currentOrder: 4, sections, open: true }
	});
	await vi.waitFor(() => {
		flushSync();
		if (!document.querySelector('.toc-item')) throw new Error('not loaded');
	});
	await tick();
	return [...document.querySelectorAll<HTMLAnchorElement>('.toc-section')].map((a) => [
		a.textContent,
		a.getAttribute('href')
	]);
}

afterEach(() => {
	if (app) unmount(app);
	app = null;
	document.body.innerHTML = '';
});

describe('TocDrawer sections', () => {
	it("lists the current chapter's sections as links into it", async () => {
		const links = await render([
			{ title: 'Chapter I', p: 0 },
			{ title: 'Chapter II', p: 14 },
			{ title: 'Chapter III', p: 31 }
		]);
		expect(links).toEqual([
			['Chapter I', '/books/against-marcion/4/?p=0'],
			['Chapter II', '/books/against-marcion/4/?p=14'],
			['Chapter III', '/books/against-marcion/4/?p=31']
		]);
		// Under the current chapter, not another.
		const current = document.querySelector('.toc-item.current')!.closest('li')!;
		expect(current.querySelectorAll('.toc-section')).toHaveLength(3);
	});

	it('lists nothing when the chapter has no sections to offer', async () => {
		expect(await render([])).toEqual([]);
	});
});

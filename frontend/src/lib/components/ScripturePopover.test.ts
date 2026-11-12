import { flushSync, mount, unmount } from 'svelte';
import { afterEach, describe, expect, it } from 'vitest';

import ScripturePopover from './ScripturePopover.svelte';
import { scripture } from '$lib/scripture.svelte';

/**
 * "Read the whole chapter": the popover over a reference in any classic or
 * sermon offers the chapter in the library's own Bible — only where the API
 * names one (the book has an edition; the reference starts in a chapter of it).
 */
let app: ReturnType<typeof mount> | null = null;
const open = (bible_chapter: { slug: string; order: number } | null | undefined) => {
	const target = document.createElement('div');
	document.body.append(target);
	app = mount(ScripturePopover, { target });
	scripture.ref = 'Romans 8:28';
	scripture.href = '';
	scripture.loading = false;
	scripture.result = {
		reference: 'Romans 8:28',
		verses: [{ number: 28, text: 'We know that all things work together for good.' }],
		version: 'Open Word Bible',
		bible_chapter
	};
	scripture.open = true;
	flushSync();
	return [...document.querySelectorAll<HTMLAnchorElement>('.scripture-pop a')].map((a) =>
		a.getAttribute('href')
	);
};

afterEach(() => {
	scripture.open = false;
	scripture.result = null;
	flushSync();
	if (app) unmount(app);
	app = null;
	document.body.innerHTML = '';
});

describe('ScripturePopover', () => {
	it('links the whole chapter in the library’s own Bible', () => {
		expect(open({ slug: 'romans', order: 9 })).toEqual(['/books/romans/9/']);
	});

	it('offers no chapter where the library has no edition of the book', () => {
		expect(open(null)).toEqual([]);
		// An API from before the field.
		expect(open(undefined)).toEqual([]);
	});
});

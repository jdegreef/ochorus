import { afterEach, describe, expect, it, vi } from 'vitest';

import {
	CHAPTER_BODY_ATTR,
	chapterSeedTag,
	proseHtml,
	resetChapterSeed,
	takeChapterSeed,
	unrecorded
} from './chapterSeed';
import type { Chapter } from './library-public';

const chapter: Chapter = {
	order: 2,
	title: 'The Fruit of the Spirit is Love',
	body_html: '<p>He said "love" &amp; meant it.</p><p>Second</p>',
	word_count: 9,
	book_title: 'Absolute Surrender',
	book_slug: 'absolute-surrender',
	author_name: 'Andrew Murray',
	author_slug: 'andrew-murray',
	is_modern_edition: false,
	has_modern_edition: true,
	available_languages: ['en', 'es'],
	prev: { order: 1, title: 'Absolute Surrender' },
	next: { order: 3, title: '</script><script>alert(1)</script>' },
	scripture_refs: [],
	study_questions: []
} as unknown as Chapter;

/** The prerendered page as Svelte writes it: the seed in the head, and the
 *  prose inside the {@html} block's hydration markers. */
function prerendered(pathname: string, c: Chapter = chapter, language = 'en') {
	document.head.innerHTML = chapterSeedTag(c, language, pathname);
	document.body.innerHTML = `<div class="reading" ${CHAPTER_BODY_ATTR}><!--1a2b3c-->${c.body_html}<!----></div>`;
}

afterEach(() => {
	resetChapterSeed();
	document.head.innerHTML = '';
	document.body.innerHTML = '';
});

describe('chapter seed', () => {
	it('rebuilds the chapter from the seed and the prose in the DOM', () => {
		prerendered('/books/absolute-surrender/2/');
		const seeded = takeChapterSeed('/books/absolute-surrender/2/');
		expect(seeded?.language).toBe('en');
		// Every field but the body round-trips exactly; the body is the browser's
		// serialization of the same prose (`"` needs no entity in text).
		const { body_html, ...rest } = seeded!.data;
		const { body_html: _orig, ...expected } = chapter;
		expect(rest).toEqual(expected);
		expect(body_html).toBe('<p>He said "love" &amp; meant it.</p><p>Second</p>');
	});

	it('never carries the body, and cannot close its own script', () => {
		const tag = chapterSeedTag(chapter, 'en', '/books/absolute-surrender/2/');
		expect(tag).not.toContain('He said');
		expect(tag).not.toContain('body_html');
		expect(tag.match(/<\/script>/g)).toHaveLength(1);
		expect(tag.match(/</g)).toHaveLength(2);
	});

	it('keeps the resolved language — an English fallback under /es says en', () => {
		prerendered('/es/books/absolute-surrender/2/', chapter, 'en');
		expect(takeChapterSeed('/es/books/absolute-surrender/2/')?.language).toBe('en');
	});

	it('matches the page with or without its trailing slash', () => {
		prerendered('/books/absolute-surrender/2/');
		expect(takeChapterSeed('/books/absolute-surrender/2')).not.toBeNull();
	});

	it('answers only the first load: later navigations fetch', () => {
		prerendered('/books/absolute-surrender/2/');
		expect(takeChapterSeed('/books/absolute-surrender/2/')).not.toBeNull();
		// The DOM still holds a seed, but it is the app's now, not the prerender's.
		expect(takeChapterSeed('/books/absolute-surrender/2/')).toBeNull();
	});

	it('ignores a seed rendered for another page', () => {
		prerendered('/books/absolute-surrender/2/');
		expect(takeChapterSeed('/books/absolute-surrender/modern/2/')).toBeNull();
	});

	it('falls back to fetching when there is no seed, no prose, or a broken seed', () => {
		expect(takeChapterSeed('/books/absolute-surrender/2/')).toBeNull();

		resetChapterSeed();
		prerendered('/books/absolute-surrender/2/');
		document.body.innerHTML = '';
		expect(takeChapterSeed('/books/absolute-surrender/2/')).toBeNull();

		resetChapterSeed();
		prerendered('/books/absolute-surrender/2/');
		document.getElementById('chapter-seed')!.textContent = '{not json';
		expect(takeChapterSeed('/books/absolute-surrender/2/')).toBeNull();
	});

	it("strips only the {@html} block's hydration markers", () => {
		const div = document.createElement('div');
		div.innerHTML = '<!--x9y8--><p>a</p><p>b</p><!---->';
		expect(proseHtml(div)).toBe('<p>a</p><p>b</p>');
	});
});

describe('unrecorded', () => {
	it('hands the load a clone, so the response the load fetch saw is never read', async () => {
		const original = new Response('{"a":1}', { headers: { 'content-type': 'application/json' } });
		const f = vi.fn(async () => original);
		const res = await unrecorded(f as unknown as typeof fetch)('https://api.example.org/x');
		expect(res).not.toBe(original);
		expect(await res.json()).toEqual({ a: 1 });
		expect(original.bodyUsed).toBe(false);
	});
});

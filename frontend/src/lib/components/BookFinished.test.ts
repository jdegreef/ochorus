import { flushSync, mount, unmount } from 'svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { BookDetail, BookSummary } from '$lib/library-public';

/**
 * The end-of-book panel: shown only while the book is stamped finished (so it
 * arrives with the finish and leaves with its Undo), and offering the ways on
 * — the author's other books, a plan that reads this one.
 */
vi.mock('$lib/lang.svelte', () => ({ getLang: () => 'en' }));
const state = vi.hoisted(() => ({ finished: new Set<string>() }));
vi.mock('$lib/progress', () => ({
	isFinished: (slug: string) => state.finished.has(slug),
	allProgress: () =>
		[...state.finished].map((slug) => ({ slug, kind: 'book', finished_at: Date.now(), at: Date.now() })),
	bookProgressReader: () => (slug: string) => ({ started: false, finished: state.finished.has(slug) })
}));
const resume = vi.hoisted(() => ({ libraryBooks: vi.fn() }));
vi.mock('$lib/resumeBooks', () => resume);
const listPlans = vi.hoisted(() => vi.fn());
vi.mock('$lib/library-public', async (importOriginal) => ({
	...(await importOriginal<typeof import('$lib/library-public')>()),
	listPlans
}));
vi.mock('$lib/marks.svelte', () => ({ marks: { allByEdition: () => [] } }));
// Stand-ins for the parts with their own stores and tests: the reflection box
// (the journal), the download menu (offline/PWA) and the share button.
const stub = vi.hoisted(() => async () => ({ default: (await import('./Arrow.svelte')).default }));
vi.mock('$lib/components/notebook/ReflectBox.svelte', stub);
vi.mock('$lib/components/BookDownloadMenu.svelte', stub);
vi.mock('$lib/components/ShareButton.svelte', stub);

const { default: BookFinished } = await import('./BookFinished.svelte');

const summary = (slug: string, author = 'murray'): BookSummary =>
	({
		slug,
		title: slug,
		language: 'en',
		subtitle: '',
		source_type: 'public_domain',
		cover_color: '#123456',
		cover_url: '',
		chapter_count: 10,
		word_count: 1000,
		author: { slug: author, name: author === 'murray' ? 'Andrew Murray' : author, birth_year: 1828 },
		topics: []
	}) as unknown as BookSummary;

const book = {
	...summary('inner-chamber'),
	word_count: 32000,
	editions: [],
	related: [],
	chapters: [],
	pdf_url: '',
	epub_url: ''
} as unknown as BookDetail;

let target: HTMLElement;
let component: ReturnType<typeof mount> | null = null;
const settle = async () => {
	await new Promise((r) => setTimeout(r, 0));
	flushSync();
};
const show = async () => {
	component = mount(BookFinished, {
		target,
		props: { book, language: 'en', shareUrl: 'https://example.org/books/inner-chamber/' }
	});
	await settle();
};

describe('BookFinished', () => {
	beforeEach(() => {
		target = document.body.appendChild(document.createElement('div'));
		state.finished = new Set();
		resume.libraryBooks.mockResolvedValue([summary('inner-chamber'), summary('abide'), summary('other', 'bounds')]);
		listPlans.mockResolvedValue([
			{ slug: 'school-of-prayer', title: '31 Days in the School of Prayer', day_count: 31, covers: [{ kind: 'book', slug: 'inner-chamber', title: '', cover_url: '', cover_color: '#123456' }] },
			{ slug: 'unrelated', title: 'Unrelated', day_count: 7, covers: [] }
		]);
	});
	afterEach(() => {
		if (component) unmount(component);
		component = null;
		target.remove();
	});

	it('says nothing while the book is still being read', async () => {
		await show();
		expect(target.textContent?.trim()).toBe('');
	});

	it('arrives with the finish and leaves with its Undo', async () => {
		await show();
		state.finished.add('inner-chamber');
		window.dispatchEvent(new CustomEvent('ochorus:sync'));
		await settle();
		expect(target.querySelector('#finished-heading')?.textContent).toBe('inner-chamber');

		state.finished.delete('inner-chamber');
		window.dispatchEvent(new CustomEvent('ochorus:sync'));
		await settle();
		expect(target.querySelector('#finished-heading')).toBeNull();
	});

	it("counts the year's finished books and offers the ways on", async () => {
		state.finished.add('inner-chamber');
		await show();
		expect(target.querySelector('.year-tile')?.textContent).toContain('1');
		const hrefs = [...target.querySelectorAll('a')].map((a) => a.getAttribute('href') ?? '');
		expect(hrefs.some((h) => h.includes('/books/abide'))).toBe(true);
		expect(hrefs.some((h) => h.includes('/books/other'))).toBe(false);
		expect(hrefs.some((h) => h.includes('/plans/school-of-prayer'))).toBe(true);
		expect(hrefs.some((h) => h.includes('/plans/unrelated'))).toBe(false);
	});
});

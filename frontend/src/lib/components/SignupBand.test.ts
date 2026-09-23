import { flushSync, mount, unmount } from 'svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { BookSummary } from '$lib/library-public';

/**
 * The progress band names the reader's book, and draws that caption ONCE: from
 * the cached in-progress summaries when they have it, else only after the book
 * list lands — never a generic caption rewritten in place a moment later.
 */
vi.mock('$lib/auth.svelte', () => ({ auth: { enabled: true, initialized: true, user: null } }));
vi.mock('$lib/lang.svelte', () => ({ getLang: () => 'en' }));
const resume = vi.hoisted(() => ({
	cachedResumeBooks: vi.fn(),
	libraryBooks: vi.fn(),
	unfinishedBookSlugs: vi.fn()
}));
vi.mock('$lib/resumeBooks', () => resume);
vi.mock('$lib/progress', () => ({
	allProgress: () => [
		{ slug: 'all-of-grace', kind: 'book', order: 3, paragraph_index: 0, language: 'en', at: 1 }
	]
}));

const { default: SignupBand } = await import('./SignupBand.svelte');

const grace = {
	slug: 'all-of-grace',
	title: 'All of Grace',
	chapter_count: 20,
	author: { slug: 'spurgeon', name: 'C. H. Spurgeon' }
} as BookSummary;

let target: HTMLElement;
let component: ReturnType<typeof mount> | null = null;
const render = () => {
	component = mount(SignupBand, { target });
	flushSync();
};

describe('SignupBand progress caption', () => {
	beforeEach(() => {
		target = document.body.appendChild(document.createElement('div'));
		resume.unfinishedBookSlugs.mockReturnValue(['all-of-grace']);
		resume.libraryBooks.mockReset();
	});
	afterEach(() => {
		if (component) unmount(component);
		target.remove();
	});

	it('names the book at once from the cache, without a request', () => {
		resume.cachedResumeBooks.mockReturnValue([grace]);
		render();
		expect(target.textContent).toContain('All of Grace');
		expect(resume.libraryBooks).not.toHaveBeenCalled();
	});

	it('on a cache miss, shows nothing until the list lands — then the named caption', async () => {
		resume.cachedResumeBooks.mockReturnValue([]);
		let resolve!: (b: BookSummary[]) => void;
		resume.libraryBooks.mockReturnValue(new Promise((r) => (resolve = r)));
		render();
		expect(target.querySelector('section')).toBeNull(); // no generic caption first
		resolve([grace]);
		await new Promise((r) => setTimeout(r, 0)); // let then/catch/finally settle
		flushSync();
		expect(target.textContent).toContain('All of Grace');
	});

	it('still shows the band if the list fails — just without the book', async () => {
		resume.cachedResumeBooks.mockReturnValue([]);
		resume.libraryBooks.mockRejectedValue(new Error('offline'));
		render();
		await new Promise((r) => setTimeout(r, 0));
		flushSync();
		expect(target.querySelector('section')).not.toBeNull();
		expect(target.textContent).not.toContain('All of Grace');
	});
});

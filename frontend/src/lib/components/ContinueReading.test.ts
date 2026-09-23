import { flushSync, mount, unmount } from 'svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { CoverBook } from '$lib/library-public';

/**
 * "Continue reading" sits above the hero, so it must be its final height from
 * mount: cached books draw at once, and a work not drawable yet holds its
 * card's space with a placeholder until its list lands.
 */
vi.mock('$lib/lang.svelte', () => ({ getLang: () => 'en' }));
const resume = vi.hoisted(() => ({
	cachedResumeBooks: vi.fn(),
	libraryBooks: vi.fn(),
	unfinishedBookSlugs: vi.fn(() => ['grace', 'pilgrim'])
}));
vi.mock('$lib/resumeBooks', () => resume);
vi.mock('$lib/progress', () => ({
	allProgress: () =>
		['grace', 'pilgrim'].map((slug, i) => ({
			slug,
			kind: 'book',
			order: 2,
			paragraph_index: 0,
			language: 'en',
			at: 10 - i
		}))
}));

const { default: ContinueReading } = await import('./ContinueReading.svelte');

const book = (slug: string): CoverBook => ({
	slug,
	title: slug === 'grace' ? 'All of Grace' : "The Pilgrim's Progress",
	language: 'en',
	subtitle: '',
	source_type: 'public_domain',
	cover_color: '#123456',
	cover_url: `/covers/art/${slug}.jpg`,
	chapter_count: 10,
	word_count: 1000,
	author: { slug: 'a', name: 'A', birth_year: 1800 }
});

let target: HTMLElement;
let component: ReturnType<typeof mount> | null = null;
const cards = () => target.querySelectorAll('a[href^="/books/"]').length;
const holes = () => target.querySelectorAll('[data-testid="work-card-placeholder"]').length;

describe('ContinueReading', () => {
	beforeEach(() => {
		target = document.body.appendChild(document.createElement('div'));
	});
	afterEach(() => {
		if (component) unmount(component);
		target.remove();
	});

	it('draws cached books at mount, holding space only for the one not cached', async () => {
		resume.cachedResumeBooks.mockReturnValue([book('grace')]);
		let resolve!: (b: CoverBook[]) => void;
		resume.libraryBooks.mockReturnValue(new Promise((r) => (resolve = r)));
		component = mount(ContinueReading, { target });
		flushSync();
		expect(cards()).toBe(1);
		expect(holes()).toBe(1); // two cards' height from the start

		resolve([book('grace'), book('pilgrim')]);
		await new Promise((r) => setTimeout(r, 0));
		flushSync();
		expect(cards()).toBe(2);
		expect(holes()).toBe(0);
	});

	it('on a cold cache, reserves every card until the list lands', () => {
		resume.cachedResumeBooks.mockReturnValue([]);
		resume.libraryBooks.mockReturnValue(new Promise(() => {}));
		component = mount(ContinueReading, { target });
		flushSync();
		expect(cards()).toBe(0);
		expect(holes()).toBe(2);
	});

	it('drops the placeholders if the list fails, rather than holding them forever', async () => {
		resume.cachedResumeBooks.mockReturnValue([]);
		resume.libraryBooks.mockRejectedValue(new Error('offline'));
		component = mount(ContinueReading, { target });
		await new Promise((r) => setTimeout(r, 0));
		flushSync();
		expect(holes()).toBe(0);
	});
});

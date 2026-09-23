import { flushSync, mount, unmount } from 'svelte';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { CoverBook } from '$lib/library-public';

/**
 * "Continue reading" sits above the hero, so it must be its final height AND
 * order from mount: cached books draw at once, a work not drawable yet holds
 * its own slot with a placeholder, and a book the language lacks gets none.
 */
vi.mock('$lib/lang.svelte', () => ({ getLang: () => 'en' }));
const resume = vi.hoisted(() => ({
	cachedResumeBooks: vi.fn(),
	knownAbsentBooks: vi.fn(() => new Set<string>()),
	libraryBooks: vi.fn(),
	unfinishedBookSlugs: vi.fn(() => ['newer', 'grace'])
}));
vi.mock('$lib/resumeBooks', () => resume);
// Newest first, as allProgress returns them: `newer` was opened after `grace`.
const progress = vi.hoisted(() => ({ slugs: ['newer', 'grace'] }));
vi.mock('$lib/progress', () => ({
	allProgress: () =>
		progress.slugs.map((slug, i) => ({
			slug,
			kind: 'book',
			order: 2,
			paragraph_index: 0,
			language: 'en',
			at: 10 - i
		})),
	offerFinish: vi.fn(),
	unmarkFinished: vi.fn()
}));

const { default: ContinueReading } = await import('./ContinueReading.svelte');

const book = (slug: string): CoverBook => ({
	slug,
	title: slug,
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
const grid = () => [...target.querySelectorAll('.grid > *')];
const shape = () =>
	grid().map((el) =>
		el.matches('[data-testid="work-card-placeholder"]')
			? 'hole'
			: (el.querySelector('a')?.getAttribute('href')?.split('/')[2] ?? '?')
	);
const settle = async () => {
	await new Promise((r) => setTimeout(r, 0));
	flushSync();
};

describe('ContinueReading', () => {
	beforeEach(() => {
		target = document.body.appendChild(document.createElement('div'));
		progress.slugs = ['newer', 'grace'];
		resume.knownAbsentBooks.mockReturnValue(new Set());
	});
	afterEach(() => {
		if (component) unmount(component);
		target.remove();
	});

	it('holds the newer, uncached book its OWN slot, so the cached card never moves', async () => {
		resume.cachedResumeBooks.mockReturnValue([book('grace')]);
		let resolve!: (b: CoverBook[]) => void;
		resume.libraryBooks.mockReturnValue(new Promise((r) => (resolve = r)));
		component = mount(ContinueReading, { target });
		flushSync();
		expect(shape()).toEqual(['hole', 'grace']);
		expect(target.querySelector('section')?.getAttribute('aria-busy')).toBe('true');

		resolve([book('grace'), book('newer')]);
		await settle();
		expect(shape()).toEqual(['newer', 'grace']);
		expect(target.querySelector('section')?.getAttribute('aria-busy')).toBe('false');
	});

	it('reserves no slot for a book the language is known not to have', () => {
		resume.cachedResumeBooks.mockReturnValue([]);
		resume.knownAbsentBooks.mockReturnValue(new Set(['newer']));
		resume.libraryBooks.mockReturnValue(new Promise(() => {}));
		component = mount(ContinueReading, { target });
		flushSync();
		expect(shape()).toEqual(['hole']);
	});

	it('drops the placeholders if the list fails, rather than holding them forever', async () => {
		resume.cachedResumeBooks.mockReturnValue([]);
		resume.libraryBooks.mockRejectedValue(new Error('offline'));
		component = mount(ContinueReading, { target });
		await settle();
		expect(shape()).toEqual([]);
	});
});

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
	knownAbsent: vi.fn(() => new Set<string>()),
	recordSermonList: vi.fn(),
	libraryBooks: vi.fn(),
	unfinishedBookSlugs: vi.fn(() => ['newer', 'grace'])
}));
vi.mock('$lib/resumeBooks', () => resume);
const listSermons = vi.hoisted(() => vi.fn());
vi.mock('$lib/library-public', async (importOriginal) => ({
	...(await importOriginal<typeof import('$lib/library-public')>()),
	listSermons
}));
// Newest first, as allProgress returns them: `newer` was opened after `grace`.
// A `sermon:` prefix makes a sermon, as progress keys them.
const progress = vi.hoisted(() => ({ slugs: ['newer', 'grace'] }));
vi.mock('$lib/progress', () => ({
	allProgress: () =>
		progress.slugs.map((key, i) => ({
			slug: key.replace(/^sermon:/, ''),
			kind: key.startsWith('sermon:') ? 'sermon' : 'book',
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
		resume.knownAbsent.mockReturnValue(new Set());
		resume.recordSermonList.mockReset();
		listSermons.mockReset();
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
		resume.knownAbsent.mockReturnValue(new Set(['newer']));
		resume.libraryBooks.mockReturnValue(new Promise(() => {}));
		component = mount(ContinueReading, { target });
		flushSync();
		expect(shape()).toEqual(['hole']);
	});

	it('records the sermon list when it lands, so the next visit knows what this language lacks', async () => {
		progress.slugs = ['sermon:power-in-prayer', 'grace'];
		resume.cachedResumeBooks.mockReturnValue([book('grace')]);
		resume.libraryBooks.mockResolvedValue([book('grace')]);
		const sermons = [{ slug: 'another-sermon' }];
		listSermons.mockResolvedValue(sermons);
		component = mount(ContinueReading, { target });
		await settle();
		expect(resume.recordSermonList).toHaveBeenCalledWith('en', sermons);
	});

	it('reserves no slot for a SERMON the language is known not to have', () => {
		progress.slugs = ['sermon:english-only', 'grace'];
		resume.cachedResumeBooks.mockReturnValue([]);
		resume.knownAbsent.mockReturnValue(new Set(['sermon:english-only']));
		resume.libraryBooks.mockReturnValue(new Promise(() => {}));
		listSermons.mockReturnValue(new Promise(() => {}));
		component = mount(ContinueReading, { target });
		flushSync();
		expect(shape()).toEqual(['hole']); // the book's slot only
	});

	it('drops the placeholders if the list fails, rather than holding them forever', async () => {
		resume.cachedResumeBooks.mockReturnValue([]);
		resume.libraryBooks.mockRejectedValue(new Error('offline'));
		component = mount(ContinueReading, { target });
		await settle();
		expect(shape()).toEqual([]);
	});
});

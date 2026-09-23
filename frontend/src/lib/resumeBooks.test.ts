import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { BookSummary } from './library-public';
import { PROGRESS_KEY, READING_DATA_KEYS, RESUME_BOOKS_KEY } from './reading-schema';

const listBooks = vi.hoisted(() => vi.fn());
vi.mock('$lib/library-public', () => ({ listBooks }));

const { cachedResumeBooks, libraryBooks, resetLibraryBooks, unfinishedBookSlugs } = await import(
	'./resumeBooks'
);

const book = (slug: string) => ({ slug, title: slug }) as BookSummary;
const progress = (records: Record<string, { finished_at?: number }>) =>
	localStorage.setItem(
		PROGRESS_KEY,
		JSON.stringify(
			Object.fromEntries(
				Object.entries(records).map(([slug, r]) => [
					slug,
					{ order: 1, paragraph_index: 0, language: 'en', at: 1, ...r }
				])
			)
		)
	);

describe('resumeBooks', () => {
	beforeEach(() => {
		localStorage.clear();
		resetLibraryBooks();
		listBooks.mockReset();
	});

	it('counts only UNFINISHED book progress — a finished shelf needs no list', () => {
		progress({ a: {}, b: { finished_at: 5 } });
		expect(unfinishedBookSlugs()).toEqual(['a']);
	});

	it('shares one request per language between every block that asks', async () => {
		listBooks.mockResolvedValue([book('a')]);
		await Promise.all([libraryBooks('en'), libraryBooks('en')]);
		await libraryBooks('en'); // a late asker (the signup band, after auth) too
		expect(listBooks).toHaveBeenCalledTimes(1);
	});

	it('retries after a failure instead of remembering it', async () => {
		listBooks.mockRejectedValueOnce(new Error('offline')).mockResolvedValue([]);
		await expect(libraryBooks('en')).rejects.toThrow('offline');
		await expect(libraryBooks('en')).resolves.toEqual([]);
	});

	it('remembers just the in-progress books, per language, for the next visit', async () => {
		progress({ a: {}, b: { finished_at: 5 } });
		listBooks.mockResolvedValue([book('a'), book('b'), book('c')]);
		await libraryBooks('en');
		expect(cachedResumeBooks('en').map((b) => b.slug)).toEqual(['a']);
		expect(cachedResumeBooks('fr')).toEqual([]);
	});

	it('is wiped on sign-out with the rest of the reader\u2019s data', () => {
		// It says what someone is reading — on a shared device that must go.
		expect(READING_DATA_KEYS).toContain(RESUME_BOOKS_KEY);
	});

	it('survives a corrupt cache', () => {
		localStorage.setItem(RESUME_BOOKS_KEY, '{not json');
		expect(cachedResumeBooks('en')).toEqual([]);
	});
});

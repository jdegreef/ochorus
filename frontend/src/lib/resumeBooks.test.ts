import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { BookSummary } from './library-public';
import { PROGRESS_KEY, READING_DATA_KEYS, RESUME_BOOKS_KEY } from './reading-schema';

const listBooks = vi.hoisted(() => vi.fn());
vi.mock('$lib/library-public', async (importOriginal) => ({
	...(await importOriginal<typeof import('./library-public')>()),
	listBooks
}));

// A fresh module per test: the shared request lives in module state, and the
// production module has no reset hook to reach it.
const fresh = async () => {
	vi.resetModules();
	return import('./resumeBooks');
};

const book = (slug: string, extra: Partial<BookSummary> = {}) =>
	({
		slug,
		title: slug,
		language: 'en',
		subtitle: '',
		source_type: 'public_domain',
		cover_color: '#000000',
		cover_url: `/covers/${slug}.jpg`,
		chapter_count: 10,
		word_count: 1000,
		topics: [],
		created_at: 'x',
		author: { slug: 'a', name: 'A', bio: 'long bio', photo_url: '', birth_year: 1800, death_year: 1900 },
		...extra
	}) as BookSummary;
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
		listBooks.mockReset();
	});
	afterEach(() => vi.useRealTimers());

	it('counts only UNFINISHED book progress — a finished shelf needs no list', async () => {
		const { unfinishedBookSlugs } = await fresh();
		progress({ a: {}, b: { finished_at: 5 } });
		expect(unfinishedBookSlugs()).toEqual(['a']);
	});

	it('shares one request between blocks that ask minutes apart', async () => {
		const { libraryBooks } = await fresh();
		listBooks.mockResolvedValue([book('a')]);
		await Promise.all([libraryBooks('en'), libraryBooks('en')]);
		await libraryBooks('en'); // a late asker (the signup band, after auth)
		expect(listBooks).toHaveBeenCalledTimes(1);
	});

	it('refetches once the shared list is old — an all-day tab still sees new books', async () => {
		vi.useFakeTimers();
		const { libraryBooks } = await fresh();
		listBooks.mockResolvedValue([]);
		await libraryBooks('en');
		vi.advanceTimersByTime(11 * 60_000);
		await libraryBooks('en');
		expect(listBooks).toHaveBeenCalledTimes(2);
	});

	it('retries after a failure instead of remembering it', async () => {
		const { libraryBooks } = await fresh();
		listBooks.mockRejectedValueOnce(new Error('offline')).mockResolvedValue([]);
		await expect(libraryBooks('en')).rejects.toThrow('offline');
		await expect(libraryBooks('en')).resolves.toEqual([]);
	});

	it('remembers a book the moment it is opened — no visit to home needed', async () => {
		const { rememberResumeBook, cachedResumeBooks } = await fresh();
		progress({ grace: {} });
		rememberResumeBook('en', book('grace'));
		const [cached] = cachedResumeBooks('en');
		expect(cached.slug).toBe('grace');
		// Stored as the cover-sized projection, not the whole book.
		expect(Object.keys(cached.author).sort()).toEqual(['birth_year', 'name', 'slug']);
		expect(cached).not.toHaveProperty('topics');
	});

	it('keeps only books still in progress, in every language', async () => {
		const { rememberResumeBook, cachedResumeBooks, libraryBooks } = await fresh();
		progress({ a: {}, b: {} });
		rememberResumeBook('fr', book('b'));
		progress({ a: {}, b: { finished_at: 5 } }); // b finished since
		listBooks.mockResolvedValue([book('a'), book('b'), book('c')]);
		await libraryBooks('en');
		expect(cachedResumeBooks('en').map((b) => b.slug)).toEqual(['a']);
		expect(cachedResumeBooks('fr')).toEqual([]); // pruned, not left to linger
	});

	it('records which in-progress books a language lacks, and forgets once one is opened there', async () => {
		const { libraryBooks, knownAbsentBooks, rememberResumeBook } = await fresh();
		progress({ a: {}, swahiliOnly: {} });
		listBooks.mockResolvedValue([book('a')]);
		await libraryBooks('en');
		expect([...knownAbsentBooks('en')]).toEqual(['swahiliOnly']);
		rememberResumeBook('en', book('swahiliOnly')); // it exists after all
		expect(knownAbsentBooks('en').size).toBe(0);
	});

	it('a replaced request failing late does not evict the fresh one', async () => {
		vi.useFakeTimers();
		const { libraryBooks } = await fresh();
		let failOld!: (e: Error) => void;
		listBooks
			.mockReturnValueOnce(new Promise((_, reject) => (failOld = reject)))
			.mockResolvedValue([]);
		const old = libraryBooks('en').catch(() => {});
		vi.advanceTimersByTime(11 * 60_000); // expired: the next asker refetches
		await libraryBooks('en');
		failOld(new Error('stalled'));
		await old;
		await libraryBooks('en'); // still shares the fresh request
		expect(listBooks).toHaveBeenCalledTimes(2);
	});

	it('does not draw a cache written against another set of covers', async () => {
		const { cachedResumeBooks } = await fresh();
		localStorage.setItem(
			RESUME_BOOKS_KEY,
			JSON.stringify({ version: 'another-cover-set', books: { en: [book('a')] }, absent: {} })
		);
		expect(cachedResumeBooks('en')).toEqual([]);
	});

	it('is wiped on sign-out with the rest of the reader’s data', () => {
		expect(READING_DATA_KEYS).toContain(RESUME_BOOKS_KEY);
	});

	it('survives a corrupt cache', async () => {
		const { cachedResumeBooks } = await fresh();
		localStorage.setItem(RESUME_BOOKS_KEY, '{not json');
		expect(cachedResumeBooks('en')).toEqual([]);
	});
});

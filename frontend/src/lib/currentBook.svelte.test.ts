import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { BookSummary } from './library-public';
import { PROGRESS_KEY } from './reading-schema';

const listBooks = vi.hoisted(() => vi.fn());
vi.mock('$lib/library-public', async (importOriginal) => ({
	...(await importOriginal<typeof import('./library-public')>()),
	listBooks
}));

// A fresh store per test: `libraryBooks` shares its request in module state.
const fresh = async () => {
	vi.resetModules();
	return (await import('./currentBook.svelte')).currentBook;
};

const book = (slug: string) =>
	({
		slug,
		title: slug,
		language: 'en',
		subtitle: '',
		source_type: 'public_domain',
		cover_color: '#000000',
		cover_url: `/covers/art/${slug}.jpg`,
		chapter_count: 10,
		word_count: 1000,
		topics: [],
		created_at: 'x',
		author: { slug: 'a', name: 'A', bio: '', photo_url: '', birth_year: null, death_year: null }
	}) as BookSummary;

const progress = (records: Record<string, { at: number; order?: number; finished_at?: number }>) =>
	localStorage.setItem(
		PROGRESS_KEY,
		JSON.stringify(
			Object.fromEntries(
				Object.entries(records).map(([slug, r]) => [
					slug,
					{ order: 1, paragraph_index: 0, language: 'en', ...r }
				])
			)
		)
	);

// The first fresh import pulls in the library and message modules: seconds
// under a full parallel run, so the default 5s is too tight.
describe('currentBook', { timeout: 30_000 }, () => {
	beforeEach(() => {
		localStorage.clear();
		listBooks.mockReset();
	});

	it('resolves the newest unfinished book, with its own resume point', async () => {
		const current = await fresh();
		progress({ old: { at: 1 }, newest: { at: 3, order: 4 }, done: { at: 5, finished_at: 5 } });
		listBooks.mockResolvedValue([book('old'), book('newest'), book('done')]);
		current.refresh();
		await vi.waitFor(() => expect(current.item?.slug).toBe('newest'));
		expect(current.item).toMatchObject({ kind: 'book', key: 'newest', order: 4, chapterCount: 10 });
	});

	it('names the book at once, so the strip never reserves a card it then drops', async () => {
		const current = await fresh();
		progress({ cold: { at: 1 } });
		listBooks.mockReturnValue(new Promise(() => {}));
		current.refresh();
		// Nothing cached to draw yet, but WHICH book is already known.
		expect(current.item).toBeNull();
		expect(current.key).toBe('cold');
	});

	it('passes over a book the language lacks, and asks for no list with nothing open', async () => {
		const current = await fresh();
		progress({ old: { at: 1 }, missing: { at: 2 } });
		listBooks.mockResolvedValue([book('old')]);
		current.refresh();
		// The list lands, marks `missing` absent, and the next one stands in.
		await vi.waitFor(() => expect(current.item?.slug).toBe('old'));

		progress({ old: { at: 1, finished_at: 2 } });
		listBooks.mockClear();
		current.refresh();
		expect(current.item).toBeNull();
		expect(listBooks).not.toHaveBeenCalled();
	});
});

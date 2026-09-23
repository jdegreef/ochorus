import { browser } from '$app/environment';
import { listBooks, type BookSummary } from '$lib/library-public';
import { allProgress } from '$lib/progress';
import { RESUME_BOOKS_KEY } from '$lib/reading-schema';

/**
 * The book list the home page's personal blocks (Continue reading, Recommended
 * next, the signup band) draw from — fetched once, shared, and remembered.
 *
 * These blocks used to receive the list from the home `load`, which made the
 * prerendered front page wait on a live API call to hydrate. Fetching it in
 * each block instead fixed that, and broke three smaller things this module
 * puts back:
 *
 * - IMMEDIACY. "Continue reading" sits ABOVE the hero, so a strip that arrives
 *   after a round-trip pushes the whole front page down, late. So the summaries
 *   of the books in progress are kept in localStorage and drawn at mount, as
 *   the strip always was; the network copy refreshes them.
 * - ONE REQUEST. The blocks mount at different moments (the signup band waits
 *   for auth), so `apiFetch`'s in-flight dedupe did not always catch the second
 *   ~125 KB request. `libraryBooks` shares one promise per language.
 * - NO WASTED REQUEST. Only UNFINISHED book progress needs the list; a reader
 *   whose every book is finished has no card to draw.
 */

/** Slugs of the books the reader has started and not finished. */
export function unfinishedBookSlugs(progress = allProgress()): string[] {
	return progress.filter((p) => p.kind === 'book' && p.finished_at == null).map((p) => p.slug);
}

/** Per-language cache of in-progress book summaries. */
type Stored = Record<string, BookSummary[]>;

function readStored(): Stored {
	if (!browser) return {};
	try {
		const parsed = JSON.parse(localStorage.getItem(RESUME_BOOKS_KEY) || '{}');
		return parsed && typeof parsed === 'object' ? (parsed as Stored) : {};
	} catch {
		return {};
	}
}

/** The last-seen summaries of this language's in-progress books; [] if none. */
export function cachedResumeBooks(lang: string): BookSummary[] {
	const books = readStored()[lang];
	return Array.isArray(books) ? books : [];
}

function remember(lang: string, books: BookSummary[]): void {
	if (!browser) return;
	const wanted = new Set(unfinishedBookSlugs());
	const stored = readStored();
	stored[lang] = books.filter((b) => wanted.has(b.slug));
	try {
		localStorage.setItem(RESUME_BOOKS_KEY, JSON.stringify(stored));
	} catch {
		/* quota or blocked storage: the cache is a nicety, the fetch still worked */
	}
}

const pending = new Map<string, Promise<BookSummary[]>>();

/**
 * This language's full book list, requested at most once per page session.
 * A failure is not kept, so the next caller retries.
 */
export function libraryBooks(lang: string): Promise<BookSummary[]> {
	let request = pending.get(lang);
	if (!request) {
		request = listBooks(lang).then((books) => {
			remember(lang, books);
			return books;
		});
		request.catch(() => pending.delete(lang));
		pending.set(lang, request);
	}
	return request;
}

/** Test seam: forget the shared requests. */
export function resetLibraryBooks(): void {
	pending.clear();
}

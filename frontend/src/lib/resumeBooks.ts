import { browser, version } from '$app/environment';
import { listBooks, toCoverBook, type BookSummary, type CoverBook } from '$lib/library-public';
import { allProgress } from '$lib/progress';
import { RESUME_BOOKS_KEY } from '$lib/reading-schema';

/**
 * The book list the home page's personal blocks (Continue reading, Recommended
 * next, the signup band) draw from — fetched once, shared, and remembered.
 *
 * These blocks used to receive the list from the home `load`, which made the
 * prerendered front page wait on a live API call to hydrate. Fetching it in
 * each block instead fixed that, and broke smaller things this module puts back:
 *
 * - IMMEDIACY. "Continue reading" sits ABOVE the hero, so a strip that arrives
 *   after a round-trip pushes the whole front page down, late. So the reader's
 *   in-progress books are kept in localStorage and drawn at mount. They are
 *   written the moment a book is OPENED (`rememberResumeBook`, from the chapter
 *   page), not only when home fetches the list: the usual returning reader
 *   arrived on a chapter from search and never saw home that visit.
 * - NO STALE ART. Entries are stamped with the build `version`, and an entry
 *   from an older deploy is not drawn: covers and titles move with deploys, and
 *   drawing last deploy's cover only to swap it a moment later is a flicker.
 *   Where no current entry exists, the strip reserves its cards' space instead
 *   (see ContinueReading), so a miss costs a placeholder, not a shift.
 * - ONE REQUEST. The blocks mount at different moments (the signup band waits
 *   for auth), so `apiFetch`'s in-flight dedupe did not always catch the second
 *   ~125 KB request. `libraryBooks` shares one per language — for a few
 *   minutes, not the whole session, so a tab left open all day still sees books
 *   published since.
 * - NO WASTED REQUEST. Only UNFINISHED book progress needs the list.
 * - NOTHING LINGERS. Each write keeps only books still in progress, in every
 *   language, so a finished or abandoned book leaves the cache — which matters
 *   for a reader who never signs in, and so is never wiped by sign-out.
 */

/** Slugs of the books the reader has started and not finished. */
export function unfinishedBookSlugs(progress = allProgress()): string[] {
	return progress.filter((p) => p.kind === 'book' && p.finished_at == null).map((p) => p.slug);
}

/** Per-language in-progress books, stamped with the build that wrote them. */
interface Stored {
	version: string;
	books: Record<string, CoverBook[]>;
}

function readStored(): Stored['books'] {
	if (!browser) return {};
	try {
		const parsed = JSON.parse(localStorage.getItem(RESUME_BOOKS_KEY) || 'null') as Stored | null;
		// Another deploy's covers and titles: not drawn (see above).
		if (!parsed || parsed.version !== version || typeof parsed.books !== 'object') return {};
		return parsed.books ?? {};
	} catch {
		return {};
	}
}

/**
 * Merge `books` into `lang`'s entry and prune every language to the books
 * still in progress. `replace` swaps the language's entry wholesale (a fresh
 * full list is authoritative); otherwise the books are upserted.
 */
function write(lang: string, books: CoverBook[], replace: boolean): void {
	if (!browser) return;
	const inProgress = new Set(unfinishedBookSlugs());
	const stored = readStored();
	const current = replace ? [] : (stored[lang] ?? []);
	const bySlug = new Map(current.map((b) => [b.slug, b]));
	for (const b of books) bySlug.set(b.slug, b);
	stored[lang] = [...bySlug.values()];
	for (const [code, list] of Object.entries(stored)) {
		const kept = list.filter((b) => inProgress.has(b.slug));
		if (kept.length) stored[code] = kept;
		else delete stored[code];
	}
	try {
		localStorage.setItem(RESUME_BOOKS_KEY, JSON.stringify({ version, books: stored } satisfies Stored));
	} catch {
		/* quota or blocked storage: the cache is a nicety, never a failure */
	}
}

/** This build's cached in-progress books for `lang`; [] if none. */
export function cachedResumeBooks(lang: string): CoverBook[] {
	const books = readStored()[lang];
	return Array.isArray(books) ? books : [];
}

/** Remember one opened book, so the next visit to home can draw it at once. */
export function rememberResumeBook(lang: string, book: BookSummary): void {
	write(lang, [toCoverBook(book)], false);
}

/** How long one fetched list is shared before the next asker refetches. */
const SHARE_MS = 10 * 60_000;
const shared = new Map<string, { at: number; request: Promise<BookSummary[]> }>();

/**
 * This language's full book list, shared between the blocks that want it for
 * `SHARE_MS`. A failure is not kept, so the next caller retries.
 */
export function libraryBooks(lang: string): Promise<BookSummary[]> {
	const hit = shared.get(lang);
	if (hit && Date.now() - hit.at < SHARE_MS) return hit.request;
	const request = listBooks(lang).then((books) => {
		write(lang, books.map(toCoverBook), true);
		return books;
	});
	request.catch(() => shared.delete(lang));
	shared.set(lang, { at: Date.now(), request });
	return request;
}

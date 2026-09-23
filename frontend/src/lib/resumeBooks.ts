import { browser } from '$app/environment';
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
 * - NO STALE ART. The cache is stamped with `__COVERS_VERSION__`, a
 *   fingerprint of the set of cover files, and is not drawn once that moves: a
 *   cover that changed its URL (plate → painting) always adds or removes a file.
 *   Stamping with the BUILD instead threw the cache away on every one of the
 *   ~30 deploys a day, almost none of which touch a cover. (A title fix is
 *   text-only and rare; it refreshes when the list lands.) Where no drawable
 *   entry exists, the strip reserves its cards' space (see ContinueReading), so
 *   a miss costs a placeholder, not a shift.
 * - HONEST PLACEHOLDERS. Each full list also records which in-progress books
 *   the language does NOT have (`knownAbsent`), so the strip does not reserve a
 *   card for a book it will skip and then shrink.
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

/** Per-language in-progress books (and books known absent there), stamped
 *  with the cover set they were drawn against. */
interface Stored {
	version: string;
	books: Record<string, CoverBook[]>;
	absent: Record<string, string[]>;
}

const EMPTY = (): Omit<Stored, 'version'> => ({ books: {}, absent: {} });

function readStored(): Omit<Stored, 'version'> {
	if (!browser) return EMPTY();
	try {
		const parsed = JSON.parse(localStorage.getItem(RESUME_BOOKS_KEY) || 'null') as Stored | null;
		// Drawn against another set of covers: not drawn (see above).
		if (!parsed || parsed.version !== __COVERS_VERSION__ || typeof parsed.books !== 'object') {
			return EMPTY();
		}
		return { books: parsed.books ?? {}, absent: parsed.absent ?? {} };
	} catch {
		return EMPTY();
	}
}

/**
 * Merge `books` into `lang`'s entry and prune every language to the books
 * still in progress. A FULL list (`full`) is authoritative: it replaces the
 * language's entry and records which in-progress books it lacks. A single
 * opened book is upserted, and is by definition not absent.
 */
function write(lang: string, books: CoverBook[], full: boolean): void {
	if (!browser) return;
	const inProgress = new Set(unfinishedBookSlugs());
	const { books: stored, absent } = readStored();
	const bySlug = new Map((full ? [] : (stored[lang] ?? [])).map((b) => [b.slug, b]));
	for (const b of books) bySlug.set(b.slug, b);
	stored[lang] = [...bySlug.values()];
	absent[lang] = full
		? [...inProgress].filter((slug) => !bySlug.has(slug))
		: (absent[lang] ?? []).filter((slug) => !bySlug.has(slug));
	const prune = <T>(map: Record<string, T[]>, keep: (x: T) => boolean) => {
		for (const [code, list] of Object.entries(map)) {
			const kept = list.filter(keep);
			if (kept.length) map[code] = kept;
			else delete map[code];
		}
	};
	prune(stored, (b) => inProgress.has(b.slug));
	prune(absent, (slug) => inProgress.has(slug));
	try {
		localStorage.setItem(
			RESUME_BOOKS_KEY,
			JSON.stringify({ version: __COVERS_VERSION__, books: stored, absent } satisfies Stored)
		);
	} catch {
		/* quota or blocked storage: the cache is a nicety, never a failure */
	}
}

/** The cached in-progress books for `lang` that are safe to draw; [] if none. */
export function cachedResumeBooks(lang: string): CoverBook[] {
	const books = readStored().books[lang];
	return Array.isArray(books) ? books : [];
}

/** In-progress books the last full list for `lang` did not have. */
export function knownAbsentBooks(lang: string): Set<string> {
	const slugs = readStored().absent[lang];
	return new Set(Array.isArray(slugs) ? slugs : []);
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
	// Evict only THIS request: an older one that fails after being replaced
	// must not take the fresh entry with it.
	request.catch(() => {
		if (shared.get(lang)?.request === request) shared.delete(lang);
	});
	shared.set(lang, { at: Date.now(), request });
	return request;
}

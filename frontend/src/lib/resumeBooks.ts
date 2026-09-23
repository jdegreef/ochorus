import { browser } from '$app/environment';
import { listBooks, toCoverBook, type BookSummary, type CoverBook } from '$lib/library-public';
import { allProgress } from '$lib/progress';
import { RESUME_BOOKS_KEY, workSlugKey } from '$lib/reading-schema';

/**
 * The book list the home page's personal blocks (Continue reading, Recommended
 * next, the signup band) draw from — fetched once, shared, and remembered —
 * and the resume cache behind "Continue reading": the reader's in-progress
 * books, plus which in-progress books AND SERMONS each language lacks
 * (`knownAbsent`, `recordSermonList`). Sermon availability is cached here too,
 * not in a module of its own; look here first.
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
 * - NO CACHE RESETS. The cache is NOT keyed to the build or to the set of
 *   cover files: both moved on most deploys (a translated edition adds an og
 *   twin, a new book adds a cover) and every reset put placeholders back in
 *   front of every returning reader. An entry is validated where it matters,
 *   one at a time: every list that lands rewrites it, so a stale entry lives
 *   for at most one visit — and the only visible staleness is the rare case of
 *   a book IN PROGRESS whose cover moved since (plate → painting). Its old path
 *   then fails to load, BookCover draws its titled plate, and the new cover
 *   arrives with the list. `SCHEMA` only guards the stored SHAPE.
 * - HONEST PLACEHOLDERS. Each full book or sermon list also records which
 *   in-progress works the language does NOT have (`knownAbsent`), so the strip
 *   reserves no card for a work it will skip and then shrink.
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

/** Bump when the stored shape changes; a cache of another shape is ignored. */
const SCHEMA = 3;

/**
 * Per-language in-progress books, and the in-progress WORKS (keyed as progress
 * keys them: a bare slug for a book, `sermon:<slug>` for a sermon) that the
 * language's last list did not have.
 */
interface Stored {
	schema: number;
	books: Record<string, CoverBook[]>;
	absent: Record<string, string[]>;
}
type Store = Omit<Stored, 'schema'>;

const empty = (): Store => ({ books: {}, absent: {} });

function readStored(): Store {
	if (!browser) return empty();
	try {
		const parsed = JSON.parse(localStorage.getItem(RESUME_BOOKS_KEY) || 'null') as Stored | null;
		if (!parsed || parsed.schema !== SCHEMA) return empty();
		return { books: parsed.books ?? {}, absent: parsed.absent ?? {} };
	} catch {
		return empty();
	}
}

/** Keys of every unfinished book and sermon, as progress stores them. */
function inProgressKeys(): Set<string> {
	return new Set(
		allProgress()
			.filter((p) => (p.kind === 'book' || p.kind === 'sermon') && p.finished_at == null)
			.map((p) => workSlugKey(p.kind, p.slug))
	);
}

/** Apply `change`, prune everything to works still in progress, and save. */
function update(change: (store: Store, inProgress: Set<string>) => void): void {
	if (!browser) return;
	const store = readStored();
	const inProgress = inProgressKeys();
	change(store, inProgress);
	const prune = <T>(map: Record<string, T[]>, keep: (x: T) => boolean) => {
		for (const [code, list] of Object.entries(map)) {
			const kept = list.filter(keep);
			if (kept.length) map[code] = kept;
			else delete map[code];
		}
	};
	prune(store.books, (b) => inProgress.has(workSlugKey('book', b.slug)));
	prune(store.absent, (key) => inProgress.has(key));
	try {
		const next = JSON.stringify({ schema: SCHEMA, ...store } satisfies Stored);
		// Most calls change nothing (the same books, the same absences): skip
		// the synchronous write when the stored copy already says this.
		if (localStorage.getItem(RESUME_BOOKS_KEY) !== next) localStorage.setItem(RESUME_BOOKS_KEY, next);
	} catch {
		/* quota or blocked storage: the cache is a nicety, never a failure */
	}
}

/**
 * Record which in-progress works of `kind` a full list for `lang` lacks.
 * Called with every list that lands, so the mark is only ever one list old.
 */
function markAbsent(
	store: Store,
	inProgress: Set<string>,
	lang: string,
	kind: 'book' | 'sermon',
	present: Set<string>
): void {
	const others = (store.absent[lang] ?? []).filter(
		(key) => (kind === 'sermon') !== key.startsWith('sermon:')
	);
	const missing = [...inProgress].filter(
		(key) =>
			(kind === 'sermon') === key.startsWith('sermon:') &&
			!present.has(key.replace(/^sermon:/, ''))
	);
	store.absent[lang] = [...others, ...missing];
}

/** The cached in-progress books for `lang`; [] if none. */
export function cachedResumeBooks(lang: string): CoverBook[] {
	const books = readStored().books[lang];
	return Array.isArray(books) ? books : [];
}

/** Work keys (see `Stored`) of in-progress works `lang`'s last lists lacked. */
export function knownAbsent(lang: string): Set<string> {
	const keys = readStored().absent[lang];
	return new Set(Array.isArray(keys) ? keys : []);
}

/** A full sermon list for `lang` landed: note which in-progress sermons it lacks. */
export function recordSermonList(lang: string, sermons: { slug: string }[]): void {
	const present = new Set(sermons.map((s) => s.slug));
	update((store, inProgress) => markAbsent(store, inProgress, lang, 'sermon', present));
}

/** Remember one opened book, so the next visit to home can draw it at once. */
export function rememberResumeBook(lang: string, book: BookSummary): void {
	update((store) => {
		const list = (store.books[lang] ?? []).filter((b) => b.slug !== book.slug);
		store.books[lang] = [...list, toCoverBook(book)];
		// It exists in this language after all.
		store.absent[lang] = (store.absent[lang] ?? []).filter((key) => key !== book.slug);
	});
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
		update((store, inProgress) => {
			store.books[lang] = books.map(toCoverBook);
			markAbsent(store, inProgress, lang, 'book', new Set(books.map((b) => b.slug)));
		});
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

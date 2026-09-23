import type { BookSummary } from './library-public';
import type { FavoriteEntry } from './favorites.svelte';
import type { ProgressRecord, WorkKind } from './reading-schema';
import { bookProgressPercent } from './reading';

/**
 * The Bookshelf's three shelves — what the reader is reading, what they mean to
 * read, and what they've finished — built from the two things the device
 * already knows: the hearted books (favorites) and the reading positions
 * (progress).
 *
 * A book lands on exactly one shelf, and the reading state outranks the heart:
 *   - a stored `finished_at`            → Finished
 *   - any other reading position        → Reading (the same rule as /reading's
 *                                         "In progress", so the two pages agree)
 *   - hearted, never opened             → To read
 *
 * So a book the reader started without hearting still shows up — a bookshelf
 * that forgets the book on your bedside table isn't much of one. Books resolve
 * against the current-language catalog; a hearted book with no row in this
 * language comes back in `unresolved` (the page draws it as a pill so a save is
 * never silently lost), while an unhearted, unresolved reading position is
 * simply left off, as on /reading.
 */
export type ShelfStatus = 'reading' | 'toRead' | 'finished';

export type ShelfBook = {
	book: BookSummary;
	status: ShelfStatus;
	/** Hearted by the reader (as opposed to only started). */
	saved: boolean;
	/** Last-opened chapter and in-chapter paragraph, for a resume deep-link. */
	order: number | null;
	paragraph: number;
	/** Chapter meter 0–100 (100 once finished, 0 when unopened). */
	pct: number;
	/** The shelf's sort key: finished_at, last-read, or saved-at (ms). */
	at: number;
};

export type Shelves = {
	reading: ShelfBook[];
	toRead: ShelfBook[];
	finished: ShelfBook[];
	/** Hearted book slugs with no row in the current language. */
	unresolved: string[];
};

type ProgressRow = ProgressRecord & { slug: string; kind: WorkKind };

export function buildShelves(
	books: BookSummary[],
	favs: FavoriteEntry[],
	progress: ProgressRow[]
): Shelves {
	const bySlug = new Map(books.map((b) => [b.slug, b]));
	const savedAt = new Map(favs.filter((f) => f.kind === 'book').map((f) => [f.slug, f.at]));
	const shelves: Shelves = {
		reading: [],
		toRead: [],
		finished: [],
		unresolved: []
	};
	const placed = new Set<string>();

	for (const p of progress) {
		if (p.kind !== 'book' || placed.has(p.slug)) continue;
		const book = bySlug.get(p.slug);
		if (!book) continue;
		placed.add(p.slug);
		const finished = p.finished_at != null;
		(finished ? shelves.finished : shelves.reading).push({
			book,
			status: finished ? 'finished' : 'reading',
			saved: savedAt.has(p.slug),
			order: p.order,
			paragraph: p.paragraph_index,
			pct: finished ? 100 : bookProgressPercent(p.order, book.chapter_count),
			at: (finished ? p.finished_at : p.at) ?? p.at
		});
	}

	for (const [slug, at] of savedAt) {
		if (placed.has(slug)) continue;
		const book = bySlug.get(slug);
		if (!book) {
			shelves.unresolved.push(slug);
			continue;
		}
		shelves.toRead.push({
			book,
			status: 'toRead',
			saved: true,
			order: null,
			paragraph: 0,
			pct: 0,
			at
		});
	}

	const newestFirst = (a: ShelfBook, b: ShelfBook) => b.at - a.at;
	shelves.reading.sort(newestFirst);
	shelves.toRead.sort(newestFirst);
	shelves.finished.sort(newestFirst);
	return shelves;
}

/**
 * The books on one of the reader's own shelves (customShelves), drawn with
 * the same status marks as the built-in shelves: a book with a finished stamp
 * is Finished, one with a position is Reading, the rest are To read. `added`
 * is the shelf's book list, `slug -> added-at`; the shelf is ordered by when
 * each book went on it, newest first (the Sort control can reorder it). A
 * book with no row in this language is left off, like the built-in shelves'
 * reading positions.
 */
export function customShelfItems(
	added: Map<string, number>,
	books: BookSummary[],
	favs: FavoriteEntry[],
	progress: ProgressRow[]
): ShelfBook[] {
	const bySlug = new Map(books.map((b) => [b.slug, b]));
	const saved = new Set(favs.filter((f) => f.kind === 'book').map((f) => f.slug));
	const recOf = new Map(progress.filter((p) => p.kind === 'book').map((p) => [p.slug, p]));
	const items: ShelfBook[] = [];
	for (const [slug, at] of added) {
		const book = bySlug.get(slug);
		if (!book) continue;
		const p = recOf.get(slug);
		const status: ShelfStatus = !p ? 'toRead' : p.finished_at != null ? 'finished' : 'reading';
		items.push({
			book,
			status,
			saved: saved.has(slug),
			order: p ? p.order : null,
			paragraph: p ? p.paragraph_index : 0,
			pct: !p ? 0 : status === 'finished' ? 100 : bookProgressPercent(p.order, book.chapter_count),
			at
		});
	}
	return items.sort((a, b) => b.at - a.at);
}

export type ShelfSort = 'recent' | 'title' | 'author' | 'shortest' | 'longest';
export const SHELF_SORTS: ShelfSort[] = ['recent', 'title', 'author', 'shortest', 'longest'];

/** A book's length for sorting: its words, else a rough count from chapters. */
const lengthOf = (b: BookSummary) => b.word_count ?? b.chapter_count * 4000;

/**
 * Reorder a shelf. `recent` keeps the shelf's own order (each shelf's clock:
 * last read, saved, finished or added), so it returns the input as is. Title
 * and author compare in the reader's language (`locale`), so accented and
 * non-Latin titles sort the way that language does.
 */
export function sortShelf(items: ShelfBook[], mode: ShelfSort, locale = 'en'): ShelfBook[] {
	if (mode === 'recent') return items;
	const collator = new Intl.Collator(locale, { sensitivity: 'base', numeric: true });
	const byTitle = (a: ShelfBook, b: ShelfBook) => collator.compare(a.book.title, b.book.title);
	const sorted = [...items];
	if (mode === 'title') sorted.sort(byTitle);
	else if (mode === 'author')
		sorted.sort((a, b) => collator.compare(a.book.author.name, b.book.author.name) || byTitle(a, b));
	else if (mode === 'shortest') sorted.sort((a, b) => lengthOf(a.book) - lengthOf(b.book) || byTitle(a, b));
	else sorted.sort((a, b) => lengthOf(b.book) - lengthOf(a.book) || byTitle(a, b));
	return sorted;
}

/** Where a shelf book's link goes: the exact resume point for a book being
 *  read, otherwise the book's own page (to begin, or to revisit). */
export function shelfHref(item: ShelfBook): string {
	if (item.status === 'reading' && item.order) {
		const p = item.paragraph > 0 ? `?p=${item.paragraph}` : '';
		return `/books/${item.book.slug}/${item.order}${p}`;
	}
	return `/books/${item.book.slug}`;
}

/**
 * A book's spine in the spines view, in px at full scale. Thickness follows
 * the book's length (word count, else chapters) so a long work looks it;
 * height varies a little per book — steadily, from its slug — so a shelf of
 * spines is uneven the way real books are, but doesn't reshuffle on reload.
 */
export function spineSize(book: Pick<BookSummary, 'slug' | 'word_count' | 'chapter_count'>): {
	width: number;
	height: number;
} {
	const bulk = book.word_count ? book.word_count / 7000 : book.chapter_count * 0.9;
	const width = Math.round(22 + Math.min(22, Math.max(0, bulk)));
	let h = 0;
	for (const c of book.slug) h = (h * 31 + c.charCodeAt(0)) >>> 0;
	const height = 150 + (h % 6) * 7; // 150–185
	return { width, height };
}

/**
 * Pack spines into shelf rows, left to right, starting a new row when the next
 * spine won't fit in `avail` px (`gap` between spines). Returns item indices
 * per row. A spine wider than a whole row still gets a row of its own.
 */
export function packRows(widths: number[], avail: number, gap: number): number[][] {
	const rows: number[][] = [];
	let row: number[] = [];
	let used = 0;
	widths.forEach((w, i) => {
		const need = row.length ? used + gap + w : w;
		if (row.length && need > avail) {
			rows.push(row);
			row = [i];
			used = w;
		} else {
			row.push(i);
			used = need;
		}
	});
	if (row.length) rows.push(row);
	return rows;
}

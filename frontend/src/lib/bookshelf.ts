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

/** Where a shelf book's link goes: the exact resume point for a book being
 *  read, otherwise the book's own page (to begin, or to revisit). */
export function shelfHref(item: ShelfBook): string {
	if (item.status === 'reading' && item.order) {
		const p = item.paragraph > 0 ? `?p=${item.paragraph}` : '';
		return `/books/${item.book.slug}/${item.order}${p}`;
	}
	return `/books/${item.book.slug}`;
}

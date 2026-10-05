import { favorites, type FavoriteEntry } from './favorites.svelte';
import { allProgress } from './progress';
import { marks } from './marks.svelte';
import { bookmarks } from './bookmarks.svelte';
import { journal } from './journal.svelte';
import { journalStats, type JournalStore } from './journal';
import { planProgress } from './planProgress.svelte';
import type { Mark } from './reading-schema';

/**
 * What a signed-out reader has already saved on this device, counted for the
 * Bookshelf / Notebook sign-up pitch: "Your bookshelf is waiting — 7 books,
 * 2 in progress…". Everything here is device-local and merges into the
 * account on sign-in, so it is exactly what an account would keep.
 *
 * `summarizeSaved` is pure (tested); `readSavedSummary` gathers its input from
 * the stores and only runs in the browser, where they live.
 */

export interface SavedCount {
	/** Message key of the chip's label (an existing, translated noun). */
	labelKey: string;
	count: number;
}

export interface SavedSummary {
	/** Non-zero counts, most telling first, at most four. */
	chips: SavedCount[];
	/** Every distinct item an account would keep, including those past the
	 *  four chips — a book both saved and being read counts once. */
	total: number;
}

export interface SavedInput {
	favorites: Pick<FavoriteEntry, 'kind' | 'slug'>[];
	/** Slugs of books with a reading place that aren't finished. */
	booksInProgress: string[];
	/** Slugs of started reading plans. */
	plansStarted: string[];
	/**
	 * Every stored mark, with its work. A mark id is unique only within its
	 * work (one highlight can also be several segments sharing an id), so a
	 * highlight is counted by work + id.
	 */
	marks: (Pick<Mark, 'id' | 'note'> & { work: string })[];
	bookmarks: number;
	journal: JournalStore;
}

const MAX_CHIPS = 4;

export function summarizeSaved(kind: 'shelf' | 'notebook', input: SavedInput): SavedSummary {
	let rows: SavedCount[];
	let total: number;
	if (kind === 'shelf') {
		const slugs = (k: FavoriteEntry['kind']) =>
			new Set(input.favorites.filter((f) => f.kind === k).map((f) => f.slug));
		const books = slugs('book');
		const plans = new Set([...slugs('plan'), ...input.plansStarted]);
		const reading = new Set(input.booksInProgress);
		rows = [
			{ labelKey: 'fav.groupBooks', count: books.size },
			{ labelKey: 'fav.shelfReading', count: reading.size },
			{ labelKey: 'fav.groupSermons', count: slugs('sermon').size },
			{ labelKey: 'fav.groupPlans', count: plans.size },
			{ labelKey: 'fav.groupQuotes', count: slugs('quote').size },
			{ labelKey: 'fav.groupAuthors', count: slugs('author').size },
			{ labelKey: 'fav.groupTopics', count: slugs('topic').size },
			{ labelKey: 'fav.groupArticles', count: slugs('article').size }
		];
		// A book that is both saved and being read is one thing kept, not two.
		const otherFavs = input.favorites.filter((f) => f.kind !== 'book' && f.kind !== 'plan').length;
		total = new Set([...books, ...reading]).size + plans.size + otherFavs;
	} else {
		const ids = new Map<string, boolean>();
		for (const m of input.marks) {
			const key = `${m.work}#${m.id}`;
			ids.set(key, (ids.get(key) ?? false) || !!m.note);
		}
		const noted = [...ids.values()].filter(Boolean).length;
		const stats = journalStats(input.journal);
		rows = [
			{ labelKey: 'settings.statHighlights', count: ids.size - noted },
			{ labelKey: 'settings.statNotes', count: noted + stats.notes },
			{ labelKey: 'settings.statBookmarks', count: input.bookmarks },
			{ labelKey: 'notebook.tabPrayers', count: stats.prayers + stats.answered }
		];
		total = rows.reduce((n, r) => n + r.count, 0);
	}
	return { chips: rows.filter((r) => r.count > 0).slice(0, MAX_CHIPS), total };
}

/** The summary for this device's stores. Browser only. */
export function readSavedSummary(kind: 'shelf' | 'notebook'): SavedSummary {
	return summarizeSaved(kind, {
		favorites: favorites.all(),
		booksInProgress: allProgress()
			.filter((p) => p.kind === 'book' && p.finished_at == null)
			.map((p) => p.slug),
		plansStarted: planProgress.started().map((p) => p.slug),
		marks: marks
			.allByEdition('en')
			.flatMap((w) => w.marks.map((m) => ({ ...m, work: `${w.kind}:${w.slug}:${w.order}` }))),
		bookmarks: bookmarks.all().length,
		journal: journal.store
	});
}

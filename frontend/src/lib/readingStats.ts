import { allProgress } from './progress';
import { readJSON } from './persisted';
import {
	MARKS_KEY,
	FAVORITES_KEY,
	BOOKMARKS_KEY,
	isFinishedNow,
	lastFinishOf,
	resumeOrderOf,
	type MarksStore,
	type BookmarksStore,
	type WorkKind
} from './reading-schema';
import { loadWorkTitles, unslug } from './workTitles';

/**
 * "Your reading" — device-local reading stats and recent history, derived from
 * the same localStorage the reader already writes (progress, marks, bookmarks,
 * favorites). No streak: a real streak needs a per-day activity log, and
 * progress only keeps the latest timestamp per work — so we show honest totals
 * and a recent-reading list rather than a number we can't back up.
 *
 * "Finished" is now the stored `finished_at` stamp on each progress record — an
 * explicit, synced fact that counts for every readable kind — not the old guess
 * (a book whose last-opened chapter was its last), which only worked for books,
 * double-counted finished books as "in progress", and re-broke when a book was
 * re-imported at a different length. `inProgress` therefore EXCLUDES finished
 * works.
 *
 * A REREAD is the one overlap, on purpose: `finished` counts every work ever
 * finished (the first completion, `finished_at`, is history — starting a book
 * again must not take a finish away), while `inProgress` counts what is being
 * read now (`isFinishedNow`), and a book started again is being read.
 */

export interface ReadingStats {
	inProgress: number;
	finished: number;
	highlights: number;
	notes: number;
	favorites: number;
	bookmarks: number;
}

export interface HistoryItem {
	kind: WorkKind;
	slug: string;
	title: string;
	author: string;
	/** Last chapter opened (1 for single-document sermons/bios). */
	order: number;
	/** When it was last read (epoch ms). */
	at: number;
	finished: boolean;
	/** When it was finished (epoch ms), or null while in progress — sorts the
	 *  finished shelf by completion date rather than last-read. */
	finishedAt: number | null;
}

/** Pure counts straight from localStorage — no network. */
export function readingCounts(): ReadingStats {
	const marks = readJSON<MarksStore>(MARKS_KEY, {});
	const favorites = readJSON<Record<string, number>>(FAVORITES_KEY, {});
	const bookmarks = readJSON<BookmarksStore>(BOOKMARKS_KEY, {});
	let highlights = 0;
	let notes = 0;
	for (const entry of Object.values(marks)) {
		for (const m of entry.m ?? []) {
			highlights += 1;
			if (m.note) notes += 1;
		}
	}
	let bookmarkCount = 0;
	for (const list of Object.values(bookmarks)) bookmarkCount += list?.length ?? 0;
	const progress = allProgress();
	const finished = progress.filter((p) => p.finished_at != null).length;
	return {
		// "In progress" is what's still being read — finished works have left it,
		// unless they are being read again.
		inProgress: progress.filter((p) => !isFinishedNow(p)).length,
		finished,
		highlights,
		notes,
		favorites: Object.keys(favorites).length,
		bookmarks: bookmarkCount
	};
}

/**
 * Counts + the resolved reading history, newest-read first. "Finished" is the
 * stored `finished_at` stamp (see `readingCounts`), so it needs no catalog — but
 * the catalogs are still fetched to resolve titles/authors (best-effort — an
 * unresolved slug falls back to a de-slugged label). The caller splits the
 * history into "currently reading" (finished === false) and a finished shelf.
 */
export async function collectReadingActivity(
	language: string
): Promise<{ stats: ReadingStats; history: HistoryItem[] }> {
	const titles = await loadWorkTitles(language);

	const history: HistoryItem[] = allProgress().map((p) => {
		const m = titles[p.kind].get(p.slug);
		return {
			kind: p.kind,
			slug: p.slug,
			title: m?.title ?? unslug(p.slug),
			author: m?.author ?? '',
			order: resumeOrderOf(p),
			at: p.at,
			// Where it stands now: a reread is on the reading list again.
			finished: isFinishedNow(p),
			finishedAt: isFinishedNow(p) ? lastFinishOf(p) : null
		};
	});

	return { stats: readingCounts(), history };
}

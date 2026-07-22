import { allProgress } from './progress';
import { readJSON } from './persisted';
import {
	MARKS_KEY,
	FAVORITES_KEY,
	BOOKMARKS_KEY,
	type MarksStore,
	type BookmarksStore,
	type WorkKind
} from './reading-schema';
import { listBooks, listSermons, listAuthors } from './library-public';

/**
 * "Your reading" — device-local reading stats and recent history, derived from
 * the same localStorage the reader already writes (progress, marks, bookmarks,
 * favorites). No streak: a real streak needs a per-day activity log, and
 * progress only keeps the latest timestamp per work — so we show honest totals
 * and a recent-reading list rather than a number we can't back up.
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
}

/** Pure counts straight from localStorage — no network. */
export function readingCounts(): Omit<ReadingStats, 'finished'> {
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
	return {
		inProgress: allProgress().length,
		highlights,
		notes,
		favorites: Object.keys(favorites).length,
		bookmarks: bookmarkCount
	};
}

function unslug(slug: string): string {
	return slug.replace(/-/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

/**
 * Counts + a "finished" tally (a book whose last-opened chapter is its last
 * chapter) + the resolved recent-reading history, newest first. Fetches the
 * catalogs for titles and chapter counts (best-effort — an unresolved slug
 * falls back to a de-slugged label and can't be "finished").
 */
export async function collectReadingActivity(
	language: string
): Promise<{ stats: ReadingStats; history: HistoryItem[] }> {
	const counts = readingCounts();
	const [books, sermons, authors] = await Promise.all([
		listBooks(language).catch(() => []),
		listSermons(language).catch(() => []),
		listAuthors(language).catch(() => [])
	]);
	const bookMeta = new Map(
		books.map((b) => [b.slug, { title: b.title, author: b.author?.name ?? '', chapters: b.chapter_count }])
	);
	const sermonMeta = new Map(sermons.map((s) => [s.slug, { title: s.title, author: s.author?.name ?? '' }]));
	const bioMeta = new Map(authors.map((a) => [a.slug, { title: a.name, author: a.name }]));

	let finished = 0;
	const history: HistoryItem[] = allProgress().map((p) => {
		let title = unslug(p.slug);
		let author = '';
		let done = false;
		if (p.kind === 'book') {
			const m = bookMeta.get(p.slug);
			if (m) {
				title = m.title;
				author = m.author;
				done = m.chapters > 0 && p.order >= m.chapters;
			}
		} else if (p.kind === 'sermon') {
			const m = sermonMeta.get(p.slug);
			if (m) {
				title = m.title;
				author = m.author;
			}
		} else if (p.kind === 'bio') {
			const m = bioMeta.get(p.slug);
			if (m) {
				title = m.title;
				author = m.author;
			}
		}
		if (done) finished += 1;
		return { kind: p.kind, slug: p.slug, title, author, order: p.order, at: p.at, finished: done };
	});

	return { stats: { ...counts, finished }, history };
}

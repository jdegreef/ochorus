import { allProgress } from './progress';
import { workSlugKey } from './reading-schema';
import { bookProgressPercent } from './reading';
import type { BookSummary, SermonSummary } from './library-public';

/**
 * One in-progress (or just-finished) work, resolved against the public catalogs
 * for its title, cover and progress — the shape both the home "Continue reading"
 * strip and the /reading page render through `WorkCard`, so the two can't drift
 * in what a resume card looks like or how its deep-link is built.
 *
 * These are structured fields, not a formatted line: `WorkCard` composes the
 * caption (a chapter meter, a finished tally, or a sermon's reference) at the
 * single render site, so the wording lives in one place rather than being baked
 * here and overridden by a caller. Progress is device-local (`allProgress()`);
 * a work with no row in the current language is dropped rather than shown as a
 * bare slug. Only books and sermons are carried, matching the strip — a
 * biography's reading position, rare and chapter-less, has no resume card here.
 */
export type ResumeItem = {
	kind: 'book' | 'sermon';
	/** The work's own slug — for the finish / un-finish actions on the card. */
	slug: string;
	/** Stable list key (`slug` for books, `sermon:slug` for sermons). */
	key: string;
	/** Deep-link back to the exact resume point, before localisation. */
	href: string;
	title: string;
	author: string;
	/** The full book, for `<BookCover>` to draw its title; absent for sermons. */
	book?: BookSummary;
	/** Chapter meter 0–100 for books; null for single-document sermons. */
	pct: number | null;
	/** Last-opened chapter and total (books only) — the caption's numbers. */
	order?: number;
	chapterCount?: number;
	/** The sermon's reference (may be ''); absent for books. */
	scriptureRef?: string;
	/**
	 * Whether the reader has FINISHED this work — the stored `finished_at` stamp
	 * (reaching the end, or an explicit mark), the same fact the "Finished" total
	 * counts, so the tile and the /reading section agree. Works for sermons too,
	 * not just books. The strip drops finished works; /reading splits on this.
	 */
	finished: boolean;
};

/**
 * Resolve device-local reading progress into resume cards, newest first.
 * `books`/`sermons` are the current-language catalogs the caller already has.
 * No slicing — the strip takes its own head; /reading shows them all.
 */
export function buildResumeItems(books: BookSummary[], sermons: SermonSummary[]): ResumeItem[] {
	const bookBySlug = new Map(books.map((b) => [b.slug, b]));
	const sermonBySlug = new Map(sermons.map((s) => [s.slug, s]));
	return allProgress()
		.map((p): ResumeItem | null => {
			if (p.kind === 'sermon') {
				const sermon = sermonBySlug.get(p.slug);
				if (!sermon) return null;
				const resume = p.paragraph_index > 0 ? `?p=${p.paragraph_index}` : '';
				return {
					kind: 'sermon',
					slug: p.slug,
					key: workSlugKey(p.kind, p.slug),
					href: `/sermons/${p.slug}${resume}`,
					title: sermon.title,
					author: sermon.author.name,
					pct: null,
					scriptureRef: sermon.scripture_ref,
					finished: p.finished_at != null
				};
			}
			// Only books past this point — a biography's position has no resume card.
			if (p.kind !== 'book') return null;
			const book = bookBySlug.get(p.slug);
			if (!book) return null;
			return {
				kind: 'book',
				slug: p.slug,
				key: workSlugKey(p.kind, p.slug),
				href: `/books/${book.slug}/${p.order}`,
				title: book.title,
				author: book.author.name,
				book,
				pct: bookProgressPercent(p.order, book.chapter_count),
				order: p.order,
				chapterCount: book.chapter_count,
				finished: p.finished_at != null
			};
		})
		.filter((x): x is ResumeItem => x !== null);
}

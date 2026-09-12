import { allProgress } from './progress';
import { workSlugKey } from './reading-schema';
import { bookProgressPercent, isBookFinished } from './reading';
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
	 * A book whose last-opened chapter is its last — the same rule the "Finished"
	 * total uses (`isBookFinished`), so the tile count and the /reading section
	 * agree. Always false for sermons. The strip ignores this and shows every
	 * item; /reading splits on it.
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
					key: workSlugKey(p.kind, p.slug),
					href: `/sermons/${p.slug}${resume}`,
					title: sermon.title,
					author: sermon.author.name,
					pct: null,
					scriptureRef: sermon.scripture_ref,
					finished: false
				};
			}
			// Only books past this point — a biography's position has no resume card.
			if (p.kind !== 'book') return null;
			const book = bookBySlug.get(p.slug);
			if (!book) return null;
			return {
				kind: 'book',
				key: workSlugKey(p.kind, p.slug),
				href: `/books/${book.slug}/${p.order}`,
				title: book.title,
				author: book.author.name,
				book,
				pct: bookProgressPercent(p.order, book.chapter_count),
				order: p.order,
				chapterCount: book.chapter_count,
				finished: isBookFinished(p.order, book.chapter_count)
			};
		})
		.filter((x): x is ResumeItem => x !== null);
}

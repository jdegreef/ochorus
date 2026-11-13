/**
 * The Bible hub (/bible/): the Bible's books in the library, in canonical
 * order, grouped Old Testament / New Testament and then by division.
 *
 * The books are the `the-bible` series, each at its place in the canon
 * (`series_position` = 1 Genesis … 66 Revelation; `build_owb_book` sets it from
 * the Open Word Bible's own book order). The library holds a growing subset of
 * the 66, so the grouping keeps only the divisions — and testaments — that have
 * a book, and is pure so it can be tested without a page.
 */

import { CANON } from '$lib/sermonCanon';
import { bookChapterPath } from '$lib/reading-schema';

/** The series whose books the hub lists. */
export const BIBLE_SERIES = 'the-bible';
/** The hub's path; prerenders to bible/index.html (isSlashedPath). */
export const BIBLE_PATH = '/bible';

/**
 * The UI locales whose chrome (footer, palette, More sheet) links the hub.
 *
 * The page itself needs no list — it 404s where the series has no book
 * (no English fallback), and its hreflang and sitemap row are derived from the
 * API's own per-language presence. But the chrome is drawn without a request,
 * and a footer link in a locale with no Bible would send the prerender crawl to
 * that 404 and fail the build. Add a locale here when its Bible books ship.
 */
export const BIBLE_LOCALES: readonly string[] = ['en'];

/** Whether the chrome links the hub for a reader in `locale`. */
export const bibleIn = (locale: string) => BIBLE_LOCALES.includes(locale);

export type Testament = 'old' | 'new';

export interface BibleDivision {
	id: string;
	testament: Testament;
	/** Canonical numbers, inclusive. */
	first: number;
	last: number;
}

/** The divisions, in canonical order. Every number 1–66 is in exactly one. */
export const BIBLE_DIVISIONS: readonly BibleDivision[] = [
	{ id: 'law', testament: 'old', first: 1, last: 5 },
	{ id: 'history', testament: 'old', first: 6, last: 17 },
	{ id: 'wisdom', testament: 'old', first: 18, last: 22 },
	{ id: 'major-prophets', testament: 'old', first: 23, last: 27 },
	{ id: 'minor-prophets', testament: 'old', first: 28, last: 39 },
	{ id: 'gospels', testament: 'new', first: 40, last: 43 },
	{ id: 'acts', testament: 'new', first: 44, last: 44 },
	{ id: 'paul', testament: 'new', first: 45, last: 57 },
	{ id: 'general-letters', testament: 'new', first: 58, last: 65 },
	{ id: 'revelation', testament: 'new', first: 66, last: 66 }
];

/** The division a canonical number falls in, or null outside 1–66. */
export const divisionOf = (position: number | null | undefined): BibleDivision | null =>
	position == null
		? null
		: (BIBLE_DIVISIONS.find((d) => position >= d.first && position <= d.last) ?? null);

/** The catalogue key of a division's heading (`bible_division_<id>`). */
export const divisionKey = (id: string) => `bible.division_${id.replace(/-/g, '_')}`;

/** The catalogue key of a testament's heading. */
export const testamentKey = (testament: Testament) =>
	testament === 'old' ? 'bible.oldTestament' : 'bible.newTestament';

export interface DivisionGroup<T> {
	division: BibleDivision;
	books: T[];
}

export interface TestamentGroup<T> {
	testament: Testament;
	divisions: DivisionGroup<T>[];
}

/**
 * The books by testament and division, in canonical order, keeping only the
 * groups that have a book. A book with no canonical number (or one outside
 * 1–66) has no place in the canon to show it at, so it is left out — the
 * series sets one on every Bible book.
 */
export function groupBible<T extends { series_position?: number | null }>(
	books: readonly T[]
): TestamentGroup<T>[] {
	const sorted = books
		.filter((b) => divisionOf(b.series_position))
		.sort((a, b) => a.series_position! - b.series_position!);
	return byTestament(
		BIBLE_DIVISIONS.flatMap((division) => {
			const here = sorted.filter((b) => divisionOf(b.series_position) === division);
			return here.length ? [{ division, books: here }] : [];
		})
	);
}

/** Division groups, in canonical order, under the testament each falls in. */
function byTestament<G extends { division: BibleDivision }>(
	groups: readonly G[]
): { testament: Testament; divisions: G[] }[] {
	const out: { testament: Testament; divisions: G[] }[] = [];
	for (const group of groups) {
		let testament = out.at(-1);
		if (testament?.testament !== group.division.testament) {
			testament = { testament: group.division.testament, divisions: [] };
			out.push(testament);
		}
		testament.divisions.push(group);
	}
	return out;
}

export interface CanonSlot<T> {
	/** Canonical number, 1 Genesis … 66 Revelation. */
	position: number;
	/** The book's short English name ("Psalms", "1 Corinthians", "John"). */
	name: string;
	/** The library's edition at this place, or null where this language has none. */
	book: T | null;
	/**
	 * 0–1: how long the book is beside the longest one here (square root of its
	 * words, so Obadiah stays a spine and the Psalms don't fill the band). 0 for
	 * an absent book. The strip draws it as the spine's thickness.
	 */
	weight: number;
}

export interface CanonDivision<T> {
	division: BibleDivision;
	slots: CanonSlot<T>[];
}

export interface CanonTestament<T> {
	testament: Testament;
	divisions: CanonDivision<T>[];
}

/**
 * The hub's canon strip: ALL 66 books in canonical order, by testament and
 * division, each slot holding the library's edition or null. Unlike
 * `groupBible`, nothing is dropped — the strip's point is the whole shape of the
 * canon, with the books a language lacks shown as gaps. The names are the
 * canon's short English names (`CANON`): the hub is drawn only in
 * BIBLE_LOCALES, all English today; a translated Bible would bring its own.
 */
export function canonStrip<
	T extends { series_position?: number | null; word_count?: number | null; chapter_count?: number }
>(books: readonly T[]): CanonTestament<T>[] {
	const at = new Map<number, T>();
	for (const b of books) {
		const p = b.series_position;
		if (divisionOf(p) && !at.has(p!)) at.set(p!, b);
	}
	// Words where the API sends them; chapters stand in for a book without a count.
	const size = (b: T) => Math.sqrt(b.word_count || (b.chapter_count ?? 0) * 500);
	const largest = Math.max(0, ...[...at.values()].map(size));
	const slot = (position: number): CanonSlot<T> => {
		const book = at.get(position) ?? null;
		return {
			position,
			name: CANON[position - 1][0],
			book,
			weight: book && largest ? Math.round((size(book) / largest) * 100) / 100 : 0
		};
	};
	return byTestament(
		BIBLE_DIVISIONS.map((division) => ({
			division,
			slots: Array.from({ length: division.last - division.first + 1 }, (_, i) =>
				slot(division.first + i)
			)
		}))
	);
}

/**
 * The reading plans the hub's "Read along" row offers, in the order it shows
 * them (`library/plan_seed.py`). Named rather than derived: a plan list row's
 * `covers` stop at five books and leave out article days, so "every cover is a
 * Bible book" cannot tell a plan that reads only the Bible from one that does
 * not. A plan here that has not shipped in a language is simply absent.
 */
export const BIBLE_PLANS: readonly string[] = [
	'john-in-21-days',
	'psalms-in-150-days',
	'proverbs-in-a-month'
];

/** The Bible's plans among `plans`, in `BIBLE_PLANS` order. */
export function biblePlans<P extends { slug: string }>(plans: readonly P[]): P[] {
	const bySlug = new Map(plans.map((p) => [p.slug, p]));
	return BIBLE_PLANS.flatMap((slug) => bySlug.get(slug) ?? []);
}

/** What the hub's passage box needs of a `/api/library/scripture/` answer. */
export interface PassageLookup {
	/** The parsed reference, as the API prints it ("John 3:16", "Psalms 23:1-6", "John"). */
	reference: string;
	verses: readonly { number: number }[];
	/** The library chapter that prints it, or null where the library has no edition. */
	bible_chapter?: { slug: string; order: number } | null;
}

/**
 * Where the hub's "Go to a passage" box sends a reader for a looked-up
 * reference (unlocalized), or null when the library prints none of it.
 *
 * The API does the parsing — book names, abbreviations ("Jn", "1 Cor"), ranges —
 * and says which reader chapter holds the reference (`bible_chapter`):
 *  - a bare book ("Romans": its reference ends in no number) opens the book's
 *    page, its introduction and contents, not chapter 1;
 *  - a verse or a range ("John 3:16", "Romans 8:28-30") opens the chapter at its
 *    first verse — the `#v<n>` anchor `build_owb_book` sets on each verse number;
 *  - a chapter ("Psalm 23", which the API prints as "Psalms 23:1-6") or a
 *    passage from verse 1 opens the chapter at its top.
 */
export function passageHref(found: PassageLookup): string | null {
	const at = found.bible_chapter;
	if (!at) return null;
	if (!/\d$/.test(found.reference.trim())) return `/books/${at.slug}`;
	const chapter = bookChapterPath(at.slug, at.order, false);
	// Verse 1 is the chapter's top (and its number is not printed there).
	const verse = found.verses[0]?.number ?? 1;
	return verse > 1 ? `${chapter}#v${verse}` : chapter;
}

/** Every name and abbreviation the canon goes by, lower-cased, plus the
 *  singular "Psalm" and the "Song of Solomon" the resolver also knows. */
const BOOK_NAMES = new Set(
	[...CANON.flat(), 'Psalm', 'Song of Solomon'].map((n) => n.toLowerCase())
);

/**
 * Whether the hub's passage box should ask the resolver: anything naming a
 * chapter (`mayBeReference`: it has a digit), or a book named on its own
 * ("Romans", "1 John", "Ps") — which opens that book's page. Any other word
 * ("grace") goes straight to search.
 */
export const mayBePassage = (q: string): boolean =>
	/\d/.test(q) || BOOK_NAMES.has(q.trim().replace(/\.$/, '').replace(/\s+/g, ' ').toLowerCase());

/** One step of the hub's "Where to start" path. */
export interface BibleStart {
	/** The Bible book's slug (its `the-bible` series volume). */
	slug: string;
	/** Why this book, and why now — English, as the hub is (BIBLE_LOCALES). */
	why: string;
}

/**
 * The hub's "Where to start": five books for a first reader, in reading order.
 * A Gospel first, the shortest; then the one written "that you may believe";
 * then the beginning; then the prayer book; then the gospel explained. The
 * reasons are English prose like the rest of the hub's own copy: the hub exists
 * only where the Bible does, English today. A step whose book is missing in the
 * series (`bibleStarts`) is left out.
 */
export const BIBLE_STARTS: readonly BibleStart[] = [
	{ slug: 'gospel-of-mark', why: 'The shortest Gospel, and the quickest: the life of Jesus in one sitting.' },
	{ slug: 'gospel-of-john', why: 'Written “so that you may believe”: who Jesus is, in his own words.' },
	{ slug: 'genesis', why: 'The beginning: creation, the fall, and God’s promise to Abraham.' },
	{ slug: 'psalms', why: 'The Bible’s prayer book. Read one a day, aloud if you can.' },
	{ slug: 'romans', why: 'The gospel set out step by step: sin, grace, faith and new life.' }
];

/** The "Where to start" steps the series has, each with its book, in order. */
export function bibleStarts<T extends { slug: string }>(
	books: readonly T[]
): { book: T; why: string }[] {
	const bySlug = new Map(books.map((b) => [b.slug, b]));
	return BIBLE_STARTS.flatMap((s) => {
		const book = bySlug.get(s.slug);
		return book ? [{ book, why: s.why }] : [];
	});
}

/**
 * The Bible chapters among `books` (1,189 for the 66): each book's reader
 * chapters less its introduction and conclusion, the two `build_owb_book` sets
 * around the Bible's own.
 */
export const bibleChapterCount = (books: readonly { chapter_count?: number }[]): number =>
	books.reduce((n, b) => n + Math.max(0, (b.chapter_count ?? 0) - 2), 0);

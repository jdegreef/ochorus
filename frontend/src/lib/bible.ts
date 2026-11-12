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
	const out: TestamentGroup<T>[] = [];
	for (const division of BIBLE_DIVISIONS) {
		const here = sorted.filter((b) => divisionOf(b.series_position) === division);
		if (!here.length) continue;
		let testament = out.at(-1);
		if (testament?.testament !== division.testament) {
			testament = { testament: division.testament, divisions: [] };
			out.push(testament);
		}
		testament.divisions.push({ division, books: here });
	}
	return out;
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

import type { BookSummary, OriginalsSeries } from './library-public';

/**
 * Ochorus Originals — the house imprint.
 *
 * It is a byline, not a person (`Author.is_imprint`), so it has no biography
 * and no author page: its books live on a publisher's page, /originals. Every
 * link that would name the imprint as an author goes through `authorPath`, so
 * a reader who taps "Ochorus Originals" on a book lands on that page rather
 * than on a monogram with nothing to say about a life.
 */
export const ORIGINALS_SLUG = 'ochorus-originals';
export const ORIGINALS_PATH = '/originals';

/** The page a writer's name links to: their author page, or /originals for
 * the imprint. Unlocalized — pass it through `localizeHref` as usual. */
export function authorPath(slug: string): string {
	return slug === ORIGINALS_SLUG ? ORIGINALS_PATH : `/authors/${slug}`;
}

/** The schema.org type of a work's author: the imprint is a publisher. */
export function authorLdType(slug: string): 'Organization' | 'Person' {
	return slug === ORIGINALS_SLUG ? 'Organization' : 'Person';
}

/**
 * The stand-alone shelves, by what a book IS. Series group themselves from the
 * data; a stand-alone book has no field that says whether it is a collected
 * life or a book on the Christian life, so the imprint's editors say so here.
 * A book missing from this map is not lost — it lands on "More Originals".
 */
export type ShelfKey = 'lives' | 'life' | 'more';

const SHELF_OF: Record<string, Exclude<ShelfKey, 'more'>> = {
	tukutendereza: 'lives',
	'a-hidden-fire': 'lives',
	'men-of-prayer-2': 'lives',
	'men-who-moved-heaven': 'lives',
	'women-who-moved-heaven-2': 'lives',
	'men-and-women-who-gave-everything-2': 'lives',
	'men-who-tended-the-flock-2': 'lives',
	'clothed-with-strength-and-dignity': 'life',
	'rise-up-men-of-god-2': 'life',
	'growing-in-wisdom': 'life'
};

const SHELF_ORDER: ShelfKey[] = ['lives', 'life', 'more'];

/** Each shelf's heading and (optional) one-line note, as i18n keys. */
export const SHELF_META: Record<ShelfKey, { label: string; note?: string }> = {
	lives: { label: 'originals.shelfLives', note: 'originals.shelfLivesNote' },
	life: { label: 'originals.shelfLife', note: 'originals.shelfLifeNote' },
	more: { label: 'originals.shelfMore' }
};

/** "Where to begin" — one door for each kind of reader. Shown only for the
 * books this language has. */
export const STARTERS: { labelKey: string; slug: string }[] = [
	{ labelKey: 'originals.pathChild', slug: 'brave-for-god' },
	{ labelKey: 'originals.pathHabit', slug: 'rooted-1' },
	{ labelKey: 'originals.pathWeek', slug: 'clothed-with-strength-and-dignity' }
];

export interface SeriesRow extends Omit<OriginalsSeries, 'books'> {
	books: BookSummary[];
	words: number;
}

export interface Shelved {
	series: SeriesRow[];
	shelves: { key: ShelfKey; books: BookSummary[] }[];
}

/**
 * Split the imprint's books into series rows (in the API's series order, each
 * in volume order) and stand-alone shelves. A book the API lists in a series is
 * never also shelved alone; empty shelves are dropped.
 */
export function shelveOriginals(books: BookSummary[], series: OriginalsSeries[]): Shelved {
	const bySlug = new Map(books.map((b) => [b.slug, b]));
	const inSeries = new Set<string>();
	const rows: SeriesRow[] = [];
	for (const s of series) {
		const members = s.books.map((slug) => bySlug.get(slug)).filter((b): b is BookSummary => !!b);
		if (!members.length) continue;
		for (const b of members) inSeries.add(b.slug);
		rows.push({
			...s,
			books: members,
			words: members.reduce((n, b) => n + (b.word_count ?? 0), 0)
		});
	}
	const shelves = SHELF_ORDER.map((key) => ({
		key,
		books: books.filter((b) => !inSeries.has(b.slug) && (SHELF_OF[b.slug] ?? 'more') === key)
	})).filter((s) => s.books.length);
	return { series: rows, shelves };
}

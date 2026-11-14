/**
 * The /bible hub's passage box, before anything is asked of the API: one-tap
 * passages under it, and suggestions as the reader types.
 *
 * Both work from the hub's own book list (the `the-bible` series summaries:
 * slug, place in the canon, chapter count), so a suggestion is a link the
 * library prints, never a guess the resolver might refuse. A query this cannot
 * read still goes to the resolver and then to search on submit, as before.
 *
 * The names are the canon's English ones (`CANON`) and a few common short
 * forms: the hub is drawn only in BIBLE_LOCALES, English today.
 */
import { CANON } from '$lib/sermonCanon';
import { bibleChapterCount, bibleChapterOrder, chapterLabel } from '$lib/bible';
import { bookChapterPath } from '$lib/reading-schema';

type HubBook = { slug: string; title: string; chapter_count?: number; series_position?: number | null };

/** One place the box can open: a book's page, or a chapter (at a verse). */
export interface PassageLink {
	label: string;
	/** Unlocalized. */
	href: string;
}

/**
 * The one-tap passages under the box: the chapters people most often look for,
 * in this order — the placeholder's three first, so the chips teach its format.
 * [canon position, chapter].
 */
export const QUICK_PASSAGES: readonly (readonly [position: number, chapter: number])[] = [
	[43, 3], // John 3
	[19, 23], // Psalm 23
	[45, 8], // Romans 8
	[46, 13], // 1 Corinthians 13
	[23, 53], // Isaiah 53
	[40, 5] // Matthew 5
];

const chapterLink = (book: HubBook, position: number, n: number, verse?: number): PassageLink => {
	const path = bookChapterPath(book.slug, bibleChapterOrder(n), false);
	const label = chapterLabel(position, n) ?? `${book.title} ${n}`;
	return verse && verse > 1 ? { label: `${label}:${verse}`, href: `${path}#v${verse}` } : { label, href: path };
};

const byPosition = (books: readonly HubBook[]) => {
	const at = new Map<number, HubBook>();
	for (const b of books) if (b.series_position != null) at.set(b.series_position, b);
	return at;
};

/** The quick passages whose book (and chapter) the library has. */
export function quickPassages(books: readonly HubBook[]): PassageLink[] {
	const at = byPosition(books);
	return QUICK_PASSAGES.flatMap(([pos, n]) => {
		const book = at.get(pos);
		return book && n <= bibleChapterCount([book]) ? [chapterLink(book, pos, n)] : [];
	});
}

/** A name squashed for matching: lower case, no dots or spaces ("1 Cor." → "1cor"). */
const squash = (s: string) => s.toLowerCase().replace(/[.\s]/g, '');

/** Short forms beyond the canon's own abbreviation, by canon position. */
const ALIASES: Record<number, readonly string[]> = {
	19: ['Psalm', 'Psa', 'Pss'],
	22: ['Song of Solomon', 'Canticles'],
	40: ['Mt'],
	41: ['Mk'],
	42: ['Lk'],
	43: ['Jn'],
	45: ['Ro'],
	57: ['Philemon', 'Phm'],
	66: ['Revelations', 'Apocalypse']
};

/** Every name each canon position goes by, squashed. */
const NAMES: readonly (readonly [position: number, names: readonly string[]])[] = CANON.map(
	([name, abbr], i) => [i + 1, [name, abbr, ...(ALIASES[i + 1] ?? [])].map(squash)] as const
);

/**
 * The edit distance between two short strings, counting two swapped letters
 * as one typo ("Roamns"): optimal string alignment.
 */
function distance(a: string, b: string): number {
	const d = Array.from({ length: a.length + 1 }, (_, i) =>
		Array.from({ length: b.length + 1 }, (_, j) => (i === 0 ? j : j === 0 ? i : 0))
	);
	for (let i = 1; i <= a.length; i++)
		for (let j = 1; j <= b.length; j++) {
			d[i][j] = Math.min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1));
			if (i > 1 && j > 1 && a[i - 1] === b[j - 2] && a[i - 2] === b[j - 1])
				d[i][j] = Math.min(d[i][j], d[i - 2][j - 2] + 1);
		}
	return d[a.length][b.length];
}

/**
 * The canon positions a typed book name could mean, best first: names it
 * begins (in canon order), else — for a name of four letters or more that
 * begins none — the books one or two typos away ("Roamns", "Phillipians").
 */
export function matchBooks(token: string): number[] {
	const q = squash(token);
	if (!q) return [];
	const prefix = NAMES.filter(([, names]) => names.some((n) => n.startsWith(q))).map(([p]) => p);
	if (prefix.length || q.length < 4) return prefix;
	const close = NAMES.map(([p, names]) => [p, Math.min(...names.map((n) => distance(q, n)))] as const)
		.filter(([, d]) => d <= (q.length >= 7 ? 2 : 1))
		.sort((a, b) => a[1] - b[1] || a[0] - b[0]);
	return close.map(([p]) => p);
}

/** "1 cor 13:4" → the book part, the chapter and the verse (both optional). */
const QUERY = /^\s*((?:[1-3]\s*)?[a-z][a-z .]*?)\s*(?:(\d{1,3})(?:\s*[:.]\s*(\d{1,3}))?)?\s*$/i;

/**
 * What the box suggests for `q`, at most `max`: with a chapter typed, that
 * chapter (at the verse) of each book the name could mean, where it has the
 * chapter; with a name alone, those books' pages. Empty for a query it cannot
 * read ("grace") — the box then leaves it to the resolver and search, as before.
 */
export function passageSuggestions(q: string, books: readonly HubBook[], max = 6): PassageLink[] {
	const m = QUERY.exec(q);
	if (!m) return [];
	const [, name, ch, vs] = m;
	const at = byPosition(books);
	const chapter = ch ? Number(ch) : null;
	const verse = vs ? Number(vs) : undefined;
	return matchBooks(name)
		.flatMap((pos) => {
			const book = at.get(pos);
			if (!book) return [];
			if (chapter == null) return [{ label: book.title, href: `/books/${book.slug}` }];
			return chapter >= 1 && chapter <= bibleChapterCount([book])
				? [chapterLink(book, pos, chapter, verse)]
				: [];
		})
		.slice(0, max);
}

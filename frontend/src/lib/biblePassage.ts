/**
 * The /bible hub's passage box, before anything is asked of the API: one-tap
 * passages under it, and suggestions as the reader types.
 *
 * Both work from the hub's own book list (the `the-bible` series summaries:
 * slug, place in the canon, chapter count), so a suggestion is a link the
 * library prints, never a guess the resolver might refuse. A query this cannot
 * read still goes to the resolver and then to search on submit, as before.
 *
 * The names are the canon's in the hub's language ($lib/bibleNames) and a few
 * common short forms; a Spanish, French, Portuguese or Swahili reader's box
 * also takes the English names.
 * Accents are optional ("Genesis", "Exodo").
 */
import { CANON } from '$lib/sermonCanon';
import { canonIn } from '$lib/bibleNames';
import { bibleIn, type BibleLocale } from '$lib/bibleLocales';
import { bibleChapterCount, bibleChapterOrder } from '$lib/bible';
import { chapterLabel } from '$lib/bibleNames';
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

const chapterLink = (
	book: HubBook,
	position: number,
	n: number,
	lang: string,
	verse?: number
): PassageLink => {
	const path = bookChapterPath(book.slug, bibleChapterOrder(n), false);
	const label = chapterLabel(position, n, lang) ?? `${book.title} ${n}`;
	return verse && verse > 1 ? { label: `${label}:${verse}`, href: `${path}#v${verse}` } : { label, href: path };
};

const byPosition = (books: readonly HubBook[]) => {
	const at = new Map<number, HubBook>();
	for (const b of books) if (b.series_position != null) at.set(b.series_position, b);
	return at;
};

/** The quick passages whose book (and chapter) the library has. */
export function quickPassages(books: readonly HubBook[], lang: string): PassageLink[] {
	const at = byPosition(books);
	return QUICK_PASSAGES.flatMap(([pos, n]) => {
		const book = at.get(pos);
		return book && n <= bibleChapterCount([book]) ? [chapterLink(book, pos, n, lang)] : [];
	});
}

/** A name folded for matching: lower case, no dots or spaces, accents kept
 *  ("1 Cor." → "1cor", "Jó" → "jó"). */
const fold = (s: string) =>
	s
		.normalize('NFC')
		.toLowerCase()
		.replace(/[.\s]/g, '');

/** A folded name without its accents ("éxodo" → "exodo"): what a reader who
 *  skips them types. */
const bare = (s: string) => s.normalize('NFD').replace(/\p{M}/gu, '').normalize('NFC');

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

/** Spanish short forms beyond the canon's own (`ALIASES`' twin). */
const ALIASES_ES: Record<number, readonly string[]> = {
	19: ['Salmo', 'Sl'],
	22: ['Cantar de los Cantares', 'Cantar', 'Cant'],
	40: ['Mat'],
	41: ['Mc', 'Mar'],
	42: ['Luc'],
	44: ['Hechos de los Apóstoles', 'Hech'],
	45: ['Rom'],
	59: ['Sant'],
	66: ['Apoc', 'Revelación']
};

/** French short forms the canon's own names do not begin: the older or
 *  Catholic names (Isaïe, Nahum, Haggaï) and the long titles. */
const ALIASES_FR: Record<number, readonly string[]> = {
	22: ['Cantique de Salomon'],
	23: ['Isaïe'],
	34: ['Nahum'],
	37: ['Haggaï'],
	44: ['Actes des Apôtres'],
	66: ['Révélation']
};

/** Portuguese short forms the canon's own names do not begin: the spellings
 *  before the 1990 agreement (Oséias, Miquéias) and the long titles. */
const ALIASES_PT: Record<number, readonly string[]> = {
	22: ['Cânticos', 'Cantares'],
	28: ['Oséias'],
	33: ['Miquéias'],
	44: ['Atos dos Apóstolos'],
	57: ['Filemon'],
	66: ['Revelação']
};

/** Swahili short forms the canon's own names and abbreviations do not begin:
 *  the books' second words (Walawi, Nyakati) and the long titles. */
const ALIASES_SW: Record<number, readonly string[]> = {
	3: ['Walawi'],
	13: ['1 Nyakati'],
	14: ['2 Nyakati'],
	22: ['Wimbo wa Sulemani'],
	40: ['Mat'],
	41: ['Mar'],
	42: ['Luk'],
	43: ['Yoh'],
	44: ['Matendo ya Mitume'],
	66: ['Ufunuo wa Yohana']
};

type Names = readonly (readonly [position: number, names: readonly string[]])[];

/** Every name each canon position goes by, folded. */
const namesOf = (canon: typeof CANON, aliases: Record<number, readonly string[]>, also?: Names): Names =>
	canon.map(
		([name, abbr], i) =>
			[i + 1, [name, abbr, ...(aliases[i + 1] ?? [])].map(fold).concat(also?.[i][1] ?? [])] as const
	);
const NAMES_EN = namesOf(CANON, ALIASES);
/** A hub locale's names, by locale: each adds the English ones. */
const NAMES: Readonly<Record<BibleLocale, Names>> = {
	en: NAMES_EN,
	es: namesOf(canonIn('es'), ALIASES_ES, NAMES_EN),
	fr: namesOf(canonIn('fr'), ALIASES_FR, NAMES_EN),
	pt: namesOf(canonIn('pt'), ALIASES_PT, NAMES_EN),
	sw: namesOf(canonIn('sw'), ALIASES_SW, NAMES_EN)
};

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
 * The canon positions a typed book name could mean, best first: a name it is
 * exactly (with its accents, then without: Portuguese "Jo" is João, "Jó" is
 * Job), then names it begins, each in canon order; else, for a name of four
 * letters or more that begins none, the books one or two typos away
 * ("Roamns", "Phillipians"), unless `fuzzy` is false.
 */
export function matchBooks(token: string, lang: string, fuzzy = true): number[] {
	const q = fold(token);
	if (!q) return [];
	const qb = bare(q);
	const names = bibleIn(lang) ? NAMES[lang] : NAMES_EN;
	const rank = (ns: readonly string[]) =>
		ns.includes(q) ? 0 : ns.some((n) => bare(n) === qb) ? 1 : ns.some((n) => bare(n).startsWith(qb)) ? 2 : 3;
	const prefix = names
		.map(([p, ns]) => [p, rank(ns)] as const)
		.filter(([, r]) => r < 3)
		.sort((a, b) => a[1] - b[1] || a[0] - b[0])
		.map(([p]) => p);
	if (prefix.length || qb.length < 4 || !fuzzy) return prefix;
	const close = names.map(([p, ns]) => [p, Math.min(...ns.map((n) => distance(qb, bare(n))))] as const)
		.filter(([, d]) => d <= (qb.length >= 7 ? 2 : 1))
		.sort((a, b) => a[1] - b[1] || a[0] - b[0]);
	return close.map(([p]) => p);
}

/** "1 cor 13:4" → the book part, the chapter and the verse (both optional). */
const QUERY = /^\s*((?:[1-3]\s*)?\p{L}[\p{L}\p{M} .]*?)\s*(?:(\d{1,3})(?:\s*[:.]\s*(\d{1,3}))?)?\s*$/iu;

/**
 * What the box suggests for `q`, at most `max`: with a chapter typed, that
 * chapter (at the verse) of each book the name could mean, where it has the
 * chapter; with a name alone, the pages of the books it begins the name of. Empty for a query it cannot
 * read ("grace") — the box then leaves it to the resolver and search, as before.
 */
export function passageSuggestions(
	q: string,
	books: readonly HubBook[],
	lang: string,
	max = 6
): PassageLink[] {
	const m = QUERY.exec(q);
	if (!m) return [];
	const [, name, ch, vs] = m;
	const at = byPosition(books);
	const chapter = ch ? Number(ch) : null;
	const verse = vs ? Number(vs) : undefined;
	// A name alone opens a book only when it reads as one (a prefix of its
	// name): a typo-close match of a bare word is as likely an ordinary word
	// («amor», "grace") the reader meant to search for. With a chapter typed,
	// a typo still reads as a reference ("Roamns 8").
	return matchBooks(name, lang, chapter != null)
		.flatMap((pos) => {
			const book = at.get(pos);
			if (!book) return [];
			if (chapter == null) return [{ label: book.title, href: `/books/${book.slug}` }];
			return chapter >= 1 && chapter <= bibleChapterCount([book])
				? [chapterLink(book, pos, chapter, lang, verse)]
				: [];
		})
		.slice(0, max);
}

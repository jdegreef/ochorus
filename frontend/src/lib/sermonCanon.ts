import { HEAT_LEVELS } from '$lib/scriptureIndex';

/**
 * The Sermons shelf's "Browse by Scripture" grid (design review #21): the 66
 * books of the Bible in canonical order, each with how many sermons on THIS
 * shelf preach from it.
 *
 * Counts come from the shelf payload's `scripture_book` / `scripture_book_order`
 * — the same fields the book filter uses (backend `scripture.book_of`), so a
 * cell's `name` is exactly the `?book=` value that filter matches. The names
 * below are pythonbible's `Book.title`, in its `Book.value` order (Genesis = 1 …
 * Revelation = 66, the numbering `BIBLE_SECTIONS` uses); the abbreviations are
 * the cell's short label. Pure, so the page stays markup and this stays tested.
 */
export const CANON: readonly (readonly [name: string, abbr: string])[] = [
	['Genesis', 'Gen'],
	['Exodus', 'Exod'],
	['Leviticus', 'Lev'],
	['Numbers', 'Num'],
	['Deuteronomy', 'Deut'],
	['Joshua', 'Josh'],
	['Judges', 'Judg'],
	['Ruth', 'Ruth'],
	['1 Samuel', '1 Sam'],
	['2 Samuel', '2 Sam'],
	['1 Kings', '1 Kgs'],
	['2 Kings', '2 Kgs'],
	['1 Chronicles', '1 Chr'],
	['2 Chronicles', '2 Chr'],
	['Ezra', 'Ezra'],
	['Nehemiah', 'Neh'],
	['Esther', 'Esth'],
	['Job', 'Job'],
	['Psalms', 'Ps'],
	['Proverbs', 'Prov'],
	['Ecclesiastes', 'Eccl'],
	['Song of Songs', 'Song'],
	['Isaiah', 'Isa'],
	['Jeremiah', 'Jer'],
	['Lamentations', 'Lam'],
	['Ezekiel', 'Ezek'],
	['Daniel', 'Dan'],
	['Hosea', 'Hos'],
	['Joel', 'Joel'],
	['Amos', 'Amos'],
	['Obadiah', 'Obad'],
	['Jonah', 'Jonah'],
	['Micah', 'Mic'],
	['Nahum', 'Nah'],
	['Habakkuk', 'Hab'],
	['Zephaniah', 'Zeph'],
	['Haggai', 'Hag'],
	['Zechariah', 'Zech'],
	['Malachi', 'Mal'],
	['Matthew', 'Matt'],
	['Mark', 'Mark'],
	['Luke', 'Luke'],
	['John', 'John'],
	['Acts', 'Acts'],
	['Romans', 'Rom'],
	['1 Corinthians', '1 Cor'],
	['2 Corinthians', '2 Cor'],
	['Galatians', 'Gal'],
	['Ephesians', 'Eph'],
	['Philippians', 'Phil'],
	['Colossians', 'Col'],
	['1 Thessalonians', '1 Thess'],
	['2 Thessalonians', '2 Thess'],
	['1 Timothy', '1 Tim'],
	['2 Timothy', '2 Tim'],
	['Titus', 'Titus'],
	['Philemon', 'Phlm'],
	['Hebrews', 'Heb'],
	['James', 'Jas'],
	['1 Peter', '1 Pet'],
	['2 Peter', '2 Pet'],
	['1 John', '1 John'],
	['2 John', '2 John'],
	['3 John', '3 John'],
	['Jude', 'Jude'],
	['Revelation', 'Rev']
];

/** Malachi's canonical position: the last book of the Old Testament. */
const LAST_OT = 39;

/**
 * Below this many distinct books the grid is all empty cells and says nothing,
 * so the shelf leaves it out. The book facet parses ENGLISH references only
 * (a translated sermon's "Colosenses 1:27" doesn't resolve). The cells'
 * abbreviations and names are English too, so the page also shows the grid
 * only on the English shelf until localized book names exist.
 */
export const CANON_MIN_BOOKS = 10;

export interface CanonCell {
	/** The facet value — what `?book=` filters on. */
	name: string;
	abbr: string;
	count: number;
	/** `.heat-N` shade (app.css): 0 for an empty book, else 1 to HEAT_LEVELS - 1. */
	heat: number;
}

export interface CanonGrid {
	old: CanonCell[];
	new: CanonCell[];
}

/** One book on the shelf, as the page's book facet holds it. */
export interface BookFacet {
	/** The payload's `scripture_book`, the value the book filter matches. */
	name: string;
	/** Its canonical position (`scripture_book_order`). */
	order: number;
	count: number;
}

/**
 * The grid for a shelf's book facets, or null when they cover fewer than
 * CANON_MIN_BOOKS of the 66.
 *
 * Built from the facets the book `<select>` already shows, so a cell's count
 * and the list its click filters to are the same figure by construction, and
 * the payload's name for a book wins over CANON's.
 *
 * A book with sermons always takes at least the first shade, so it never looks
 * like an empty one; the rest climb on a square-root scale to the shelf's
 * busiest book (John's 58 against a long tail of ones and twos would leave a
 * linear scale with one dark cell and sixty pale ones).
 */
export function canonGrid(facets: readonly BookFacet[]): CanonGrid | null {
	const byOrder = new Map<number, BookFacet>();
	for (const f of facets) if (f.order >= 1 && f.order <= CANON.length) byOrder.set(f.order, f);
	if (byOrder.size < CANON_MIN_BOOKS) return null;
	const max = Math.max(...[...byOrder.values()].map((f) => f.count));
	const top = HEAT_LEVELS - 1;
	const cells = CANON.map(([name, abbr], i): CanonCell => {
		const f = byOrder.get(i + 1);
		const count = f?.count ?? 0;
		const heat = count ? 1 + Math.round((top - 1) * Math.sqrt(count / max)) : 0;
		return { name: f?.name ?? name, abbr, count, heat };
	});
	return { old: cells.slice(0, LAST_OT), new: cells.slice(LAST_OT) };
}

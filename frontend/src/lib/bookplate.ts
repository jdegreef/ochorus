import { coverStyleFor, type CoverStyleId } from './coverStyles';
import { eraOf } from './eras';
import type { BookSummary } from './library-public';
import type { ProgressRecord, WorkKind } from './reading-schema';

/**
 * An ex libris bookplate for a finished book — what the plate SAYS, decided
 * apart from the two things that draw it (`Bookplate.svelte` on the page,
 * `bookplateCard.ts` as a PNG), so the decisions are tested once.
 *
 * NOTHING NEW IS STORED. A plate is the reader's name (their profile's display
 * name), a book, and the day it was finished — the `finished_at` stamp the
 * progress record already carries and `readingSync` already mirrors to the
 * account. So a plate appears on every device the reader signs in on, and
 * un-finishing a book takes its plate away, with no second record to drift.
 *
 * ONE DESIGN, THE BOOK'S OWN TYPE. The plate does not have a look per era; it
 * wears the face the book's cover is set in (`coverStyleFor`), so a Puritan's
 * plate is lettered in the Fell types and a Victorian's in a display face, the
 * same way their covers already are.
 */

/** The words every plate opens on. Latin, and left so in every language:
 *  it is what bookplates have said for five centuries, in every country. */
export const EX_LIBRIS = 'EX LIBRIS';

/**
 * The name a plate is made out to: the reader's display name, as they wrote it
 * (whitespace tidied). Null when there is none — signed out, or an account that
 * has not given a name. Never the email: a plate is printed and passed around,
 * and a handle guessed from an address ("jd1987") is not a name.
 */
export function plateName(displayName: string | null | undefined): string | null {
	const name = (displayName ?? '').replace(/\s+/g, ' ').trim();
	return name || null;
}

/**
 * The day the book was finished, written out in the reader's own locale —
 * "11 November 2026", "11 de noviembre de 2026", "2026年11月11日". A locale the
 * runtime cannot format falls back to English rather than throwing.
 */
export function plateDate(at: number, locale: string): string {
	const opts: Intl.DateTimeFormatOptions = { day: 'numeric', month: 'long', year: 'numeric' };
	try {
		return new Intl.DateTimeFormat(locale, opts).format(at);
	} catch {
		return new Intl.DateTimeFormat('en', opts).format(at);
	}
}

/** The cover recipe whose face the plate is lettered in. */
export function plateStyle(
	author: { slug: string; birth_year: number | null },
	bookSlug: string
): CoverStyleId {
	return coverStyleFor(eraOf(author.birth_year), author.slug, bookSlug);
}

/**
 * Each recipe's Latin face and the weight it ships, as a canvas literal.
 *
 * A LITERAL BECAUSE CANVAS CANNOT READ A CUSTOM PROPERTY (the same reason as
 * `quoteCard.CARD_SERIF`). The page draws the plate with `var(--cover-face-*)`;
 * the PNG has to name the family. `bookplate.test.ts` holds each one to the
 * first family of its app.css token, so the two renderers cannot disagree.
 *
 * The weight is the one the face is loaded at (app.css @imports): IM Fell and
 * Libre Baskerville ship 400 only, Amatic SC 700 only; asking for another gets
 * a synthesised stem.
 */
export const PLATE_FACES: Record<CoverStyleId, { family: string; weight: number }> = {
	inscriptional: { family: 'Cinzel Variable', weight: 500 },
	devotional: { family: 'EB Garamond Variable', weight: 500 },
	press: { family: 'IM Fell English', weight: 400 },
	enlightenment: { family: 'Libre Baskerville', weight: 400 },
	revival: { family: 'Playfair Display Variable', weight: 500 },
	house: { family: 'Fraunces Variable', weight: 500 },
	lettered: { family: 'Amatic SC', weight: 700 },
	originals: { family: 'Fraunces Variable', weight: 600 },
	young: { family: 'Hanken Grotesk Variable', weight: 600 }
};

/** After the Latin face: a face for every script a name or title may be in.
 *  Canvas falls back per glyph through this list like the DOM does, so an
 *  Arabic name on an IM Fell plate lands on Amiri, not the device serif. */
const SERIF_SCRIPTS =
	"'Amiri', 'Tiro Devanagari Hindi', 'PT Serif', 'Noto Serif Ethiopic', 'Noto Serif KR', 'Noto Serif JP', Georgia, 'Times New Roman', serif";
const SANS_SCRIPTS =
	"'Noto Sans Arabic', 'Noto Sans Devanagari', 'PT Sans', 'Noto Sans Ethiopic', 'Noto Sans KR', 'Noto Sans JP', system-ui, sans-serif";

/** The canvas font stack a plate in this recipe is lettered in. */
export function plateFontStack(style: CoverStyleId): string {
	return `'${PLATE_FACES[style].family}', ${style === 'young' ? SANS_SCRIPTS : SERIF_SCRIPTS}`;
}

export type PlateScript = 'arabic' | 'devanagari' | 'cyrillic' | 'ethiopic' | 'korean' | 'japanese';

/** Script → a locale whose font sheet (`fontSheets.SCRIPT_FONTS`) carries it. */
export const SCRIPT_SHEET: Record<PlateScript, string> = {
	arabic: 'ar',
	devanagari: 'hi',
	cyrillic: 'uk',
	ethiopic: 'am',
	korean: 'ko',
	japanese: 'ja'
};

const SCRIPT_TESTS: [PlateScript, RegExp][] = [
	['arabic', /\p{Script=Arabic}/u],
	['devanagari', /\p{Script=Devanagari}/u],
	['cyrillic', /\p{Script=Cyrillic}/u],
	['ethiopic', /\p{Script=Ethiopic}/u],
	['korean', /\p{Script=Hangul}/u],
	['japanese', /[\p{Script=Hiragana}\p{Script=Katakana}\p{Script=Han}]/u]
];

/**
 * The non-Latin scripts in a piece of text — what a plate has to load a face
 * for. Read from the TEXT, not the page's language: an Arabic name on an
 * English page still needs Amiri.
 */
export function textScripts(text: string): PlateScript[] {
	return SCRIPT_TESTS.filter(([, re]) => re.test(text)).map(([s]) => s);
}

/** Whether a line reads right to left: its first strong character does. */
export function isRtl(text: string): boolean {
	const first = /[\p{L}]/u.exec(text)?.[0];
	return !!first && /[\p{Script=Arabic}\p{Script=Hebrew}\p{Script=Syriac}\p{Script=Thaana}]/u.test(first);
}

/**
 * A translated template around one placeholder, split so the placeholder can be
 * set differently ("finished %title%": the title in the book's face). Word
 * order is the catalogue's: "%title% を読了" puts the words after. A template
 * missing the placeholder keeps its words before it.
 */
export function splitAround(template: string, token: string): [string, string] {
	const i = template.indexOf(token);
	if (i < 0) return [template.trim(), ''];
	return [template.slice(0, i).trim(), template.slice(i + token.length).trim()];
}

export interface Plate {
	book: BookSummary;
	/** When it was finished (ms) — the `finished_at` stamp. */
	at: number;
}

type ProgressRow = ProgressRecord & { slug: string; kind: WorkKind };

/**
 * The reader's plates, newest first: one per finished book with a row in this
 * language. A book finished in another language has no title to letter here
 * (there is no English fallback), so it waits for that language's shelf.
 */
export function finishedPlates(progress: ProgressRow[], books: BookSummary[]): Plate[] {
	const bySlug = new Map(books.map((b) => [b.slug, b]));
	const seen = new Set<string>();
	const plates: Plate[] = [];
	for (const p of progress) {
		if (p.kind !== 'book' || p.finished_at == null || seen.has(p.slug)) continue;
		const book = bySlug.get(p.slug);
		if (!book) continue;
		seen.add(p.slug);
		plates.push({ book, at: p.finished_at });
	}
	return plates.sort((a, b) => b.at - a.at);
}

/** The saved image's file name. */
export const plateFilename = (slug: string): string => `ochorus-bookplate-${slug}.png`;

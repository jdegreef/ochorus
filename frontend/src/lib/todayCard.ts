// The home page's Today card (design #20): today's verse and the devotional
// reading for this date, both drawn from the dated devotionals' shelf
// (`getDailyShelf`), so outside English they are in the reader's own language
// and Bible. (English Scripture is the OWB: the card looks a candidate's
// reference up there, and these candidates are only where the day's
// references come from.) The sermon of the day is `pickDailySermon`'s.
// Picked CLIENT-SIDE by the card, for the same reason as the rest of the day's
// blocks: home is prerendered, and a build-time pick would freeze on the day
// of the deploy.

import { localDayNumber } from '$lib/dailyArticles';

export type Verse = { text: string; ref: string };

/** Opening quote mark → the marks that can close it. */
const CLOSERS: Record<string, string> = {
	'“': '”"',
	'«': '»',
	'„': '“”',
	'"': '"',
	'‘': '’'
};

/** Any quote mark: a second quotation after the first closes. */
const QUOTE = /[“”«»„"‘’]/;

/** Spaces, brackets, dashes and full stops (Latin, Amharic, Devanagari)
 *  around a reference. */
const REF_TRIM = /^[\s()\-–—.,;:።।]+|[\s()\-–—.,;:።।]+$/g;

/** A digit in any script (Arabic-Indic, Devanagari…), or an Ethiopic numeral. */
const DIGIT = /[\p{Nd}፩-፼]/u;

/** Where the quotation opened at 0 closes — nested quotations of the same
 *  kind counted in and out — or -1. */
function closeOf(line: string, closers: string): number {
	const opener = line[0];
	const nests = !closers.includes(opener);
	let depth = 1;
	for (let i = 1; i < line.length; i++) {
		if (closers.includes(line[i]) && --depth === 0) return i;
		if (nests && line[i] === opener) depth++;
	}
	return -1;
}

/**
 * The verse in a devotional's opening line, split from its reference:
 * `“Bless the Lord, O, my soul” (Ps. ciii. 1).` → text + `Ps. ciii. 1`.
 * Only a line that is ONE quotation followed by a reference with a number in
 * it is a verse: a poem's first line, two quoted verses in a row, or an
 * excerpt the server cut short ("…") returns null.
 */
export function splitVerse(excerpt: string): Verse | null {
	const line = excerpt.trim();
	const closers = CLOSERS[line[0]];
	if (!closers || line.includes('…')) return null;
	const end = closeOf(line, closers);
	if (end < 2) return null;
	const text = line.slice(1, end).trim();
	const ref = line.slice(end + 1).replace(REF_TRIM, '');
	if (!text || !DIGIT.test(ref) || QUOTE.test(ref) || ref.length > 40) return null;
	return { text, ref };
}

/**
 * The day's devotional — one of the shelf's books, a different one each day
 * — and the verses on offer: every other book's entry that opens on a verse,
 * starting after the day's book, then the day's own, so the verse column
 * doesn't repeat the reading's where it can help it.
 */
export function pickToday<T extends { excerpt: string }>(
	readings: readonly T[],
	date: Date
): { reading: T | null; verses: (Verse & { from: T })[] } {
	if (!readings.length) return { reading: null, verses: [] };
	const at = localDayNumber(date) % readings.length;
	const verses: (Verse & { from: T })[] = [];
	for (let i = 1; i <= readings.length; i++) {
		const from = readings[(at + i) % readings.length];
		const verse = splitVerse(from.excerpt);
		if (verse) verses.push({ ...verse, from });
	}
	return { reading: readings[at], verses };
}

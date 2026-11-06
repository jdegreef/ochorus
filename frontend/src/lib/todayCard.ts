// The home page's Today card (design #20): today's verse and the devotional
// reading for this date, both drawn from the dated devotionals' shelf
// (`getDailyShelf`), so they are in the reader's own language and Bible.
// The sermon of the day is `pickDailySermon`'s. Picked CLIENT-SIDE by the
// card, for the same reason as the rest of the day's blocks: home is
// prerendered, and a build-time pick would freeze on the day of the deploy.

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

/** Spaces, brackets, dashes and full stops (Latin, Amharic, Devanagari)
 *  around a reference. */
const REF_TRIM = /^[\s()\-–—.,;:።।]+|[\s()\-–—.,;:።।]+$/g;

/**
 * The verse in a devotional's opening line, split from its reference:
 * `“Bless the Lord, O, my soul” (Ps. ciii. 1).` → text + `Ps. ciii. 1`.
 * Only a line that opens on a quotation and ends on a reference with a number
 * in it is a verse: a poem's first line, or an excerpt cut short ("…"),
 * returns null.
 */
export function splitVerse(excerpt: string): Verse | null {
	const line = excerpt.trim();
	const closers = CLOSERS[line[0]];
	if (!closers) return null;
	const end = Math.max(...[...closers].map((c) => line.lastIndexOf(c)));
	if (end < 2) return null;
	const text = line.slice(1, end).trim();
	const ref = line.slice(end + 1).replace(REF_TRIM, '');
	if (!text || !/\d/.test(ref) || ref.length > 40) return null;
	return { text, ref };
}

/**
 * The day's devotional — one of the shelf's books, a different one each day
 * — and the verse, taken from another book's entry where one opens on a
 * verse (else the same book's), so the two columns don't repeat each other.
 * Either is null when the shelf has none.
 */
export function pickToday<T extends { excerpt: string }>(
	readings: readonly T[],
	date: Date
): { reading: T | null; verse: (Verse & { from: T }) | null } {
	if (!readings.length) return { reading: null, verse: null };
	const at = localDayNumber(date) % readings.length;
	const reading = readings[at];
	// The others first, starting after the day's book; the day's own book last.
	for (let i = 1; i <= readings.length; i++) {
		const from = readings[(at + i) % readings.length];
		const verse = splitVerse(from.excerpt);
		if (verse) return { reading, verse: { ...verse, from } };
	}
	return { reading, verse: null };
}

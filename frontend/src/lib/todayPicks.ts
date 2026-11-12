// The day's three picks — the verse, the devotional reading for this date and
// the sermon of the day — fetched and chosen together, for everything that
// shows "today" in one piece (the home page's Today card first). One
// function, so no two of them can disagree about what today's verse is.
//
// The verse and the reading come from the dated devotionals' shelf
// (`getDailyShelf`), so outside English the verse is in the reader's language
// and Bible. English Scripture is the Open Word Bible (CLAUDE.md), so in
// English the shelf only supplies the day's references: the first one the
// Scripture API knows is shown in the OWB's words, tagged OWB. The sermon is
// `pickDailySermon`'s. Chosen with the caller's LOCAL date: every caller is
// client-side for that reason.

import { getDailyShelf, listSermons, type DailyEntry, type SermonSummary } from '$lib/library-public';
import { dateKey } from '$lib/dailyDate';
import { pickDailySermon } from '$lib/dailySermon';
import { pickToday, type Verse } from '$lib/todayCard';
import { lookupScripture } from '$lib/scripture.svelte';
import { contentLang } from '$lib/reading';

export type TodayPicks = {
	reading: DailyEntry | null;
	/** The verse, and the language its words are in. */
	verse: (Verse & { lang: string }) | null;
	sermon: SermonSummary | null;
};

/** How many of the shelf's references English tries in the OWB. */
const OWB_TRIES = 3;

/** The day's verse: the first candidate, or in English the first one the
 *  OWB has (looked up together; null when it has none of them). */
async function verseOf(verses: (Verse & { from: DailyEntry })[], lang: string): Promise<TodayPicks['verse']> {
	if (lang !== 'en') {
		const v = verses[0];
		return v ? { text: v.text, ref: v.ref, lang: contentLang(v.from.book.language) } : null;
	}
	const found = await Promise.all(verses.slice(0, OWB_TRIES).map((v) => lookupScripture(v.ref)));
	const hit = found.find((r) => r?.verses.length);
	return hit
		? { text: hit.verses.map((v) => v.text).join(' '), ref: `${hit.reference} · OWB`, lang: 'en' }
		: null;
}

/**
 * Today's picks in `lang` for the local date of `now`. A failed fetch leaves
 * that pick null (a language with no devotional has no verse or reading, one
 * with no sermon no sermon) rather than failing the whole day.
 */
export async function loadTodayPicks(now: Date, lang: string): Promise<TodayPicks> {
	const [readings, sermons] = await Promise.all([
		getDailyShelf(dateKey(now), lang).then((r) => r.readings, () => []),
		listSermons(lang).catch(() => [])
	]);
	const { reading, verses } = pickToday(readings, now);
	return { reading, verse: await verseOf(verses, lang), sermon: pickDailySermon(sermons, now) };
}

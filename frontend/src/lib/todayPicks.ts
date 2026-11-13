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

import { getBook, getDailyShelf, listSermons, type DailyEntry, type SermonSummary } from '$lib/library-public';
import { bibleIn } from '$lib/bible';
import { pickDailyChapter, type DailyChapter } from '$lib/dailyChapter';
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
	/** The chapter of the day ($lib/dailyChapter), where the language has the
	 *  Bible (`bibleIn`); `word_count` when the book's contents could be fetched. */
	chapter: (DailyChapter & { word_count?: number }) | null;
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
 * The verse alone for the local date of `day` — what the home-screen widget
 * stores for the next few days ($lib/widgetSync), chosen exactly as
 * `loadTodayPicks` chooses it, so the widget and the Today card agree. Null
 * when the language has none, or the fetch failed.
 */
export async function loadDayVerse(day: Date, lang: string): Promise<TodayPicks['verse']> {
	const readings = await getDailyShelf(dateKey(day), lang).then((r) => r.readings, () => []);
	return verseOf(pickToday(readings, day).verses, lang);
}

/**
 * Today's picks in `lang` for the local date of `now`. A failed fetch leaves
 * that pick null (a language with no devotional has no verse or reading, one
 * with no sermon no sermon) rather than failing the whole day.
 */
export async function loadTodayPicks(now: Date, lang: string): Promise<TodayPicks> {
	const [readings, sermons, chapter] = await Promise.all([
		getDailyShelf(dateKey(now), lang).then((r) => r.readings, () => []),
		listSermons(lang).catch(() => []),
		chapterOf(now, lang)
	]);
	const { reading, verses } = pickToday(readings, now);
	return { reading, verse: await verseOf(verses, lang), sermon: pickDailySermon(sermons, now), chapter };
}

/** The chapter of the day where `lang` has the Bible, with its length from the
 *  book's contents. The pick never waits on that fetch's success: without it
 *  the chapter is still offered, only with no reading time. */
async function chapterOf(now: Date, lang: string): Promise<TodayPicks['chapter']> {
	if (!bibleIn(lang)) return null;
	const pick = pickDailyChapter(now);
	const toc = await getBook(pick.slug, lang).then((b) => b.chapters, () => []);
	const word_count = toc.find((c) => c.order === pick.order)?.word_count;
	return word_count ? { ...pick, word_count } : pick;
}

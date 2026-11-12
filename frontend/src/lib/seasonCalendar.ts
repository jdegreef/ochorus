/**
 * The Advent and Lent calendars (design #34): in the season, /today and the
 * home page's Today card show a door for each day — past doors open on the
 * day's short reading and its line of Scripture, today's is lit, the rest
 * stay shut until their day.
 *
 * One data shape serves both seasons. A season is a WINDOW (`adventWindow`,
 * `lentWindow`): the calendar days that get a door, computed from the date
 * (never written down, so it is right in any year). Its doors are a curated
 * list of readings that already exist in the library (`ADVENT_DOORS`,
 * `LENT_DOORS`), laid on the window's days in order.
 *
 * - Advent runs from Advent Sunday to Christmas Eve, a door every day: 22 to
 *   28 of them, depending on the weekday Christmas falls on. The list is
 *   written for the longest Advent; a shorter one drops its `spare` entries,
 *   the last first, so the first door is always the opening of the season and
 *   the last always the birth.
 * - Lent runs from Ash Wednesday to Holy Saturday, the forty days without
 *   their Sundays (the Sundays are feasts, not fast days, and are not
 *   counted). `liturgicalSeason` splits off Holy Week; the calendar keeps it.
 *
 * Content is per-language and there is no English fallback (CLAUDE.md): a
 * door shows only when its reading exists in the reader's language, and a
 * language left with too few doors (`MIN_SHARE`) has no calendar at all.
 * Every date is the reader's LOCAL calendar day, so the calendar is built
 * client-side — a prerender would freeze on the build day.
 */
import { localDayNumber } from './dailyArticles';
import { adventStart, dayNumber, easterDay } from './liturgical';
import { chapterPath } from './editionHref';
import { ApiError } from './api';
import { getBookExact, listSermons } from './library-public';

export type CalendarSeason = 'advent' | 'lent';

/** What a door opens on: a sermon (its own Scripture text goes with it) or a
 *  book chapter, with the verse it is read beside — in English, the house
 *  Bible's (OWB) words for it are shown on the day. */
export type DoorReading =
	| { kind: 'sermon'; slug: string }
	| { kind: 'chapter'; book: string; chapter: number; ref: string };

export interface CalendarEntry {
	reading: DoorReading;
	/** May be left out when the season is short (Advent only). */
	spare?: true;
}

const sermon = (slug: string, spare?: true): CalendarEntry => ({ reading: { kind: 'sermon', slug }, spare });
const chapter = (book: string, n: number, ref: string, spare?: true): CalendarEntry => ({
	reading: { kind: 'chapter', book, chapter: n, ref },
	spare
});

/**
 * Advent, for its longest year (28 days). Four movements, as the /advent/
 * hub's plan: waiting and watching for the Lord's coming; the prophets'
 * promises; the Word made flesh; the Christmas story, Luke 1–2, to the birth
 * on Christmas Eve. Seven spares, one more than the shortest Advent (22 days)
 * needs.
 */
export const ADVENT_DOORS: readonly CalendarEntry[] = [
	// Waiting for the Lord
	chapter('waiting-on-god', 30, 'Luke 12:36'), // For the Coming of His Son
	sermon('the-practical-hope-of-the-lords-coming'), // Simpson, James 5:7-8
	sermon('one-antidote-for-many-ills', true), // Spurgeon, Psalm 80:19
	chapter('waiting-on-god', 28, 'Micah 7:7'), // In Holy Expectancy
	sermon('waiting-only-upon-god', true), // Spurgeon, Psalm 62:6
	chapter('waiting-on-god', 19, 'Isaiah 8:17', true), // In Times of Darkness
	sermon('the-appearing-of-the-grace-of-god'), // Luther, Titus 2:11-15
	// Promised by the prophets
	sermon('comfort-ye-my-people'), // Newton, Isaiah 40:1
	sermon('waiting-and-singing', true), // Maclaren, Psalm 59:9
	chapter('the-first-apology', 33, 'Isaiah 7:14'), // Manner of Christ's birth predicted
	chapter('the-first-apology', 34, 'Micah 5:2'), // Place of Christ's birth foretold
	sermon('the-immutability-of-god'), // Spurgeon, Malachi 3:6
	sermon('brave-encouragements', true), // Maclaren, Haggai 2:1-9
	sermon('the-joy-bringer'), // Maclaren, Isaiah 61:3
	sermon('the-heavenly-workers-and-the-earthly-watchers', true), // Maclaren, Isaiah 62:1
	sermon('unto-us-a-child-is-born'), // Newton, Isaiah 9:6
	// The Word made flesh
	chapter('on-the-incarnation', 8, 'Hebrews 2:14'), // The Word visited the earth
	sermon('bethlehem-and-its-good-news'), // Bonar, John 1:14
	sermon('grace-and-truth'), // Maclaren, John 1:17
	sermon('behold-the-lamb-of-god'), // Newton, John 1:29
	sermon('the-mystery-of-godliness', true), // Calvin, 1 Timothy 3:16
	// The Christmas story
	chapter('hurlbuts-life-of-christ', 4, 'Luke 1:13'), // The Stranger by the Golden Altar
	chapter('hurlbuts-life-of-christ', 5, 'Luke 1:31'), // The Angel Visits Nazareth
	chapter('hurlbuts-life-of-christ', 6, 'Luke 1:46-47'), // A Young Girl's Journey (the Magnificat)
	chapter('hurlbuts-life-of-christ', 7, 'Luke 1:68'), // The Boy Who Never Tasted Wine (the Benedictus)
	chapter('hurlbuts-life-of-christ', 8, 'Luke 2:7'), // The Child-King in His Cradle
	sermon('the-angels-message-and-song'), // Newton, Luke 2:8-14
	sermon('the-story-of-the-birth-of-jesus') // Luther, Luke 2:1-14 — Christmas Eve
];

/**
 * Lent's forty doors — not curated yet (Ash Wednesday 2027 is 10 February).
 * Same shape as Advent's, forty entries, no spares (Lent is always forty
 * days). Until it is filled, `buildCalendar` finds no doors and nothing shows.
 */
export const LENT_DOORS: readonly CalendarEntry[] = [];

export const SEASON_DOORS: Record<CalendarSeason, readonly CalendarEntry[]> = {
	advent: ADVENT_DOORS,
	lent: LENT_DOORS
};

const DAY_MS = 86_400_000;
const weekday = (day: number) => new Date(day * DAY_MS).getUTCDay();
const range = (from: number, to: number) => Array.from({ length: to - from + 1 }, (_, i) => from + i);

export interface SeasonWindow {
	season: CalendarSeason;
	/** The year the season ends in (Lent's and Advent's alike are one civil year). */
	year: number;
	/** The days that get a door, as day numbers (`localDayNumber`), in order. */
	days: number[];
}

/** Advent Sunday to Christmas Eve, a door every day. */
export function adventWindow(year: number): SeasonWindow {
	const start = adventStart(year);
	return { season: 'advent', year, days: range(start, dayNumber(year, 11, 24)) };
}

/** Ash Wednesday (Easter − 46) to Holy Saturday, without the Sundays: forty. */
export function lentWindow(year: number): SeasonWindow {
	const easter = easterDay(year);
	return { season: 'lent', year, days: range(easter - 46, easter - 1).filter((d) => weekday(d) !== 0) };
}

/** The calendar season the reader's local `date` falls in, or null. A Sunday
 *  in Lent is inside it, though it has no door of its own. */
export function seasonWindowOn(date: Date): SeasonWindow | null {
	const today = localDayNumber(date);
	const year = date.getFullYear();
	for (const w of [adventWindow(year), lentWindow(year)]) {
		if (today >= w.days[0] && today <= w.days[w.days.length - 1]) return w;
	}
	return null;
}

/** `entries` fitted to `count` doors: spares dropped, the last first, until
 *  it fits (a list still too long is cut; one too short leaves days bare). */
export function fitEntries(entries: readonly CalendarEntry[], count: number): readonly CalendarEntry[] {
	let over = entries.length - count;
	if (over <= 0) return entries;
	const drop = new Set<number>();
	for (let i = entries.length - 1; i >= 0 && over > 0; i--) {
		if (entries[i].spare) {
			drop.add(i);
			over--;
		}
	}
	return entries.filter((_, i) => !drop.has(i)).slice(0, count);
}

export type DoorState = 'open' | 'today' | 'locked';

/** Past days are open, today's is lit, the rest are shut. */
export const doorState = (day: number, today: number): DoorState =>
	day < today ? 'open' : day === today ? 'today' : 'locked';

/** What the reader's language has, for resolving doors: its sermons, and the
 *  books asked for (only an edition truly in that language — no English
 *  fallback stands in for it). */
export interface Shelf {
	sermons: ReadonlyMap<string, { title: string; scripture_ref: string }>;
	books: ReadonlyMap<
		string,
		{ title: string; has_modern_edition?: boolean; chapters: readonly { order: number; title: string }[] }
	>;
	/** A book fetch failed for a reason other than "not in this language":
	 *  the shelf is used, but not kept, so the next look retries it. */
	partial?: boolean;
}

export interface Door {
	/** 1-based position in the season (gaps where a language has no reading). */
	n: number;
	day: number;
	state: DoorState;
	title: string;
	/** The work it is from: a chapter's book; '' for a sermon. */
	source: string;
	/** The Scripture reference, in the reader's language; '' where there is
	 *  none in it (a chapter's reference is written in English). */
	ref: string;
	/** An English reference the house Bible can be asked for ('' outside English). */
	owbRef: string;
	kind: DoorReading['kind'];
	slug: string;
	chapter: number;
	hasModern: boolean;
}

/** The book slugs a season's doors read from — what a loader must fetch. */
export const doorBooks = (entries: readonly CalendarEntry[]): string[] => [
	...new Set(entries.flatMap((e) => (e.reading.kind === 'chapter' ? [e.reading.book] : [])))
];

/**
 * The window's doors in `lang` as of day number `today`: each day matched to
 * its entry, and kept only when the reading exists in `shelf`.
 */
export function resolveDoors(
	w: SeasonWindow,
	entries: readonly CalendarEntry[],
	shelf: Shelf,
	lang: string,
	today: number
): Door[] {
	const fitted = fitEntries(entries, w.days.length);
	const en = lang === 'en';
	const doors: Door[] = [];
	w.days.forEach((day, i) => {
		const r = fitted[i]?.reading;
		if (!r) return;
		const base = { n: i + 1, day, state: doorState(day, today) };
		if (r.kind === 'sermon') {
			const s = shelf.sermons.get(r.slug);
			if (!s) return;
			doors.push({
				...base,
				title: s.title,
				source: '',
				ref: s.scripture_ref,
				owbRef: en ? s.scripture_ref : '',
				kind: 'sermon',
				slug: r.slug,
				chapter: 0,
				hasModern: false
			});
			return;
		}
		const b = shelf.books.get(r.book);
		const c = b?.chapters.find((ch) => ch.order === r.chapter);
		if (!b || !c) return;
		doors.push({
			...base,
			title: c.title,
			source: b.title,
			ref: en ? r.ref : '',
			owbRef: en ? r.ref : '',
			kind: 'chapter',
			slug: r.book,
			chapter: r.chapter,
			hasModern: !!b.has_modern_edition
		});
	});
	return doors;
}

/** The share of a season's days that must have a door in the reader's
 *  language for its calendar to show: fewer, and it is gaps more than doors. */
export const MIN_SHARE = 1 / 3;

/** Whether `doors` make a calendar for window `w`. */
export const enoughDoors = (w: SeasonWindow, doors: readonly Door[]) =>
	doors.length > 0 && doors.length >= Math.ceil(w.days.length * MIN_SHARE);

/** A door's reading's path (unlocalized). A chapter honours "Prefer Modern
 *  English", as every other way into a chapter does. */
export const doorPath = (d: Door): string =>
	d.kind === 'sermon' ? `/sermons/${d.slug}` : chapterPath(d.slug, d.chapter, d.hasModern);

export interface Calendar {
	window: SeasonWindow;
	doors: Door[];
	/** Today's door, when today has one in this language. */
	today: Door | null;
}

/** One fetch of a language's shelf per season per page: the Today card and
 *  /today ask for the same one, and a day turning over reuses it. */
const shelves = new Map<string, Promise<Shelf>>();

async function fetchShelf(lang: string, books: string[]): Promise<Shelf> {
	let partial = false;
	const [sermons, editions] = await Promise.all([
		listSermons(lang),
		Promise.all(
			books.map((slug) =>
				getBookExact(slug, lang).catch((e) => {
					// A 404 is an answer (no edition in this language); anything
					// else is a failure worth asking again.
					if (!(e instanceof ApiError && e.status === 404)) partial = true;
					return null;
				})
			)
		)
	]);
	return {
		sermons: new Map(sermons.filter((s) => s.language === lang).map((s) => [s.slug, s])),
		books: new Map(editions.flatMap((b) => (b && b.language === lang ? [[b.slug, b] as const] : []))),
		partial
	};
}

/**
 * The calendar for the reader's local `now` in `lang`, or null out of season,
 * or when the language has too few of the season's readings. A failed
 * sermon fetch shows no calendar and is not cached, so it is retried; a
 * book that fails drops only its own doors, and the shelf is not kept, so
 * the next call asks for it again.
 */
export async function loadCalendar(now: Date, lang: string): Promise<Calendar | null> {
	const w = seasonWindowOn(now);
	const entries = w ? SEASON_DOORS[w.season] : [];
	if (!w || !entries.length) return null;
	const key = `${w.season}-${w.year}-${lang}`;
	let shelf = shelves.get(key);
	if (!shelf) {
		shelf = fetchShelf(lang, doorBooks(entries));
		shelves.set(key, shelf);
	}
	let got: Shelf;
	try {
		got = await shelf;
	} catch {
		shelves.delete(key);
		return null;
	}
	if (got.partial && shelves.get(key) === shelf) shelves.delete(key);
	const doors = resolveDoors(w, entries, got, lang, localDayNumber(now));
	if (!enoughDoors(w, doors)) return null;
	return { window: w, doors, today: doors.find((d) => d.state === 'today') ?? null };
}

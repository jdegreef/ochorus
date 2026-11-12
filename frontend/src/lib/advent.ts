/**
 * The /advent/ hub: which Advent a date belongs to, where the reader stands in
 * it, and the hub's hand-picked shelves.
 *
 * Every date is computed (`adventStart`, the fourth Sunday before Christmas),
 * never written down, so the page is right in any year without an edit. The
 * prerender bakes the build day's answer; the page recomputes on mount.
 *
 * English-only, like /quotes and /scripture: the plan it leads with reads
 * books that exist only in English, so there is no localized hub to serve.
 */
import { localDayNumber } from './dailyArticles';
import { adventStart } from './liturgical';

/** The reading plan the hub leads with (backend `plan_seed.CURATED_PLANS`). */
export const ADVENT_PLAN = 'advent-with-the-classics';

/** The season in the Bible itself (Open Word Bible, English only — as is this
 *  hub): offered beside the classics plan, 1 December to Christmas Day. */
export const ADVENT_SCRIPTURE_PLAN = 'advent-in-scripture';

/** The plan's four weeks, in order: its days run in sevens (plan_seed's
 *  comment on the plan holds it to that). A label for each week of days. */
export const ADVENT_WEEKS = [
	'Waiting for the Lord',
	'Promised by the prophets',
	'The Word made flesh',
	'The Christmas story'
];

/** Books on the incarnation and the waiting, beyond the plan's own. */
export const ADVENT_BOOKS = [
	'on-the-incarnation',
	'waiting-on-god',
	'hurlbuts-life-of-christ',
	'the-great-catechism',
	'the-everlasting-man',
	'tell-me-the-story-4'
];

/** Sermons for Advent and Christmas: the promise, the birth, the coming again. */
export const ADVENT_SERMONS = [
	'comfort-ye-my-people',
	'unto-us-a-child-is-born',
	'the-story-of-the-birth-of-jesus',
	'bethlehem-and-its-good-news',
	'religious-joy',
	'the-song-of-the-angels',
	'the-appearing-of-the-grace-of-god',
	'the-practical-hope-of-the-lords-coming'
];

const DAY_MS = 86_400_000;
/** Christmas Eve of `year` as a day number (`adventStart`'s unit). */
const christmasEve = (year: number) => Date.UTC(year, 11, 24) / DAY_MS;

export interface AdventWindow {
	year: number;
	/** Advent Sunday and Christmas Eve, as day numbers. */
	start: number;
	end: number;
}

/**
 * The Advent a reader on `date` is looking towards: this year's until its last
 * day (Christmas Eve), then next year's — so from Christmas Day the hub already
 * points at the coming one.
 */
export function adventFor(date: Date): AdventWindow {
	const today = localDayNumber(date);
	let year = date.getFullYear();
	if (today > christmasEve(year)) year += 1;
	return { year, start: adventStart(year), end: christmasEve(year) };
}

export type AdventStatus =
	| { kind: 'before'; days: number }
	| { kind: 'during'; week: number; daysToChristmas: number };

/** How far off Advent is, or which week of it `date` falls in (1–4). */
export function adventStatus(date: Date, w: AdventWindow = adventFor(date)): AdventStatus {
	const today = localDayNumber(date);
	if (today < w.start) return { kind: 'before', days: w.start - today };
	return {
		kind: 'during',
		week: Math.floor((today - w.start) / 7) + 1,
		daysToChristmas: w.end + 1 - today
	};
}

const fmt = (opts: Intl.DateTimeFormatOptions) =>
	new Intl.DateTimeFormat('en-GB', { ...opts, timeZone: 'UTC' });
const LONG = fmt({ weekday: 'long', day: 'numeric', month: 'long' });
const DAY_MONTH = fmt({ day: 'numeric', month: 'long' });
const SHORT = fmt({ weekday: 'short', day: 'numeric', month: 'short' });

/** "Sunday 29 November" */
export const longDate = (day: number) => LONG.format(day * DAY_MS);
/** "29 November" */
export const dayMonth = (day: number) => DAY_MONTH.format(day * DAY_MS);
/** "Sun 29 Nov" */
export const shortDate = (day: number) => SHORT.format(day * DAY_MS);

/** The hub's one status line for `date`. */
export function statusLine(date: Date, w: AdventWindow = adventFor(date)): string {
	const s = adventStatus(date, w);
	if (s.kind === 'before') {
		const when = s.days === 1 ? 'tomorrow' : `in ${s.days} days`;
		return `Advent begins ${when}, on ${longDate(w.start)}.`;
	}
	const toGo = s.daysToChristmas === 1 ? 'Christmas is tomorrow' : `${s.daysToChristmas} days to Christmas`;
	return `The ${['first', 'second', 'third', 'fourth'][s.week - 1]} week of Advent · ${toGo}.`;
}

/** The plan's days in weeks of seven, each with its label. */
export function planWeeks<T extends { day: number }>(days: T[]): { label: string; days: T[] }[] {
	const weeks: { label: string; days: T[] }[] = [];
	for (let i = 0; i < days.length; i += 7) {
		weeks.push({ label: ADVENT_WEEKS[i / 7] ?? `Week ${i / 7 + 1}`, days: days.slice(i, i + 7) });
	}
	return weeks;
}

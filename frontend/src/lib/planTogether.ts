/**
 * "Read together": a group reading one plan on the same dates, carried
 * entirely by a link — `/plans/<slug>/?together=2026-10-12&days=weekdays`.
 *
 * Nothing about the group is stored anywhere but in that link (and, once a
 * reader joins, on their own device): no accounts, no member list, no
 * progress shared with anyone. Everyone who opens the link computes the same
 * "the group is on Day 4 today" from the start date and the reading days
 * alone, the way a printed reading schedule works. Pure, so the arithmetic is
 * tested apart from the page.
 */
import { READING_DAYS, parseIsoDay, schedulePlan, type ReadingDays } from './planSchedule';
import { localToday } from './streak';

/** A group's shared schedule: the day it starts and the days it reads on. */
export interface Together {
	/** `YYYY-MM-DD`. */
	start: string;
	rule: ReadingDays;
}

/** The query parameters a "read together" link carries. */
const START = 'together';
const DAYS = 'days';

/** A link's group, or null when it carries none (or a malformed one). An
 *  unknown reading-days rule reads as daily rather than voiding the invite. */
export function togetherFromQuery(params: URLSearchParams): Together | null {
	const start = params.get(START) ?? '';
	if (!parseIsoDay(start)) return null;
	const days = params.get(DAYS);
	const rule = READING_DAYS.find((r) => r === days) ?? 'daily';
	return { start, rule };
}

/** The query string that carries `t` (daily is the default, so it is left out). */
export const togetherQuery = (t: Together): string =>
	`?${START}=${t.start}` + (t.rule === 'daily' ? '' : `&${DAYS}=${t.rule}`);

/** Where the group is on `today`. */
export type GroupStatus =
	| { kind: 'before'; starts: Date }
	| { kind: 'today'; day: number }
	| { kind: 'next'; day: number; date: Date }
	| { kind: 'finished'; ended: Date };

/**
 * The group's day on `today`: every day of the plan laid on the shared
 * calendar (planSchedule's rule, so the group's dates and a member's own
 * calendar agree), then today found among them.
 */
export function groupStatus(t: Together, dayCount: number, today: Date): GroupStatus {
	const start = parseIsoDay(t.start)!;
	const days = schedulePlan(
		Array.from({ length: dayCount }, (_, i) => i + 1),
		start,
		t.rule
	);
	const now = localToday(today);
	if (!days.length || now < localToday(days[0].date)) return { kind: 'before', starts: days[0]?.date ?? start };
	const last = days[days.length - 1];
	if (now > localToday(last.date)) return { kind: 'finished', ended: last.date };
	const at = days.find((d) => localToday(d.date) >= now)!;
	return localToday(at.date) === now ? { kind: 'today', day: at.item } : { kind: 'next', day: at.item, date: at.date };
}

/** How a group's dates read: "Monday, October 12" in the reader's language. */
export const groupDateFormat = (lang: string) =>
	new Intl.DateTimeFormat(lang, { weekday: 'long', month: 'long', day: 'numeric' });

/** The day a leader is offered first: the coming Monday (today, if it is one),
 *  which is where most groups begin a week of reading. */
export function nextMonday(today: Date): string {
	const d = new Date(today.getFullYear(), today.getMonth(), today.getDate());
	d.setDate(d.getDate() + ((8 - d.getDay()) % 7));
	return localToday(d);
}

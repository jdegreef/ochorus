/**
 * A reading plan laid out on real dates: which day of the plan falls on which
 * date for a reader starting on a given day and reading on chosen weekdays.
 * Pure, so the schedule (and the calendar file built from it) is unit-tested
 * apart from the page.
 */
import { localToday } from './streak';

/** Which weekdays a reader reads on. */
export const READING_DAYS = ['daily', 'weekdays', 'monsat'] as const;
export type ReadingDays = (typeof READING_DAYS)[number];

/** Does `rule` read on this date? (getDay: 0 = Sunday … 6 = Saturday.) */
export const readsOn = (date: Date, rule: ReadingDays): boolean => {
	const wd = date.getDay();
	if (rule === 'weekdays') return wd >= 1 && wd <= 5;
	if (rule === 'monsat') return wd !== 0;
	return true;
};

/** The local date a `YYYY-MM-DD` string (localToday's format) names, or null. */
export const parseIsoDay = (s: string): Date | null => {
	const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(s);
	if (!m) return null;
	const d = new Date(+m[1], +m[2] - 1, +m[3]);
	return localToday(d) === s ? d : null;
};

/**
 * Each item (a plan's days still to read, in order) on its date: the first on
 * the first reading day on or after `start`, each next on the following one.
 */
export function schedulePlan<T>(items: T[], start: Date, rule: ReadingDays): { item: T; date: Date }[] {
	const out: { item: T; date: Date }[] = [];
	const cur = new Date(start.getFullYear(), start.getMonth(), start.getDate());
	for (const item of items) {
		while (!readsOn(cur, rule)) cur.setDate(cur.getDate() + 1);
		out.push({ item, date: new Date(cur) });
		cur.setDate(cur.getDate() + 1);
	}
	return out;
}

/**
 * The locale's first day of the week (0 = Sunday … 6 = Saturday): Sunday for
 * en-US, Monday for most of the world. Intl's week info where the browser has
 * it, else Monday.
 */
export function weekStart(lang: string): number {
	try {
		const loc = new Intl.Locale(lang) as Intl.Locale & {
			getWeekInfo?: () => { firstDay: number };
			weekInfo?: { firstDay: number };
		};
		const first = (loc.getWeekInfo?.() ?? loc.weekInfo)?.firstDay;
		if (first) return first % 7; // Intl counts Monday 1 … Sunday 7
	} catch {
		// An unknown tag: fall through.
	}
	return 1;
}

/** A day in a month grid, with its `YYYY-MM-DD` key computed once. */
export interface GridDay {
	date: Date;
	iso: string;
}

/**
 * The weeks of a month as rows of seven days, starting on `firstDay`, padded
 * with the neighbouring months' days so every row is whole.
 */
export function monthGrid(year: number, month: number, firstDay = 1): GridDay[][] {
	const first = new Date(year, month, 1);
	const lead = (first.getDay() - firstDay + 7) % 7;
	const cur = new Date(year, month, 1 - lead);
	const weeks: GridDay[][] = [];
	do {
		const week: GridDay[] = [];
		for (let i = 0; i < 7; i++) {
			week.push({ date: new Date(cur), iso: localToday(cur) });
			cur.setDate(cur.getDate() + 1);
		}
		weeks.push(week);
	} while (cur.getMonth() === month);
	return weeks;
}

/**
 * A reading plan laid out on real dates: which day of the plan falls on which
 * date for a reader starting on a given day and reading on chosen weekdays.
 * Pure, so the schedule (and the calendar file built from it) is unit-tested
 * apart from the page.
 */

/** Which weekdays a reader reads on. */
export type ReadingDays = 'daily' | 'weekdays' | 'monsat';

export const READING_DAYS: ReadingDays[] = ['daily', 'weekdays', 'monsat'];

/** Does `rule` read on this date? (getDay: 0 = Sunday … 6 = Saturday.) */
export const readsOn = (date: Date, rule: ReadingDays): boolean => {
	const wd = date.getDay();
	if (rule === 'weekdays') return wd >= 1 && wd <= 5;
	if (rule === 'monsat') return wd !== 0;
	return true;
};

/** Local midnight of `d` — schedules are in whole days, never times. */
export const startOfDay = (d: Date): Date => new Date(d.getFullYear(), d.getMonth(), d.getDate());

/** `YYYY-MM-DD` for a local date — the schedule's map key and the date input's value. */
export const isoDay = (d: Date): string =>
	`${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;

/** The local date a `YYYY-MM-DD` string names, or null for anything else. */
export const parseIsoDay = (s: string): Date | null => {
	const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(s);
	if (!m) return null;
	const d = new Date(+m[1], +m[2] - 1, +m[3]);
	return isoDay(d) === s ? d : null;
};

/**
 * Each of `days` (plan day numbers, in order) on its date: the first on the
 * first reading day on or after `start`, each next one on the following
 * reading day.
 */
export function schedulePlan(
	days: number[],
	start: Date,
	rule: ReadingDays
): { day: number; date: Date }[] {
	const out: { day: number; date: Date }[] = [];
	const cur = startOfDay(start);
	for (const day of days) {
		while (!readsOn(cur, rule)) cur.setDate(cur.getDate() + 1);
		out.push({ day, date: new Date(cur) });
		cur.setDate(cur.getDate() + 1);
	}
	return out;
}

/**
 * The weeks of a month as rows of seven local dates, Monday first, padded
 * with the neighbouring months' days so every row is whole.
 */
export function monthGrid(year: number, month: number): Date[][] {
	const first = new Date(year, month, 1);
	const lead = (first.getDay() + 6) % 7; // days before it back to Monday
	const cur = new Date(year, month, 1 - lead);
	const weeks: Date[][] = [];
	do {
		const week: Date[] = [];
		for (let i = 0; i < 7; i++) {
			week.push(new Date(cur));
			cur.setDate(cur.getDate() + 1);
		}
		weeks.push(week);
	} while (cur.getMonth() === month);
	return weeks;
}

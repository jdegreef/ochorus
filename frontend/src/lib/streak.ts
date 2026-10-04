/**
 * Reading-streak maths over an activity log of local calendar days ('YYYY-MM-DD').
 * Pure and timezone-safe: day arithmetic parses as UTC midnight so it never
 * drifts, while "today" is the reader's *local* date (a streak is a wall-clock,
 * human notion). `now` is injectable for deterministic tests.
 */

/** A local 'YYYY-MM-DD' shifted by `n` days. */
export function shiftDay(iso: string, n: number): string {
	const d = new Date(iso + 'T00:00:00Z');
	d.setUTCDate(d.getUTCDate() + n);
	return d.toISOString().slice(0, 10);
}

/** Today's *local* date as 'YYYY-MM-DD'. */
export function localToday(now: Date = new Date()): string {
	const p = (x: number) => String(x).padStart(2, '0');
	return `${now.getFullYear()}-${p(now.getMonth() + 1)}-${p(now.getDate())}`;
}

/**
 * Consecutive days read, ending today — or ending yesterday if today hasn't been
 * read yet, so a streak doesn't visibly "break" until a whole day passes unread.
 */
export function currentStreak(days: Iterable<string>, today: string): number {
	const set = new Set(days);
	let cursor = today;
	if (!set.has(cursor)) {
		cursor = shiftDay(today, -1);
		if (!set.has(cursor)) return 0;
	}
	let count = 0;
	while (set.has(cursor)) {
		count += 1;
		cursor = shiftDay(cursor, -1);
	}
	return count;
}

const ISO_DAY = /^\d{4}-\d{2}-\d{2}$/;

/**
 * Each logged day's 1-based place in its run of consecutive days. Malformed
 * entries (a corrupt cache, a bad sync row) are skipped rather than allowed to
 * throw in the date maths and take the calendar down with them.
 */
export function runLengths(days: Iterable<string>): Map<string, number> {
	const runs = new Map<string, number>();
	for (const day of [...new Set(days)].filter((d) => ISO_DAY.test(d)).sort()) {
		runs.set(day, (runs.get(shiftDay(day, -1)) ?? 0) + 1);
	}
	return runs;
}

/** The longest run of consecutive days in the log. */
export function longestStreak(days: Iterable<string>): number {
	let best = 0;
	for (const run of runLengths(days).values()) if (run > best) best = run;
	return best;
}

/** The streak's flame, by length: a spark under a week, a flame to a month, a
 *  blaze to a hundred days, then a crown. Drawn larger and brighter each step
 *  (DashboardStats); a milestone worth noticing, not a score. The reading
 *  calendar shades a run by the same steps (`runLevel`), so the flame and the
 *  calendar's present end always say the same thing. */
export const STREAK_TIERS = ['spark', 'flame', 'blaze', 'crown'] as const;
export type StreakTier = (typeof STREAK_TIERS)[number];

export function streakTier(streak: number): StreakTier {
	if (streak >= 100) return 'crown';
	if (streak >= 30) return 'blaze';
	if (streak >= 7) return 'flame';
	return 'spark';
}

/** A read day's calendar shade: 0 unread, else 1–4 by the tier its run has
 *  reached on that day (spark 1, flame 2, blaze 3, crown 4). */
export function runLevel(run: number): 0 | 1 | 2 | 3 | 4 {
	if (run <= 0) return 0;
	return (STREAK_TIERS.indexOf(streakTier(run)) + 1) as 1 | 2 | 3 | 4;
}

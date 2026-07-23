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

/** The longest run of consecutive days in the log. */
export function longestStreak(days: Iterable<string>): number {
	const sorted = [...new Set(days)].sort();
	let best = 0;
	let run = 0;
	let prev: string | null = null;
	for (const d of sorted) {
		run = prev && shiftDay(prev, 1) === d ? run + 1 : 1;
		if (run > best) best = run;
		prev = d;
	}
	return best;
}

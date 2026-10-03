/**
 * Contribution-style reading heatmap maths over the activity log of local
 * calendar days ('YYYY-MM-DD') — the same log the streak uses (see streak.ts).
 * Pure and timezone-safe: day arithmetic parses as UTC midnight, and month
 * labels format in UTC so they never drift a day. Weeks start on Sunday
 * (row 0 = Sunday … row 6 = Saturday), matching the familiar contribution grid.
 */

import { runLengths, runLevel, shiftDay } from './streak';

/** One day cell in the grid. `future` = after today (a trailing placeholder in
 *  the current, still-unfinished week) — rendered blank, never as "unread". */
export interface HeatCell {
	iso: string;
	read: boolean;
	future: boolean;
	/** 0 unread, else 1–4 by the streak tier this day's unbroken run had
	 *  reached (streak.ts, `runLevel`) — the calendar's shade. */
	level: 0 | 1 | 2 | 3 | 4;
}


export interface HeatmapGrid {
	/** Columns, oldest→newest; each column is 7 cells, Sunday→Saturday. */
	weeks: HeatCell[][];
	/** A short month name at the column where that month first appears. */
	monthLabels: { col: number; label: string }[];
}

/** UTC weekday of a 'YYYY-MM-DD' (0 = Sunday). */
function weekday(iso: string): number {
	return new Date(iso + 'T00:00:00Z').getUTCDay();
}

function monthShort(iso: string, locale: string): string {
	return new Date(iso + 'T00:00:00Z').toLocaleDateString(locale, {
		month: 'short',
		timeZone: 'UTC'
	});
}

/**
 * Build a `weeks`-column grid ending with the week that contains `today`. The
 * last column runs to this Saturday (trailing days after today are `future`),
 * so the grid is always a clean rectangle aligned on weekday rows.
 */
export function buildHeatmap(
	days: Iterable<string>,
	today: string,
	weeks = 26,
	locale = 'en',
	runsFrom: Iterable<string> = days
): HeatmapGrid {
	// Runs are measured over `runsFrom` (by default the same log), so a view
	// that draws a slice — one year — still shades a run that began before it.
	const read = new Set(days);
	const runs = runLengths(runsFrom);
	const lastSaturday = shiftDay(today, 6 - weekday(today));
	const firstSunday = shiftDay(lastSaturday, -(weeks * 7 - 1));

	const grid: HeatCell[][] = [];
	const monthLabels: { col: number; label: string }[] = [];
	let lastMonth = '';
	let lastLabelCol = -99;
	for (let w = 0; w < weeks; w++) {
		const col: HeatCell[] = [];
		for (let d = 0; d < 7; d++) {
			const iso = shiftDay(firstSunday, w * 7 + d);
			const future = iso > today;
			const run = future || !read.has(iso) ? 0 : (runs.get(iso) ?? 0);
			col.push({ iso, read: run > 0, future, level: runLevel(run) });
		}
		// Label the column by the month its first (Sunday) cell falls in, but only
		// when that month changes — so each month is labelled once, at its start.
		// Skip a label sitting within 3 columns of the previous one, so a partial
		// first month at the left edge doesn't collide with the next month's label.
		const m = monthShort(col[0].iso, locale);
		if (m !== lastMonth) {
			lastMonth = m;
			if (w - lastLabelCol >= 3) {
				monthLabels.push({ col: w, label: m });
				lastLabelCol = w;
			}
		}
		grid.push(col);
	}
	return { weeks: grid, monthLabels };
}

/**
 * Distinct days read in the current week (Sunday through `today`) — the
 * numerator for a "days per week" goal. Never counts future days.
 */
export function weekReadCount(days: Iterable<string>, today: string): number {
	const read = new Set(days);
	const dow = weekday(today);
	const sunday = shiftDay(today, -dow);
	let count = 0;
	for (let d = 0; d <= dow; d++) {
		if (read.has(shiftDay(sunday, d))) count += 1;
	}
	return count;
}

// The reading-hours grid's derived numbers: its busiest cell, and the hour of
// day reading peaks across the week, from which a send time is suggested.
// Pure, so the page stays markup and these stay tested.

export const WEEKDAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'] as const;

/** "6am", "12pm", "11pm". */
export const hourLabel = (h: number) => `${h % 12 || 12}${h < 12 ? 'am' : 'pm'}`;

type Grid = (number | null)[][];

/** The single busiest weekday × hour, or null if no cell is shown. */
export function busiestCell(minutes: Grid) {
	let best: { day: number; hour: number; minutes: number } | null = null;
	minutes.forEach((row, day) =>
		row.forEach((m, hour) => {
			if (m && (!best || m > best.minutes)) best = { day, hour, minutes: m };
		})
	);
	return best as { day: number; hour: number; minutes: number } | null;
}

/** The hour of day with the most reading across the whole week, and a send
 *  time half an hour before it: a reminder should arrive just ahead of the
 *  habit, not on top of it. Null if no cell is shown. */
export function sendTime(minutes: Grid) {
	const byHour = Array.from({ length: 24 }, (_, h) => minutes.reduce((a, row) => a + (row[h] ?? 0), 0));
	const peak = Math.max(...byHour);
	if (!peak) return null;
	const hour = byHour.indexOf(peak);
	return { hour, label: hourLabel((hour + 23) % 24).replace(/(am|pm)$/, ':30$1') };
}

// The calendar keys the dated devotionals are addressed by: `MM-DD`.
//
// "Today" is the reader's LOCAL date, so it is worked out here, in the browser,
// and sent to the API in the URL (`/api/library/daily/<MM-DD>/`) — never left to
// the server, whose clock is UTC and whose responses are cached. The day pages
// and the Today shelf are client-rendered for the same reason: a prerendered
// "today" would freeze on the day the site last deployed.

import { localToday } from './streak';

/** `MM-DD` for `d` in the reader's own time zone. */
export function dateKey(d: Date): string {
	return localToday(d).slice(5);
}

/** Whether `s` is a real calendar `MM-DD` (29 February included — the
 *  devotionals are written against a leap year). */
export function isDateKey(s: string | null | undefined): s is string {
	const m = /^(\d{2})-(\d{2})$/.exec(s ?? '');
	if (!m) return false;
	const month = Number(m[1]);
	const day = Number(m[2]);
	return month >= 1 && month <= 12 && day >= 1 && day <= new Date(2024, month, 0).getDate();
}

/** `MM-DD` as a `yyyy-MM-DD` value for a date input, in the current year
 *  (a leap year stands in when the key is 29 February and this year has none). */
export function inputValue(key: string, now: Date): string {
	let year = now.getFullYear();
	if (key === '02-29' && new Date(year, 1, 29).getMonth() !== 1) year = 2024;
	return `${year}-${key}`;
}

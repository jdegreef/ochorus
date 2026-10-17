import type { ForSermon } from './forPages';
import { parseIsoDay } from './planSchedule';
import { buildScheduleICS } from './reminder';

/**
 * A sermon series on a group's calendar: the first meeting's date, then the
 * same weekday each week after, one sermon to a week — so the leader's
 * calendar (and every member's, once they're sent the file) says what to read
 * before each meeting. No account and no server, as with a plan's calendar.
 */

/** The reminder's hour on each meeting day: in the morning, in time to read. */
export const SERIES_REMINDER = '08:00';

/** Each week's meeting date, from the first (`YYYY-MM-DD`); none for a bad date. */
export function seriesDates(firstMeeting: string, weeks: number): Date[] {
	const first = parseIsoDay(firstMeeting);
	if (!first) return [];
	return Array.from({ length: weeks }, (_, i) => {
		const d = new Date(first);
		d.setDate(first.getDate() + 7 * i);
		return d;
	});
}

/** The series as an iCalendar file: one event per week, named for that
 *  week's sermon, linking to it. */
export function seriesICS(
	series: { title: string; sermons: ForSermon[] },
	firstMeeting: string,
	opts: {
		now: Date;
		week: (n: number) => string;
		sermonUrl: (slug: string) => string;
	}
): string {
	const dates = seriesDates(firstMeeting, series.sermons.length);
	return buildScheduleICS(
		series.sermons.map((s, i) => ({
			date: dates[i],
			summary: `${opts.week(i + 1)} · ${s.title} — ${series.title}`,
			url: opts.sermonUrl(s.slug)
		})),
		SERIES_REMINDER,
		{
			now: opts.now,
			uidPrefix: `ochorus-series-${slugify(series.title)}-${firstMeeting}`
		}
	);
}

const slugify = (s: string) =>
	s
		.normalize('NFKD')
		.replace(/\p{M}/gu, '')
		.toLowerCase()
		.replace(/[^a-z0-9]+/g, '-')
		.replace(/^-|-$/g, '');

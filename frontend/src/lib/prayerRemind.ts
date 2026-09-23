import * as m from './paraglide/messages.js';
import { SITE_URL } from './config';
import { downloadFile } from './dataExport';
import { truncateMeta } from './seo';
import { buildReminderICS } from './reminder';
import { parseRemind, type JournalEntry, type PrayerList } from './journal';

/**
 * A prayer's reminder, the same zero-infrastructure way the reading reminder
 * works: a repeating calendar event (.ics) the reader adds once, which then
 * fires on every device their calendar reaches. The Notebook only records
 * which reminder they added, so it can say so on the prayer.
 */

/** A weekday's name in `locale`, Sunday = 0 (the stored `weekly-0` and the
 *  calendar's BYDAY order). 2026-01-04 is a Sunday, so day d is the 4th + d. */
export function weekdayName(day: number, locale: string): string {
	return new Date(2026, 0, 4 + day).toLocaleDateString(locale, { weekday: 'long' });
}

/** "Every day at 07:00" / "Every Sunday at 09:00", in the reader's language. */
export function remindLabel(remind: string, locale: string): string {
	const r = parseRemind(remind);
	if (!r) return '';
	if (r.freq === 'daily') return m.notebook_remind_every_day({ time: r.time });
	return m.notebook_remind_every_week({ day: weekdayName(r.day, locale), time: r.time });
}

/** What the calendar event says: who the prayer is for, else its first words. */
export function remindSummary(e: JournalEntry): string {
	if (e.person) return m.notebook_remind_summary_for({ person: e.person });
	return m.notebook_remind_summary({ what: truncateMeta(e.title || e.body, 60) });
}

export function downloadRemindCalendar(e: JournalEntry, remind: string, now = new Date()) {
	const r = parseRemind(remind);
	if (!r) return;
	const ics = buildReminderICS(r.time, {
		now,
		uid: `${crypto.randomUUID?.() ?? Date.now()}@ochorus.com`,
		summary: remindSummary(e),
		// The prayer's own words go in the event — it is the reader's own
		// calendar, and the point is to have the words in front of them.
		description: `${e.body}\n\n${SITE_URL}/notebook?view=prayers`,
		url: `${SITE_URL}/notebook?view=prayers`,
		...(r.freq === 'weekly' ? { weekday: r.day } : {})
	});
	downloadFile('ochorus-prayer-reminder.ics', 'text/calendar;charset=utf-8', ics);
}

/**
 * A prayer list's reminder: one repeating calendar event for the whole group,
 * listing what is being prayed for in it today (the list is copied into the
 * event when it is added — the link opens the list as it stands then).
 */
export function downloadGroupCalendar(list: PrayerList, groupName: string, remind: string, now = new Date()) {
	const r = parseRemind(remind);
	if (!r) return;
	const url = `${SITE_URL}/notebook?view=prayers&group=${list.group || 'other'}`;
	const lines = list.cards.flatMap((c) =>
		c.prayers.map((p) => `• ${c.person ? `${c.person} — ` : ''}${truncateMeta(p.title || p.body, 80)}`)
	);
	const ics = buildReminderICS(r.time, {
		now,
		uid: `${crypto.randomUUID?.() ?? Date.now()}@ochorus.com`,
		summary: m.notebook_group_remind_summary({ group: groupName }),
		description: `${lines.slice(0, 20).join('\n')}\n\n${url}`,
		url,
		...(r.freq === 'weekly' ? { weekday: r.day } : {})
	});
	downloadFile(`ochorus-${list.group || 'prayers'}-reminder.ics`, 'text/calendar;charset=utf-8', ics);
}

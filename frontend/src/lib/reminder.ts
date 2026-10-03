/**
 * Daily reading reminder as an iCalendar (.ics) file — zero server infrastructure.
 * The reader picks a time; we hand them a repeating all-devices calendar event
 * they add once. `now`, `uid` and the text are injected so the builder is pure
 * and testable (and so the caller owns i18n).
 */
import type { ReadingDays } from './planSchedule';

export interface ReminderOptions {
	/** Reference time; the first occurrence is today (if still ahead) or tomorrow. */
	now: Date;
	/** Stable unique id for the VEVENT (e.g. a timestamp+random string). */
	uid: string;
	summary: string;
	description: string;
	url: string;
	/**
	 * Repeat weekly on this weekday (0 = Sunday … 6 = Saturday) instead of
	 * daily — a Notebook prayer reminder can be "every Sunday". Omitted = daily.
	 */
	weekday?: number;
}

const BYDAY = ['SU', 'MO', 'TU', 'WE', 'TH', 'FR', 'SA'];

const pad = (n: number) => String(n).padStart(2, '0');

/** The reminder time every picker starts from. */
export const DEFAULT_REMINDER_TIME = '07:00';
/** Where Settings keeps the reader's daily reminder time ("07:30"). */
export const REMINDER_TIME_KEY = 'ochorus:reminder-time';

/** The daily reminder time the reader set, or the default. */
export function readReminderTime(): string {
	try {
		const v = localStorage.getItem(REMINDER_TIME_KEY);
		if (v && /^\d{2}:\d{2}$/.test(v)) return v;
	} catch {
		// Storage blocked: the default stands.
	}
	return DEFAULT_REMINDER_TIME;
}

/** A local calendar date, `YYYYMMDD` — an all-day event's DTSTART. */
function fmtDate(d: Date): string {
	return `${d.getFullYear()}${pad(d.getMonth() + 1)}${pad(d.getDate())}`;
}

/** Floating local time (no Z): the reminder fires at the same wall-clock time
 *  wherever the reader is — what a daily habit reminder should do. */
function fmtLocal(d: Date): string {
	return `${fmtDate(d)}T${pad(d.getHours())}${pad(d.getMinutes())}00`;
}

/** "07:30" → [7, 30]; anything unparsable counts as 0. */
function parseHHMM(hhmm: string): [number, number] {
	const [h, m] = hhmm.split(':').map((x) => parseInt(x, 10));
	return [h || 0, m || 0];
}

/** An alert on an event, at `trigger` (an RFC 5545 duration from its start). */
function alarm(trigger: string, summary: string): string[] {
	return ['BEGIN:VALARM', `TRIGGER:${trigger}`, 'ACTION:DISPLAY', `DESCRIPTION:${esc(summary)}`, 'END:VALARM'];
}

/**
 * A content line folded at 75 octets (RFC 5545 §3.1): each continuation starts
 * with a space. Counts UTF-8 bytes and never splits a character, so a long
 * title in any script survives strict importers.
 */
export function foldLine(line: string): string {
	const enc = new TextEncoder();
	const out: string[] = [];
	let cur = '';
	let bytes = 0;
	for (const ch of line) {
		const n = enc.encode(ch).length;
		// Continuation lines spend one octet on their leading space.
		if (bytes + n > (out.length ? 74 : 75)) {
			out.push(cur);
			cur = '';
			bytes = 0;
		}
		cur += ch;
		bytes += n;
	}
	out.push(cur);
	return out.join('\r\n ');
}

/** A whole calendar file around `events`' lines, folded and CRLF-joined as RFC 5545 requires. */
function calendar(product: string, events: string[]): string {
	const lines = ['BEGIN:VCALENDAR', 'VERSION:2.0', `PRODID:-//Ochorus//${product}//EN`, 'CALSCALE:GREGORIAN'];
	return [...lines, ...events, 'END:VCALENDAR'].map(foldLine).join('\r\n') + '\r\n';
}

/** UTC stamp for DTSTAMP. */
function fmtUTC(d: Date): string {
	return (
		`${d.getUTCFullYear()}${pad(d.getUTCMonth() + 1)}${pad(d.getUTCDate())}` +
		`T${pad(d.getUTCHours())}${pad(d.getUTCMinutes())}${pad(d.getUTCSeconds())}Z`
	);
}

/** Escape a text value per RFC 5545 (backslash, semicolon, comma, newline). */
function esc(s: string): string {
	return s.replace(/\\/g, '\\\\').replace(/;/g, '\\;').replace(/,/g, '\\,').replace(/\r?\n/g, '\\n');
}

/** Build the .ics text for a daily reminder at `hhmm` ("07:00"). */
export function buildReminderICS(hhmm: string, opts: ReminderOptions): string {
	const [h, m] = parseHHMM(hhmm);
	const start = new Date(opts.now);
	start.setHours(h, m, 0, 0);
	const weekly = opts.weekday !== undefined && opts.weekday >= 0 && opts.weekday <= 6;
	if (weekly) {
		// The first occurrence is the next such weekday (today, if still ahead).
		start.setDate(start.getDate() + ((opts.weekday! - start.getDay() + 7) % 7));
		if (start.getTime() <= opts.now.getTime()) start.setDate(start.getDate() + 7);
	} else if (start.getTime() <= opts.now.getTime()) {
		// If today's time has already passed, start tomorrow.
		start.setDate(start.getDate() + 1);
	}

	return calendar('Reading Reminder', [
		'BEGIN:VEVENT',
		`UID:${opts.uid}`,
		`DTSTAMP:${fmtUTC(opts.now)}`,
		`DTSTART:${fmtLocal(start)}`,
		weekly ? `RRULE:FREQ=WEEKLY;BYDAY=${BYDAY[opts.weekday!]}` : 'RRULE:FREQ=DAILY',
		`SUMMARY:${esc(opts.summary)}`,
		`DESCRIPTION:${esc(opts.description)}`,
		`URL:${esc(opts.url)}`,
		...alarm('PT0M', opts.summary),
		'END:VEVENT'
	]);
}

export interface ScheduledReading {
	date: Date;
	summary: string;
	url: string;
}

/**
 * A reading plan's schedule as an iCalendar file: one all-day event per
 * reading, each with an alert at `hhmm` ("07:00") that morning — the plan on
 * the reader's own calendar, reminders included, with no server. `now` and
 * `uidPrefix` are injected so the builder stays pure.
 */
export function buildScheduleICS(
	readings: ScheduledReading[],
	hhmm: string,
	opts: { now: Date; uidPrefix: string }
): string {
	const [h, m] = parseHHMM(hhmm);
	// An all-day event lasts one day without a DTEND (RFC 5545 §3.6.1); the
	// alert counts from its start, local midnight — so h:m that morning.
	return calendar(
		'Reading Plan',
		readings.flatMap((r, i) => [
			'BEGIN:VEVENT',
			`UID:${opts.uidPrefix}-${i + 1}`,
			`DTSTAMP:${fmtUTC(opts.now)}`,
			`DTSTART;VALUE=DATE:${fmtDate(r.date)}`,
			`SUMMARY:${esc(r.summary)}`,
			`URL:${esc(r.url)}`,
			...alarm(`PT${h}H${m}M`, r.summary),
			'END:VEVENT'
		])
	);
}

/** RRULE weekdays for each reading-days rule (RFC 5545 BYDAY). */
const RULE_BYDAY: Record<ReadingDays, string> = {
	daily: '',
	weekdays: 'MO,TU,WE,TH,FR',
	monsat: 'MO,TU,WE,TH,FR,SA'
};

/**
 * An "Add to Google Calendar" link for a reading plan: ONE repeating event at
 * the reader's reminder time, on their reading days, for exactly the readings
 * left — opened in Google's own event editor.
 *
 * Why not the .ics: Google's import drops an event's own alerts (VALARM), so
 * the file's per-reading reminders never fire there. An event made in
 * Google's editor takes the calendar's default notification instead — the
 * alert the reader gets. Times are floating local (no Z) with `ctz`, so the
 * event sits at the same wall-clock time wherever they are.
 */
export function googleCalendarUrl(opts: {
	title: string;
	details: string;
	/** The first reading's date (already a reading day). */
	start: Date;
	hhmm: string;
	rule: ReadingDays;
	/** How many readings are left. */
	count: number;
	/** The reader's IANA time zone. */
	ctz?: string;
}): string {
	const [h, m] = parseHHMM(opts.hhmm);
	const from = new Date(opts.start);
	from.setHours(h, m, 0, 0);
	const to = new Date(from.getTime() + 15 * 60_000); // a short slot: it's a reminder
	const byday = RULE_BYDAY[opts.rule];
	const rrule = byday
		? `RRULE:FREQ=WEEKLY;BYDAY=${byday};COUNT=${opts.count}`
		: `RRULE:FREQ=DAILY;COUNT=${opts.count}`;
	const params = new URLSearchParams({
		action: 'TEMPLATE',
		text: opts.title,
		details: opts.details,
		dates: `${fmtLocal(from)}/${fmtLocal(to)}`,
		recur: rrule
	});
	if (opts.ctz) params.set('ctz', opts.ctz);
	return `https://calendar.google.com/calendar/render?${params}`;
}

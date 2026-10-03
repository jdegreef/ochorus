/**
 * Daily reading reminder as an iCalendar (.ics) file — zero server infrastructure.
 * The reader picks a time; we hand them a repeating all-devices calendar event
 * they add once. `now`, `uid` and the text are injected so the builder is pure
 * and testable (and so the caller owns i18n).
 */

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

/** Floating local time (no Z): the reminder fires at the same wall-clock time
 *  wherever the reader is — what a daily habit reminder should do. */
function fmtLocal(d: Date): string {
	return (
		`${d.getFullYear()}${pad(d.getMonth() + 1)}${pad(d.getDate())}` +
		`T${pad(d.getHours())}${pad(d.getMinutes())}00`
	);
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
	const [h, m] = hhmm.split(':').map((x) => parseInt(x, 10));
	const start = new Date(opts.now);
	start.setHours(h || 0, m || 0, 0, 0);
	const weekly = opts.weekday !== undefined && opts.weekday >= 0 && opts.weekday <= 6;
	if (weekly) {
		// The first occurrence is the next such weekday (today, if still ahead).
		start.setDate(start.getDate() + ((opts.weekday! - start.getDay() + 7) % 7));
		if (start.getTime() <= opts.now.getTime()) start.setDate(start.getDate() + 7);
	} else if (start.getTime() <= opts.now.getTime()) {
		// If today's time has already passed, start tomorrow.
		start.setDate(start.getDate() + 1);
	}

	const lines = [
		'BEGIN:VCALENDAR',
		'VERSION:2.0',
		'PRODID:-//Ochorus//Reading Reminder//EN',
		'CALSCALE:GREGORIAN',
		'BEGIN:VEVENT',
		`UID:${opts.uid}`,
		`DTSTAMP:${fmtUTC(opts.now)}`,
		`DTSTART:${fmtLocal(start)}`,
		weekly ? `RRULE:FREQ=WEEKLY;BYDAY=${BYDAY[opts.weekday!]}` : 'RRULE:FREQ=DAILY',
		`SUMMARY:${esc(opts.summary)}`,
		`DESCRIPTION:${esc(opts.description)}`,
		`URL:${esc(opts.url)}`,
		'BEGIN:VALARM',
		'TRIGGER:PT0M',
		'ACTION:DISPLAY',
		`DESCRIPTION:${esc(opts.summary)}`,
		'END:VALARM',
		'END:VEVENT',
		'END:VCALENDAR'
	];
	// RFC 5545 requires CRLF line breaks.
	return lines.join('\r\n') + '\r\n';
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
	const [h, m] = hhmm.split(':').map((x) => parseInt(x, 10));
	const day = (d: Date) => `${d.getFullYear()}${pad(d.getMonth() + 1)}${pad(d.getDate())}`;
	const lines = ['BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//Ochorus//Reading Plan//EN', 'CALSCALE:GREGORIAN'];
	readings.forEach((r, i) => {
		const next = new Date(r.date);
		next.setDate(next.getDate() + 1);
		lines.push(
			'BEGIN:VEVENT',
			`UID:${opts.uidPrefix}-${i + 1}`,
			`DTSTAMP:${fmtUTC(opts.now)}`,
			`DTSTART;VALUE=DATE:${day(r.date)}`,
			`DTEND;VALUE=DATE:${day(next)}`,
			`SUMMARY:${esc(r.summary)}`,
			`URL:${esc(r.url)}`,
			'BEGIN:VALARM',
			// Relative to the all-day event's start, local midnight: that morning.
			`TRIGGER:PT${h || 0}H${m || 0}M`,
			'ACTION:DISPLAY',
			`DESCRIPTION:${esc(r.summary)}`,
			'END:VALARM',
			'END:VEVENT'
		);
	});
	lines.push('END:VCALENDAR');
	return lines.join('\r\n') + '\r\n';
}

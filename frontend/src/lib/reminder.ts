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
}

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
	// If today's time has already passed, start tomorrow.
	if (start.getTime() <= opts.now.getTime()) start.setDate(start.getDate() + 1);

	const lines = [
		'BEGIN:VCALENDAR',
		'VERSION:2.0',
		'PRODID:-//Ochorus//Reading Reminder//EN',
		'CALSCALE:GREGORIAN',
		'BEGIN:VEVENT',
		`UID:${opts.uid}`,
		`DTSTAMP:${fmtUTC(opts.now)}`,
		`DTSTART:${fmtLocal(start)}`,
		'RRULE:FREQ=DAILY',
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

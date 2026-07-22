import { describe, it, expect } from 'vitest';
import { buildReminderICS } from './reminder';

const base = { uid: 'u1', summary: 'Ochorus — daily reading', description: 'A few minutes with a classic.', url: 'https://ochorus.com' };

describe('buildReminderICS', () => {
	it('builds a daily-recurring VEVENT with CRLF endings', () => {
		const ics = buildReminderICS('07:00', { ...base, now: new Date('2026-07-22T09:00:00') });
		expect(ics).toContain('BEGIN:VCALENDAR');
		expect(ics).toContain('RRULE:FREQ=DAILY');
		expect(ics).toContain('UID:u1');
		expect(ics).toContain('\r\n');
		expect(ics.trimEnd().endsWith('END:VCALENDAR')).toBe(true);
	});

	it('starts tomorrow when the time has already passed today', () => {
		const ics = buildReminderICS('07:00', { ...base, now: new Date('2026-07-22T09:00:00') });
		expect(ics).toContain('DTSTART:20260723T070000');
	});

	it('starts today when the time is still ahead', () => {
		const ics = buildReminderICS('21:30', { ...base, now: new Date('2026-07-22T09:00:00') });
		expect(ics).toContain('DTSTART:20260722T213000');
	});

	it('escapes commas in text values', () => {
		const ics = buildReminderICS('07:00', {
			...base,
			description: 'Read a classic, daily.',
			now: new Date('2026-07-22T06:00:00')
		});
		expect(ics).toContain('DESCRIPTION:Read a classic\\, daily.');
	});
});

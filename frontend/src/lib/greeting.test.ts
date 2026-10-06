import { describe, expect, it } from 'vitest';
import { dayPart, greetingName } from './greeting';

describe('dayPart', () => {
	it.each([
		[4, 'morning'],
		[11, 'morning'],
		[12, 'afternoon'],
		[16, 'afternoon'],
		[17, 'evening'],
		[23, 'evening'],
		[0, 'evening'],
		[3, 'evening']
	] as const)('%i:00 is %s', (hour, part) => {
		expect(dayPart(hour)).toBe(part);
	});
});

describe('greetingName', () => {
	it('uses the first word of the display name', () => {
		expect(greetingName('James DeGreef', 'x@y.com')).toBe('James');
		expect(greetingName('  Amina  ', undefined)).toBe('Amina');
	});
	it('falls back to the email local part, never the address', () => {
		expect(greetingName('', 'reader.one@example.org')).toBe('reader.one');
		expect(greetingName('   ', undefined)).toBe('');
	});
});

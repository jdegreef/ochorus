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

describe('dayPart by language', () => {
	it('keeps "good night" for the night where the evening greeting means it', () => {
		expect(dayPart(18, 'es')).toBe('afternoon');
		expect(dayPart(19, 'pt')).toBe('afternoon');
		expect(dayPart(20, 'es')).toBe('evening');
		expect(dayPart(18, 'fr')).toBe('evening');
	});
});

describe('greetingName', () => {
	it('keeps a name that opens with a title or an initial whole', () => {
		expect(greetingName('Rev. John Smith', undefined)).toBe('Rev. John Smith');
		expect(greetingName('Dr Amina Yusuf', undefined)).toBe('Dr Amina Yusuf');
		expect(greetingName('J. R. Miller', undefined)).toBe('J. R. Miller');
		expect(greetingName('Pastor Ade', undefined)).toBe('Pastor Ade');
	});

	it('uses the first word of the display name', () => {
		expect(greetingName('James DeGreef', 'x@y.com')).toBe('James');
		expect(greetingName('  Amina  ', undefined)).toBe('Amina');
	});
	it('falls back to the email local part, never the address', () => {
		expect(greetingName('', 'reader.one@example.org')).toBe('reader.one');
		expect(greetingName('   ', undefined)).toBe('');
	});
});

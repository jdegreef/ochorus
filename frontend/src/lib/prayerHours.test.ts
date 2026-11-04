import { describe, expect, it } from 'vitest';
import { prayerHour, skyBody } from './prayerHours';

describe('prayerHour', () => {
	it.each([
		[0, 'vigils'],
		[4, 'vigils'],
		[5, 'lauds'],
		[7, 'lauds'],
		[8, 'terce'],
		[11, 'sext'],
		[13, 'sext'],
		[14, 'none'],
		[17, 'vespers'],
		[19, 'vespers'],
		[20, 'compline'],
		[23, 'compline']
	])('%i:00 is %s', (hour, name) => {
		expect(prayerHour(hour)).toBe(name);
	});
});

describe('skyBody', () => {
	const at = (h: number, m = 0) => skyBody(new Date(2026, 10, 3, h, m));
	it('raises the sun at Lauds, tops it at midday, sets it at Compline', () => {
		expect(at(5)).toEqual({ body: 'sun', along: 0, height: 0 });
		expect(at(12, 30).along).toBeCloseTo(0.5);
		expect(at(12, 30).height).toBeCloseTo(1);
		expect(at(19, 59).body).toBe('sun');
		expect(at(19, 59).along).toBeLessThan(1);
	});
	it('gives the night to the moon, across midnight', () => {
		expect(at(20)).toEqual({ body: 'moon', along: 0, height: 0 });
		expect(at(0, 30).along).toBeCloseTo(0.5);
		expect(at(4, 59).body).toBe('moon');
		expect(at(4, 59).along).toBeLessThan(1);
	});
});

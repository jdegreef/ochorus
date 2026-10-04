import { describe, expect, it } from 'vitest';

import { busiestCell, hourLabel, sendTime } from './engagementHours';

const empty = () => Array.from({ length: 7 }, () => Array<number | null>(24).fill(null));

describe('reading hours', () => {
	it('labels hours on a 12-hour clock', () => {
		expect([0, 6, 12, 23].map(hourLabel)).toEqual(['12am', '6am', '12pm', '11pm']);
	});

	it('finds the busiest cell and the hour that peaks across the week', () => {
		const g = empty();
		g[6][6] = 50; // Sunday 6am: the busiest single cell
		g[0][21] = 30; // but 9pm wins across the week
		g[1][21] = 30;
		g[2][6] = 5;
		expect(busiestCell(g)).toEqual({ day: 6, hour: 6, minutes: 50 });
		expect(sendTime(g)).toEqual({ hour: 21, label: '8:30pm' });
	});

	it('suggests the evening before for a midnight peak', () => {
		const g = empty();
		g[3][0] = 10;
		expect(sendTime(g)?.label).toBe('11:30pm');
	});

	it('has nothing to say about an empty grid', () => {
		expect(busiestCell(empty())).toBeNull();
		expect(sendTime(empty())).toBeNull();
	});
});
